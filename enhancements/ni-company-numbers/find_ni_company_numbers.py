"""Find Companies House numbers for unlinked Northern Irish charities in their latest accounts.

Standalone enhancement: reads the published Spine release, the CCNI catalogue of the Braw
corpus API, each target charity's most recent accounts (markdown), and the Companies House
public data API (company profiles, cached); writes scored candidates and high-confidence
matches in matches.csv schema.

Usage: python find_ni_company_numbers.py [--limit 50] [--release-dir ...] [--ch-keys ...]
"""
from __future__ import annotations

import argparse
import base64
import difflib
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
RELEASE_DIR = Path(r"C:\Users\diarm\Dropbox\cso-spine\code\release-v1.3.1-Sep2026")
# Same key source as code/companies-house (line "COH_API_KEYS=key1,key2,..."); a plain
# one-key-per-line file (the collection repo's coh-api-keys.txt format) also works.
CH_KEYS = Path(r"C:\Users\diarm\Dropbox\cso-spine\.env")
API_KEYS = Path(r"C:\Users\diarm\Braw Data\web-apps - Documents\braw-charity-accounts-api\.api-keys.local.json")
WORK_DIR = SCRIPT_DIR / "work"
OUT_DIR = SCRIPT_DIR / "output"

BASE = "https://corpusapi.brawdata.com"
JURISDICTION = "GB-NIC"
CATALOGUE_YEARS = range(2000, 2027)
MIN_REQUEST_GAP = 1.05  # seconds; API allows 60 requests a minute per key
PROGRESS_EVERY = 100

CH_BASE = "https://api.company-information.service.gov.uk"
CH_KEY_GAP = 0.5  # seconds between uses of one key: CH allows 600 requests / 5 min per key
CH_429_PAUSE = 300  # a key that gets a 429 is rested for one full 5-minute window
CH_MAX_ATTEMPTS = 5  # per number, on top of 429 key rotations

NAME_SIMILARITY_HIGH = 0.85
KEYWORD_WINDOW = 100  # chars before a mention searched for a keyword
SNIPPET_HALF = 60  # snippet ~120 chars around the first mention
KEYWORDS = ("company", "registered number", "registration number", "reg. no", "reg no",
            "limited by guarantee", "companies house")
DROP_NAME_TOKENS = {"LIMITED", "LTD", "THE", "CIC", "COMPANY", "CLG"}
MATCH_TYPE = "companyid - accounts regex"
CONFIDENCE_ORDER = {"high": 0, "medium": 1, "low": 2}

# Modern NI form: "NI" (or OCR "Nl") + 5-6 digits; the C in "NIC101307" blocks charity numbers.
# ponytail: 1-4 digit shorthand like "NI 4978" is deliberately skipped (too many false
# positives such as years, "NI 2025"); to upgrade, allow \d{1,6} but only when keyword_context.
NI_RE = re.compile(r"(?<![A-Za-z0-9])N[Il]\s*[:.\-]?\s*(\d{5,6})(?!\d)")
# Old NI form: "R0" + 6 digits, optional single space after R (e.g. R0000304).
OLD_NI_RE = re.compile(r"(?<![A-Za-z0-9])R ?0(\d{6})(?!\d)")
MARKDOWN_NOISE_RE = re.compile(r"\*\*|~~")

_last_request = 0.0


# ---------- API ----------
def get(path: str, key: str, raw: bool = False):
    """GET from the corpus API, paced and retried on 429 (copied from sample.py)."""
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


def load_ch_keys(path: Path) -> list[str]:
    """Companies House keys from a .env line COH_API_KEYS=k1,k2,... or a one-key-per-line file."""
    lines = [s.strip() for s in path.read_text(encoding="utf-8").splitlines() if s.strip() and not s.startswith("#")]
    env = [s.split("=", 1)[1] for s in lines if s.startswith("COH_API_KEYS=")]
    raw = env[0] if env else ",".join(s for s in lines if "=" not in s)
    keys = [k.strip().strip("\"'") for k in raw.split(",") if k.strip().strip("\"'")]
    if not keys:
        raise SystemExit(f"no Companies House API keys found in {path}")
    return keys


def ch_get(number: str, keys: list[str], free_at: list[float]) -> dict | None:
    """GET /company/{number} (basic auth: key as username, blank password); None on 404.

    Uses whichever key is free soonest, so keys rotate round-robin; free_at[i] is when key i may
    next be used (0.5s pacing, rested 5 min after a 429). 5xx/network errors back off and retry.
    """
    errors = 0
    for _ in range(CH_MAX_ATTEMPTS + 2 * len(keys)):
        i = min(range(len(keys)), key=free_at.__getitem__)
        wait = free_at[i] - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        free_at[i] = time.monotonic() + CH_KEY_GAP
        auth = base64.b64encode(f"{keys[i]}:".encode()).decode()
        req = urllib.request.Request(f"{CH_BASE}/company/{number}",
                                     headers={"Authorization": f"Basic {auth}", "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code == 429:
                free_at[i] = time.monotonic() + CH_429_PAUSE
                continue
            if e.code < 500:
                raise
            last = e
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
        errors += 1
        if errors >= CH_MAX_ATTEMPTS:
            raise last
        time.sleep(5 * errors)
    raise RuntimeError("rate limited (429) on every key repeatedly")


# ---------- atomic writes ----------
def write_text_atomic(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_csv_atomic(df: pd.DataFrame, path: Path) -> None:
    tmp = path.with_name(path.name + ".tmp")
    df.to_csv(tmp, index=False)
    os.replace(tmp, path)


# ---------- text normalisation / extraction ----------
def normalise_name(name: str) -> str:
    """Uppercase, & -> AND, drop punctuation and legal-form/filler tokens, collapse spaces."""
    s = re.sub(r"[^A-Z0-9 ]", " ", str(name).upper().replace("&", " AND "))
    return " ".join(t for t in s.split() if t not in DROP_NAME_TOKENS)


def normalise_postcode(pc) -> str:
    return re.sub(r"\s", "", str(pc or "")).upper()


def extract_company_numbers(text: str) -> list[dict]:
    """One dict per distinct normalised NI company number found in the text."""
    clean = MARKDOWN_NOISE_RE.sub("  ", text)
    hits: list[tuple[str, int, int]] = []
    hits += [("NI" + m.group(1).zfill(6), m.start(), m.end()) for m in NI_RE.finditer(clean)]
    hits += [("R0" + m.group(1), m.start(), m.end()) for m in OLD_NI_RE.finditer(clean)]
    found: dict[str, dict] = {}
    for number, start, end in sorted(hits, key=lambda h: h[1]):
        before = clean[max(0, start - KEYWORD_WINDOW):start].lower()
        has_kw = any(k in before for k in KEYWORDS)
        if number not in found:
            snippet = " ".join(clean[max(0, start - SNIPPET_HALF):end + SNIPPET_HALF].split())
            found[number] = {"number": number, "n_mentions": 0, "keyword_context": False, "snippet": snippet}
        found[number]["n_mentions"] += 1
        found[number]["keyword_context"] |= has_kw
    return list(found.values())


# ---------- pipeline steps ----------
def load_ccni_ch_links(release_dir: Path) -> pd.DataFrame:
    m = pd.read_csv(release_dir / "TSCS_spine.matches.csv", dtype=str, keep_default_na=False)
    m = m[(m["orgA_source"] == "ccni") & (m["orgB_source"] == "CH")].copy()
    m["orgB_id_in_source"] = m["orgB_id_in_source"].str.strip().str.upper()
    return m


def load_targets(release_dir: Path, links: pd.DataFrame) -> pd.DataFrame:
    """NI charities in the Spine with no charity-to-company link."""
    spine = pd.read_csv(release_dir / "TSCS_spine.spine.csv", dtype=str, keep_default_na=False,
                        usecols=["uid", "organisationname", "postcode", "removeddate"])
    t = spine[spine["uid"].str.startswith("GB-NIC-") & ~spine["uid"].isin(set(links["orgA_uid"]))].copy()
    t["charity_number"] = t["uid"].str[len("GB-NIC-"):]
    return t[["uid", "charity_number", "organisationname", "postcode", "removeddate"]]


def spine_presence(release_dir: Path) -> tuple[set[str], dict[str, set[str]]]:
    """(company numbers with their own Spine row, company number -> Spine org uids it is folded into).

    supplementary.csv carries only each record's own uid (id_in_source is blank), so the absorbing
    organisation comes from matches.csv: orgA_uid (always a Spine row) absorbs the orgB_uid company.
    """
    spine = pd.read_csv(release_dir / "TSCS_spine.spine.csv", dtype=str, keep_default_na=False,
                        usecols=["uid"])["uid"]
    own = set(spine[spine.str.startswith("GB-COH-")].str[len("GB-COH-"):])
    m = pd.read_csv(release_dir / "TSCS_spine.matches.csv", dtype=str, keep_default_na=False,
                    usecols=["orgA_uid", "orgB_uid"])
    m = m[m["orgB_uid"].str.startswith("GB-COH-") & (m["orgA_uid"] != m["orgB_uid"])]
    folded = m.groupby(m["orgB_uid"].str[len("GB-COH-"):])["orgA_uid"].agg(set).to_dict()
    return own, folded


def load_catalogue(key: str, work_dir: Path) -> pd.DataFrame:
    """Combined GB-NIC catalogue for all years, cached to work/catalogue_gb_nic.csv."""
    path = work_dir / "catalogue_gb_nic.csv"
    if path.exists():
        return pd.read_csv(path, dtype=str, keep_default_na=False)
    rows: list[dict] = []
    for y in CATALOGUE_YEARS:
        rows += get(f"/catalogue/year/{y}?jurisdiction={JURISDICTION}", key)["accounts"]
    cols = ["doc_id", "jurisdiction", "charity_number", "year_end_date", "file_size"]
    cat = pd.DataFrame(rows).reindex(columns=cols).astype(str)
    # charity number taken from doc_id ("GB-NIC/101307/2025-03-31") so it matches the Spine's bare form
    cat["charity_number"] = cat["doc_id"].str.split("/").str[1]
    write_csv_atomic(cat, path)
    return cat


def latest_docs(catalogue: pd.DataFrame, targets: pd.DataFrame) -> pd.DataFrame:
    """Most recent accounts per charity, inner-joined to targets."""
    latest = (catalogue.sort_values(["charity_number", "year_end_date"])
              .drop_duplicates("charity_number", keep="last")[["charity_number", "doc_id", "year_end_date"]])
    return targets.merge(latest, on="charity_number", how="inner")


def doc_path(work_dir: Path, charity_number: str, year_end_date: str) -> Path:
    return work_dir / "docs" / f"{charity_number}_{year_end_date}.md"


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


def extract_all(docs: pd.DataFrame, work_dir: Path) -> pd.DataFrame:
    """One row per (charity, distinct number) across all cached documents."""
    rows: list[dict] = []
    for r in docs.itertuples(index=False):
        path = doc_path(work_dir, r.charity_number, r.year_end_date)
        if not path.exists():
            continue
        found = extract_company_numbers(path.read_text(encoding="utf-8", errors="replace"))
        for f in found:
            rows.append({"uid": r.uid, "charity_number": r.charity_number, "charity_name": r.organisationname,
                         "charity_postcode": r.postcode, "charity_removeddate": r.removeddate,
                         "doc_id": r.doc_id, "year_end_date": r.year_end_date, "company_number": f["number"],
                         "n_mentions": f["n_mentions"], "keyword_context": f["keyword_context"],
                         "n_distinct_numbers_in_doc": len(found), "snippet": f["snippet"]})
    cols = ["uid", "charity_number", "charity_name", "charity_postcode", "charity_removeddate", "doc_id",
            "year_end_date", "company_number", "n_mentions", "keyword_context", "n_distinct_numbers_in_doc", "snippet"]
    return pd.DataFrame(rows, columns=cols)


def lookup_companies_house(numbers: set[str], keys: list[str], work_dir: Path) -> tuple[pd.DataFrame, int, int]:
    """Company profile for every candidate number via the CH API, cached to work/ch_profiles/.

    Resumable: cached numbers (including 404s, cached as _not_found) are never re-requested.
    Returns (register details for numbers found, lookups made this run, failures).
    """
    # ponytail: sequential requests; a few thousand lookups at ~0.5s each is fine. Add a thread
    # per key if this ever has to cover tens of thousands of numbers.
    cache = work_dir / "ch_profiles"
    cache.mkdir(parents=True, exist_ok=True)
    todo = sorted(n for n in numbers if not (cache / f"{n}.json").exists())
    free_at = [0.0] * len(keys)
    failures: list[dict] = []
    fetched = 0
    for i, n in enumerate(todo, 1):
        try:
            profile = ch_get(n, keys, free_at) or {"_not_found": True, "company_number": n}
            write_text_atomic(cache / f"{n}.json", json.dumps(profile))
            fetched += 1
        except (urllib.error.URLError, TimeoutError, OSError, RuntimeError, ValueError) as e:
            failures.append({"company_number": n, "error": f"{type(e).__name__}: {e}"})
        if i % PROGRESS_EVERY == 0:
            print(f"  CH lookups {i:,}/{len(todo):,} (new {fetched:,}, failed {len(failures):,})", flush=True)
    write_csv_atomic(pd.DataFrame(failures, columns=["company_number", "error"]), work_dir / "ch_lookup_failures.csv")

    cols = ["ch_company_name", "company_number", "ch_status", "ch_incorporation_date", "ch_dissolution_date",
            "ch_postcode", "ch_address", "ch_company_type"]
    address_keys = ("address_line_1", "address_line_2", "locality", "region", "postal_code")
    rows: list[dict] = []
    for n in sorted(numbers):
        path = cache / f"{n}.json"
        if not path.exists():
            continue
        d = json.loads(path.read_text(encoding="utf-8"))
        if d.get("_not_found"):
            continue
        office = d.get("registered_office_address") or {}
        rows.append({"ch_company_name": d.get("company_name", ""), "company_number": n,
                     "ch_status": d.get("company_status", ""), "ch_incorporation_date": d.get("date_of_creation", ""),
                     "ch_dissolution_date": d.get("date_of_cessation", ""),
                     "ch_postcode": office.get("postal_code", ""),
                     "ch_address": ", ".join(str(office.get(k) or "").strip() for k in address_keys
                                             if str(office.get(k) or "").strip()),
                     "ch_company_type": d.get("type", "")})
    return pd.DataFrame(rows, columns=cols), fetched, len(failures)


def same_as_charity_number(company_number: str, charity_number: str) -> bool:
    """True when the 'company number' is just the charity number with an NI/R0 prefix (e.g. NI110229 vs 110229)."""
    digits = re.sub(r"^(NI|R0)", "", str(company_number)).lstrip("0")
    return digits == str(charity_number).lstrip("0")


def score(cands: pd.DataFrame, ch: pd.DataFrame, links: pd.DataFrame,
          own_rows: set[str], folded: dict[str, set[str]]) -> pd.DataFrame:
    """Join register details, compute name/postcode/other-link/Spine evidence and confidence."""
    already_linked = links.groupby("orgB_id_in_source")["orgA_uid"].agg(set).to_dict()
    df = cands.merge(ch, on="company_number", how="left")
    df["is_own_charity_number"] = [same_as_charity_number(n, c)
                                   for n, c in zip(df["company_number"], df["charity_number"])]
    df["in_ch_register"] = df["company_number"].isin(set(ch["company_number"]))
    df["name_similarity"] = [round(difflib.SequenceMatcher(None, normalise_name(a), normalise_name(b)).ratio(), 3)
                             if reg else 0.0 for a, b, reg in zip(df["charity_name"], df["ch_company_name"].fillna(""),
                                                                   df["in_ch_register"])]
    df["postcode_match"] = [bool(normalise_postcode(a)) and normalise_postcode(a) == normalise_postcode(b)
                            for a, b in zip(df["charity_postcode"], df["ch_postcode"].fillna(""))]
    df["linked_to_other_charity"] = [",".join(sorted(already_linked.get(n, set()) - {u}))
                                     for n, u in zip(df["company_number"], df["uid"])]
    df["company_spine_row"] = df["company_number"].isin(own_rows)
    df["folded_into"] = [",".join(sorted(folded.get(n, set()) - {u}))
                         for n, u in zip(df["company_number"], df["uid"])]
    df["implication"] = ["dedup: company has own Spine row" if own
                         else "conflict: folded into other Spine org" if fold
                         else "enrich: company not on Spine" if reg else ""
                         for own, fold, reg in zip(df["company_spine_row"], df["folded_into"], df["in_ch_register"])]

    def confidence(r) -> str:
        if not r.in_ch_register or r.linked_to_other_charity or r.folded_into or r.is_own_charity_number:
            return "low"
        strong = r.name_similarity >= NAME_SIMILARITY_HIGH or r.postcode_match
        specific = r.n_distinct_numbers_in_doc == 1 or r.keyword_context
        return "high" if strong and specific else "medium"

    df["confidence"] = [confidence(r) for r in df.itertuples(index=False)]
    n_high = df[df["confidence"] == "high"].groupby("uid")["uid"].transform("size")
    df.loc[n_high[n_high > 1].index, "confidence"] = "medium"  # ambiguous: >1 high number for one charity
    df = df.sort_values(["confidence", "uid"], key=lambda s: s.map(CONFIDENCE_ORDER) if s.name == "confidence" else s)
    return df.reset_index(drop=True)


def to_matches_schema(scored: pd.DataFrame) -> pd.DataFrame:
    h = scored[scored["confidence"] == "high"]
    return pd.DataFrame({"uid": h["uid"], "orgA_id_in_source": h["charity_number"], "orgA_source": "ccni",
                         "orgA_uid": h["uid"], "orgB_id_in_source": h["company_number"], "orgB_source": "CH",
                         "orgB_uid": "GB-COH-" + h["company_number"], "match_type": MATCH_TYPE})


def main() -> None:
    ap = argparse.ArgumentParser(description="Find NI company numbers in unlinked charities' latest accounts.")
    ap.add_argument("--release-dir", type=Path, default=RELEASE_DIR)
    ap.add_argument("--ch-keys", type=Path, default=CH_KEYS, help="Companies House API keys file")
    ap.add_argument("--api-keys", type=Path, default=API_KEYS)
    ap.add_argument("--work-dir", type=Path, default=WORK_DIR)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--limit", type=int, default=None, help="process only the first N targets with a document")
    a = ap.parse_args()
    a.work_dir.mkdir(parents=True, exist_ok=True)
    a.out_dir.mkdir(parents=True, exist_ok=True)
    key = json.loads(a.api_keys.read_text())["prod"]  # never printed or logged
    ch_keys = load_ch_keys(a.ch_keys)  # never printed or logged

    links = load_ccni_ch_links(a.release_dir)
    targets = load_targets(a.release_dir, links)
    print(f"targets (NI charities with no company link): {len(targets):,}", flush=True)
    docs = latest_docs(load_catalogue(key, a.work_dir), targets)
    n_with_doc = len(docs)
    if a.limit:
        docs = docs.head(a.limit)
    print(f"targets with a document: {n_with_doc:,}; processing {len(docs):,}", flush=True)

    fetched, n_failed = fetch_docs(docs, key, a.work_dir)
    cands = extract_all(docs, a.work_dir)
    print(f"candidate rows: {len(cands):,}; looking up Companies House profiles "
          f"({len(ch_keys)} keys)...", flush=True)
    ch, ch_fetched, ch_failed = lookup_companies_house(set(cands["company_number"]), ch_keys, a.work_dir)
    scored = score(cands, ch, links, *spine_presence(a.release_dir))
    matches = to_matches_schema(scored)

    write_csv_atomic(scored, a.out_dir / "ni_company_number_candidates.csv")
    write_csv_atomic(matches, a.out_dir / "ni_company_number_matches.csv")
    summary = {
        "targets": len(targets),
        "targets_with_doc": n_with_doc,
        "targets_without_doc": len(targets) - n_with_doc,
        "processed": len(docs),
        "docs_fetched_this_run": fetched,
        "docs_fetched": sum(doc_path(a.work_dir, c, y).exists() for c, y in zip(docs["charity_number"], docs["year_end_date"])),
        "fetch_failures": n_failed,
        "docs_with_any_number": int(cands["uid"].nunique()),
        "candidate_rows": len(scored),
        "ch_lookups_this_run": ch_fetched,
        "ch_lookup_failures": ch_failed,
        "in_register": int(scored["in_ch_register"].sum()),
        "by_confidence": {c: int((scored["confidence"] == c).sum()) for c in CONFIDENCE_ORDER},
        **{f"{c}_by_implication": {k: int(v) for k, v in
                                   scored.loc[scored["confidence"] == c, "implication"].value_counts().items()}
           for c in ("high", "medium")},
        "charities_with_high": int(matches["uid"].nunique()),
    }
    write_text_atomic(a.out_dir / "run_summary.json", json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
