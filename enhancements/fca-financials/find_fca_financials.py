"""Financial figures from FCA co-operative/mutual society annual returns (AR30) in the Braw corpus.

Standalone enhancement. FETCH stage: builds the GB-MPR catalogue of the Braw corpus API (every
return per society, i.e. a panel) and caches each return's markdown text under work/docs/.
EXTRACT stage: regex-only reading of modern AR30 section 4.2 (six figures) and the year-end date
from the cached text, plus an optional comparison with the PDF pipeline's v4 baseline.

Usage: python find_fca_financials.py [--limit 50] [--no-fetch] [--min-year 2018] [--work-dir ...]
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import time
import urllib.error
import urllib.request
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
API_KEYS = Path(r"C:\Users\diarm\Braw Data\web-apps - Documents\braw-charity-accounts-api\.api-keys.local.json")
WORK_DIR = SCRIPT_DIR / "work"
OUT_DIR = SCRIPT_DIR / "output"
BASELINE_DIR = Path(r"D:\fca-annual-reports\archive\v4-baseline-20260727\build-audit-20260727")

BASE = "https://corpusapi.brawdata.com"
JURISDICTION = "GB-MPR"
MIN_YEAR = 2018
MIN_REQUEST_GAP = 1.05  # seconds; API allows 60 requests a minute per key
PROGRESS_EVERY = 100
SAMPLE_SEED = 42

_last_request = 0.0


# ---------- API ----------
def get(path: str, key: str, raw: bool = False):
    """GET from the corpus API, paced and retried on 429 (copied from the NI enhancement)."""
    global _last_request
    req = urllib.request.Request(BASE + path, headers={"X-API-Key": key})
    while True:
        wait = MIN_REQUEST_GAP - (time.monotonic() - _last_request)
        if wait > 0:
            time.sleep(wait)
        _last_request = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
            break
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            time.sleep(int(e.headers.get("Retry-After") or 10))
    return data.decode("utf-8") if raw else json.loads(data)


# ---------- atomic writes ----------
def write_text_atomic(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_csv_atomic(df: pd.DataFrame, path: Path) -> None:
    tmp = path.with_name(path.name + ".tmp")
    df.to_csv(tmp, index=False)
    os.replace(tmp, path)


# ---------- fetch stage ----------
def load_catalogue(key: str, work_dir: Path, min_year: int) -> pd.DataFrame:
    """Combined GB-MPR catalogue, min_year to this year, cached to work/catalogue_gb_mpr.csv.

    Every document per society is kept (panel). The cache is reused as-is on later runs, so
    delete it to rebuild with a different --min-year or to pick up newly added returns.
    """
    path = work_dir / "catalogue_gb_mpr.csv"
    if path.exists():
        return pd.read_csv(path, dtype=str, keep_default_na=False)
    rows: list[dict] = []
    for y in range(min_year, datetime.date.today().year + 1):
        rows += get(f"/catalogue/year/{y}?jurisdiction={JURISDICTION}", key)["accounts"]
    cat = pd.DataFrame(rows).astype(str)  # all columns as returned (doc_id, charity_number, year_end_date, ...)
    cat = cat.drop_duplicates("doc_id").sort_values("doc_id").reset_index(drop=True)
    write_csv_atomic(cat, path)
    return cat


def doc_path(work_dir: Path, number: str, year_end_date: str) -> Path:
    return work_dir / "docs" / f"{number}_{year_end_date}.md"


def fetch_docs(docs: pd.DataFrame, key: str, work_dir: Path) -> tuple[int, int]:
    """Fetch each document's text to the cache (resumable). Returns (fetched_this_run, failures)."""
    (work_dir / "docs").mkdir(parents=True, exist_ok=True)
    failures: list[dict] = []
    fetched = 0
    for i, r in enumerate(docs.itertuples(index=False), 1):
        path = doc_path(work_dir, r.charity_number, r.year_end_date)
        if not path.exists():
            try:
                write_text_atomic(path, get(f"/accounts/{r.doc_id}?format=raw", key, raw=True))
                fetched += 1
            except (urllib.error.URLError, TimeoutError, OSError, UnicodeDecodeError) as e:
                failures.append({"doc_id": r.doc_id, "error": f"{type(e).__name__}: {e}"})
        if i % PROGRESS_EVERY == 0:
            print(f"  docs {i:,}/{len(docs):,} (new {fetched:,}, failed {len(failures):,})", flush=True)
    write_csv_atomic(pd.DataFrame(failures, columns=["doc_id", "error"]), work_dir / "fetch_failures.csv")
    return fetched, len(failures)


# ---------- extract stage ----------
# Section 4.2 labels in form order: field -> (whitespace-tolerant label pattern, unit).
FIELDS = {
    "number_of_members": (r"number\s*of\s*members", "count"),
    "turnover": (r"turnover", "GBP"),
    "assets": (r"assets", "GBP"),
    "number_of_employees": (r"number\s*of\s*employees", "count"),
    "share_capital": (r"share\s*capital", "GBP"),
    "highest_rate_interest_paid_on_shares": (r"highest\s*rate\s*of\s*interest(?:\s*paid)?", "percent"),
}
MODERN_TITLE = re.compile(r"Annual Return \(AR3[0O]{1,2}\) forms?", re.I)
BLOCK_START = re.compile(r"4\.2\s+Based\s+on\s+the\s+accounts", re.I)
BLOCK_END = re.compile(r"4\.3\s+What\s+Standard", re.I)
MAX_BLOCK = 3000  # characters; used when "4.3 What Standard" is missing or OCR-garbled
FOOTER = re.compile(r"(?:FCA.{0,6}?)?Mutua\S*\s+Annua\S*\s+Return\s*\(AR3\w*\).{0,30}?Release\s*\d+"
                    r".{0,6}?[A-Za-z]+\s+\d{4}", re.I)
PAGE = re.compile(r"Page\s*\d+(?:\s*of\s*\d+)?", re.I)
IF_ANY = re.compile(r"\(\s*if\s*any\s*\)", re.I)
YEAR_END_Q = re.compile(r"\d\.\d\s*What\s+date\s+did\s+the\s+financial\s+year\s+covered\s+by\s+these\s+"
                        r"accounts\s+end\?", re.I)
TOKEN = re.compile(r"£?\s*\(?\d+(?:[.,]\s?\d+)*\)?%?|\S+")  # "64, 205" stays one token, "12741 0" is two
OK_STATUSES = {"parsed", "nil", "not_applicable"}


def classify(text: str) -> str:
    if MODERN_TITLE.search(text) and BLOCK_START.search(text) and "AR41" not in text:
        return "ar30_modern"
    if re.search(r"4\.2\s+Has\s+your\s+society\s+produced\s+accounts", text, re.I):
        return "ar30_2014"
    if "AR41" in text:
        return "ar41"
    if re.search(r"A\.\s?R\.\s?5", text):
        return "ar5"
    if re.search(r"credit\s+union", text, re.I):
        return "credit_union"
    return "other"


def find_block(text: str) -> tuple[str, int]:
    """Raw text of the FIRST section 4.2 block and its end position in the document."""
    m = BLOCK_START.search(text)
    if not m:
        return "", 0
    end = BLOCK_END.search(text, m.end())
    stop = min(end.start() if end else len(text), m.end() + MAX_BLOCK)
    return text[m.end():stop], stop


def layout_of(text: str, block: str, block_end: int) -> str:
    """paper (PDF form, filled or scanned) vs online (web form). The footer is only looked for
    up to the end of the first block: 4253R has an online copy followed by a scanned one."""
    return "paper" if IF_ANY.search(block) or FOOTER.search(text[:block_end]) else "online"


def normalise_block(block: str) -> str:
    s = re.sub(r"<[^>]*>|[*|#_\"]", " ", block)  # <br>, comments, bold, table pipes, headings
    s = PAGE.sub(" ", FOOTER.sub(" ", s))
    s = re.sub(r"(?:paid\s*)?on\s*shares", " ", IF_ANY.sub(" ", s), flags=re.I)
    return " ".join(s.split())


def field_tokens(block: str) -> dict[str, str]:
    """Raw value text for each field found in a normalised block.

    Tokens between a label and the next found label belong to it. A label with no token waits
    (stacked labels, 6365R): the next non-empty run fills waiting labels in order. Fewer tokens
    than waiting labels go to the nearest labels; surplus tokens are kept on the last label so
    the value goes to review instead of silently losing digits.
    """
    hits, pos = [], 0
    for field, (pattern, _) in FIELDS.items():
        m = re.compile(pattern, re.I).search(block, pos)
        if m:
            hits.append((field, m))
            pos = m.end()
    out: dict[str, str] = {}
    pending: list[str] = []
    for i, (field, m) in enumerate(hits):
        stop = hits[i + 1][1].start() if i + 1 < len(hits) else len(block)
        toks = [t.strip() for t in TOKEN.findall(block, m.end(), stop) if any(c.isalnum() for c in t)]
        pending.append(field)
        if not toks:
            continue
        targets = pending[-len(toks):] if len(toks) < len(pending) else pending
        for j, f in enumerate(targets):
            out[f] = " ".join(toks[j:]) if j == len(targets) - 1 else toks[j]
        pending = []
    return out


def format_decimal(value: Decimal) -> str:
    return str(value.quantize(Decimal(1))) if value == value.to_integral() else format(value.normalize(), "f")


def parse_value(raw: str, unit: str, online: bool) -> tuple[str, str]:
    """(normalised value, status) for one raw token. Mirrors ar30_financials._parse_value."""
    s = raw.replace("**", "").strip()
    if not s:
        return "", "missing"
    if re.fullmatch(r"N/?A|NOT\s+APPLICABLE", s, re.I):
        return "-9", "not_applicable"  # missing-data code, not a measurement
    if re.fullmatch(r"N\s*[Il1|]\s*L|NONE", s, re.I):
        return "0", "nil"
    if re.fullmatch(r"[Oo]{1,2}", s):  # letter O for zero; trusted only when typed into the web form
        return ("0", "nil") if online else ("", "review")
    if unit == "percent" and "£" in s:
        return "", "review"
    bare = s.replace("£", "").replace("%", "").strip()
    if re.search(r"\s", bare) or bare.count("(") != bare.count(")"):
        return "", "review"
    inner = bare[1:-1] if bare.startswith("(") and bare.endswith(")") else bare
    if re.fullmatch(r"[1-9]\d{0,2}(?:\.\d{3})+", inner.lstrip("+-")):  # "1.234" = OCR for "1,234"
        return "", "review"
    if unit == "GBP" and "." in inner and len(inner.rsplit(".", 1)[1]) > 2:
        return "", "review"
    if len(re.sub(r"\D", "", inner)) > 15:
        return "", "review"
    try:
        n = Decimal(inner.replace(",", ""))
    except InvalidOperation:
        return "", "review"
    if not n.is_finite():
        return "", "review"
    if bare.startswith("("):
        n = -n
    if n == 0:
        n = Decimal(0)  # drop a phantom "-0"
    if unit == "count" and n != n.to_integral():
        return "", "review"
    if unit in {"count", "percent"} and n < 0:
        return "", "review"
    if unit == "percent" and (n > 100 or (0 < n < 1 and "%" not in s)):
        return "", "review"
    return format_decimal(n), "parsed"


def year_end_on_form(text: str) -> str:
    """ISO date answered to "2.1 What date did the financial year ... end?", or blank.

    Online forms give dd/mm/yyyy (sometimes in a table cell); filled PDFs give eight digit boxes
    ("3 1 1 2 2 0 2 1"), on the next line or the same line. Scanned forms are usually garbage.
    """
    m = YEAR_END_Q.search(text)
    if not m:
        return ""
    after = re.sub(r"<[^>]*>|[*|#]", " ", text[m.end():m.end() + 150]).strip()
    d = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})\b", after)
    b = re.match(r"(\d)\s*(\d)\s*(\d)\s*(\d)\s*(\d)\s*(\d)\s*(\d)\s*(\d)\b", after)
    try:
        if d:
            return datetime.date(int(d[3]), int(d[2]), int(d[1])).isoformat()
        if b:
            g = "".join(b.groups())
            return datetime.date(int(g[4:]), int(g[2:4]), int(g[:2])).isoformat()
    except ValueError:
        pass
    return ""


def extract_doc(text: str) -> dict:
    """Form type, layout, year-end and the six section 4.2 figures for one document."""
    row: dict = {"form_type": classify(text), "layout": "", "year_end_on_form": ""}
    for f in FIELDS:
        row.update({f: "", f"{f}_status": "", f"{f}_raw": ""})
    row["confidence"] = ""
    if row["form_type"] != "ar30_modern":
        return row
    block, block_end = find_block(text)
    row["layout"] = layout_of(text, block, block_end)
    row["year_end_on_form"] = year_end_on_form(text)
    raws = field_tokens(normalise_block(block))
    for f, (_, unit) in FIELDS.items():
        row[f"{f}_raw"] = raws.get(f, "")
        row[f], row[f"{f}_status"] = parse_value(row[f"{f}_raw"], unit, row["layout"] == "online")
    ok = all(row[f"{f}_status"] in OK_STATUSES for f in FIELDS)
    row["confidence"] = "high" if row["layout"] == "online" and ok else "review"
    return row


def extract_docs(docs: pd.DataFrame, work_dir: Path) -> pd.DataFrame:
    """One row per selected catalogue document that is cached; uncached documents are skipped."""
    rows = []
    for r in docs.itertuples(index=False):
        path = doc_path(work_dir, r.charity_number, r.year_end_date)
        if not path.exists():
            continue
        e = extract_doc(path.read_text(encoding="utf-8"))
        matches = "" if not e["year_end_on_form"] else str(e["year_end_on_form"] == r.year_end_date)
        rows.append({"uid": f"GB-MPR-{r.charity_number}", "society_number": r.charity_number,
                     "doc_id": r.doc_id, "catalogue_year_end": r.year_end_date,
                     "form_type": e["form_type"], "layout": e["layout"],
                     "year_end_on_form": e["year_end_on_form"], "year_end_matches_catalogue": matches,
                     **{k: e[k] for f in FIELDS for k in (f, f"{f}_status")},
                     **{f"{f}_raw": e[f"{f}_raw"] for f in FIELDS}, "confidence": e["confidence"]})
    cols = (["uid", "society_number", "doc_id", "catalogue_year_end", "form_type", "layout",
             "year_end_on_form", "year_end_matches_catalogue"]
            + [k for f in FIELDS for k in (f, f"{f}_status")] + [f"{f}_raw" for f in FIELDS] + ["confidence"])
    return pd.DataFrame(rows, columns=cols)


def compare_baseline(ours: pd.DataFrame, baseline_dir: Path) -> pd.DataFrame:
    """Long table of our values against the PDF pipeline's parsed values, matched on
    (society number, year end). Only fields the baseline parsed are compared."""
    parse = pd.read_csv(baseline_dir / "parser-v4-parse.csv", dtype=str, keep_default_na=False,
                        usecols=["fca_registration_number", "fca_document_id", "document_date",
                                 "form_version", "release_status"])
    parse = parse[(parse["form_version"] == "modern") & (parse["release_status"] == "releasable")]
    parse = parse.drop_duplicates(["fca_registration_number", "document_date"], keep="first")
    vals = pd.read_csv(baseline_dir / "parser-v4-values.csv", dtype=str, keep_default_na=False,
                       usecols=["fca_document_id", "field_code", "normalized_value", "value_status"])
    vals = vals[(vals["value_status"] == "parsed") & vals["field_code"].isin(list(FIELDS))]
    base = parse.merge(vals, on="fca_document_id")
    long = ours.melt(id_vars=["society_number", "catalogue_year_end"], value_vars=list(FIELDS),
                     var_name="field", value_name="ours")
    long["ours_status"] = ours.melt(value_vars=[f"{f}_status" for f in FIELDS])["value"].to_numpy()
    out = long.merge(base, left_on=["society_number", "catalogue_year_end", "field"],
                     right_on=["fca_registration_number", "document_date", "field_code"])
    ours_n = pd.to_numeric(out["ours"], errors="coerce")
    base_n = pd.to_numeric(out["normalized_value"], errors="coerce")
    out["agree"] = (ours_n.round(2) == base_n.round(2))
    return out.rename(columns={"catalogue_year_end": "year_end", "normalized_value": "baseline"})[
        ["society_number", "year_end", "field", "ours", "ours_status", "baseline", "agree"]]


def run_summary(out: pd.DataFrame) -> dict:
    modern = out[out["form_type"] == "ar30_modern"]
    return {
        "documents_extracted": len(out),
        "by_form_type": out["form_type"].value_counts().to_dict(),
        "by_layout": modern["layout"].value_counts().to_dict(),
        "by_confidence": modern["confidence"].value_counts().to_dict(),
        "year_end_matches_catalogue": modern["year_end_matches_catalogue"].replace("", "blank")
        .value_counts().to_dict(),
        "field_status": {f: modern[f"{f}_status"].value_counts().to_dict() for f in FIELDS},
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch FCA mutual society annual returns and extract AR30 section 4.2.")
    ap.add_argument("--api-keys", type=Path, default=API_KEYS)
    ap.add_argument("--work-dir", type=Path, default=WORK_DIR)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--baseline-dir", type=Path, default=BASELINE_DIR,
                    help="PDF pipeline v4 build audit; the comparison is skipped if the folder is absent")
    ap.add_argument("--no-fetch", action="store_true",
                    help="extract from cached documents only (needs a cached catalogue; uncached rows skipped)")
    ap.add_argument("--min-year", type=int, default=MIN_YEAR, help="first catalogue year (default 2018)")
    ap.add_argument("--limit", type=int, default=None,
                    help="process a reproducible random sample of N catalogue rows (spans years)")
    a = ap.parse_args()
    a.work_dir.mkdir(parents=True, exist_ok=True)
    key = "" if a.no_fetch else json.loads(a.api_keys.read_text())["prod"]  # never printed or logged

    docs = load_catalogue(key, a.work_dir, a.min_year)
    n_catalogue = len(docs)
    if a.limit:
        docs = docs.sample(n=min(a.limit, n_catalogue), random_state=SAMPLE_SEED).sort_values("doc_id")
    print(f"catalogue documents: {n_catalogue:,} ({docs['charity_number'].nunique():,} societies in "
          f"selection); processing {len(docs):,}", flush=True)

    if not a.no_fetch:
        fetched, n_failed = fetch_docs(docs, key, a.work_dir)
        print(f"fetched this run: {fetched:,}; failures: {n_failed:,}", flush=True)

    out = extract_docs(docs, a.work_dir)
    print(f"extracted {len(out):,}/{len(docs):,} selected documents (rest not cached)", flush=True)
    a.out_dir.mkdir(parents=True, exist_ok=True)
    write_csv_atomic(out, a.out_dir / "fca_ar30_financials.csv")
    summary = {"catalogue_documents": n_catalogue, "selected_documents": len(docs), **run_summary(out)}
    if a.baseline_dir.exists():
        comp = compare_baseline(out, a.baseline_dir)
        write_csv_atomic(comp, a.out_dir / "baseline_comparison.csv")
        missing = comp["ours"] == ""
        summary["baseline_comparison"] = {
            f: {"agree": int((g["agree"]).sum()), "disagree": int((~g["agree"] & (g["ours"] != "")).sum()),
                "ours_missing": int((g["ours"] == "").sum())}
            for f, g in comp.groupby("field")}
        print(f"baseline: {len(comp):,} field values compared, {int(comp['agree'].sum()):,} agree, "
              f"{int(missing.sum()):,} missing on our side", flush=True)
    else:
        print(f"baseline folder not found, comparison skipped: {a.baseline_dir}", flush=True)
    write_text_atomic(a.out_dir / "run_summary.json", json.dumps(summary, indent=2))
    print(json.dumps(summary["by_form_type"]), json.dumps(summary.get("by_confidence", {})), flush=True)


if __name__ == "__main__":
    main()
