"""Financial figures from FCA mutual society annual returns (AR30, AR41) in the Braw corpus.

Standalone enhancement. FETCH stage: builds the GB-MPR catalogue of the Braw corpus API (every
return per society, i.e. a panel) and caches each return's markdown text under work/docs/.
EXTRACT stage: regex-only reading of modern AR30 section 4.2 (six figures), the four of those
figures on the older AR30 (Release 3, July 2014) section 2.1, four on the working men's club return
(AR41), six rows of the credit union annual return (CY), and the year-end date from the cached
text (also from the credit union accounts form), plus an optional comparison with the PDF
pipeline's v4 baseline.

Usage: python find_fca_financials.py [--limit 50 | --target 3000] [--no-fetch] [--min-year 2018] [--work-dir ...]
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
ANY_LABEL = re.compile("|".join(p for p, _ in FIELDS.values()), re.I)
MODERN_TITLE = re.compile(r"Annual Return \(AR3\w{0,3}\) for", re.I)  # OCR: "AR3SOQ" (4398), "(AR30O) for" (4079)
NOISE = re.compile(r"Doc\s*ID:\s*(?:[0-9a-f]\s?){30,40}"  # filed-copy hash, OCR may split it
                   r"|Demo\s*Version\s*-?\s*Select\s*\.?\s*Pdf\s*SDK", re.I)  # PDF-tool watermark
BLOCK_START = re.compile(r"4\W{1,3}2\W*(?:Based\W*)+(?:on\W*)+(?:the\W*)+a?ccounts",
                         re.I)  # OCR: "4,2", "Basedon", "@Ccounts"; 7404 doubles every word ("Based Based on on")
BLOCK_END = re.compile(r"4\.3\s+What\s+Standard", re.I)
SECTION4 = re.compile(r"Section\W*4\W*Financial", re.I)  # block start when OCR lost the 4.2 heading (4681R)
EMPTY_CELL = "¤"  # stands in for an empty last table cell ("|Number of employees (if any)||"), 829RS
MAX_BLOCK = 3000  # characters; used when "4.3 What Standard" is missing or OCR-garbled
FOOTER = re.compile(r"(?:FCA.{0,6}?)?Mutua\S*\s+Annua\S*\s+Return\s*\(AR3\w*\).{0,30}?Release\s*\d+"
                    r".{0,6}?[A-Za-z]+\s+\d{4}", re.I)
PAGE = re.compile(r"Page\s*\d+(?:\s*of\s*\d+)?", re.I)
IF_ANY = re.compile(r"\(\s*if\s*any\s*\)", re.I)
TICK_BOX = re.compile("[☒☐]")  # tick boxes of the fillable PDF form; OCR never emits them
OCR_MARK = re.compile(r"^-\s+e\s+(?:this|a\s?set)\b"  # page-1 bullets read as "e"
                      r"|FCA\W{0,3}[@®©e]\W{0,3}Mutuals"  # footer bullet read as @, ®, ©, e
                      r"|\.orq\.uk", re.M)  # "fca.org.uk" read as "fca.orq.uk"
YEAR_END_Q = re.compile(r"\d\.\d\s*What\s+date\s+did\s+the\s+financial\s+year\s+covered\s+by\s+these\s+"
                        r"accounts\s+end\?", re.I)
TOKEN = re.compile(r"£?\s*\(?\d+(?:[.,]\s?\d+)*\)?%?|\S+")  # "64, 205" stays one token, "12741 0" is two
OK_STATUSES = {"parsed", "nil", "not_applicable", "not_on_form"}
AR41 = re.compile(r"AR\s?41")  # 422W writes "AR 41"
AR5 = re.compile(r"A\.\s?R\.\s?5|FORM\W{0,3}AR\W?[5S]\b"  # OCR: "FORM AR.S", "FORMARS" (104BEN)
                 r"|SPECIALLY\s+AUTHORISED\s+SOCIETY")  # printed header, when the form number is lost (157SA)
CU_HEAD = 3000  # characters: a credit union names itself on its cover page; building and friendly
# societies mention credit unions only deeper in their accounts (108B, 218F)
CU_YEAR_END_Q = re.compile(r"On\s*what\s*date\s*did\s*the\s*financial\s*year\s*in\s*these\s*accounts\s*end\?", re.I)

# Credit union annual return (CY): "label | value | row code" rows, e.g. "||Total assets||4,225,676|C16|";
# scans glue the code to the value ("2,200,000B5") or misread it ("Att" for A11).
CY_TITLE = re.compile(r"Annual\s*return\s*\(CY\)\s*for\s*credit", re.I)  # not the "(CY) - Auditor's statement"
CY_ONLINE = re.compile(r"\*\*Return\s*Details:\*\*.{0,1000}?" + CY_TITLE.pattern, re.I | re.S)  # web-form text; OCR loses the bold
CY_YEAR_END_Q = re.compile(r"Return\s*End\s*Date:?", re.I)
CY_FIELDS = {  # field -> (row code, label at the start of its cell, used when OCR lost the code)
    "number_of_members": ("A2", r"Number\s*of\s*members\s*at\s*the\s*financial\s*year\W*end"),
    "turnover": ("J13", r"Total\s*income"),
    "assets": ("C16", r"Total\s*assets"),
    "number_of_employees": ("A11", r"Total\s*number\s*of\s*staff"),
    "share_capital": ("G1", r"Members\W*share\s*balances\s*\(total\)"),
    "highest_rate_interest_paid_on_shares": ("L5", r"Rate\s*of\s*dividend"),
}
NUM = r"\(?-?\d[\d,]*(?:\.\d+)?\)?"

# Older AR30 (Release 3, July 2014): lettered rows A-T under "2.1 You must enter the figures below",
# ending at "2.2 Names of subsidiaries". Four rows feed the output fields; employees and the share
# interest rate are not asked on this form (status not_on_form).
R3_FOOTER = re.compile(r"Release\s*3.{0,10}July\s*20\d\d", re.I)  # page footer; OCR: "July 2074"
R3_START = re.compile(r"must\s*enter\s*the\s*figures", re.I)  # OCR: "Yo Se|umustenterthe figures"
R3_START_FALLBACK = re.compile(r"2\s+Statistics", re.I)  # 4161: the 2.1 heading is lost in picture text
R3_END = re.compile(r"2\W{0,3}2\W*Names", re.I)
R3_FIELDS = {  # field -> label of its row
    "number_of_members": r"members\s*at\s*end\s*of\s*year",  # D
    "turnover": r"tu(?:rn|m)\s*over(?:\s*for\s*(?:the\s*)?year)?",  # E; OCR "Tumover"
    "assets": r"total\s*assets(?:[\s*]*\([^|\d)]*\)?)*",  # J "(equal to amount in row O, below)"; AR41 G "(E+F) (equal..."
    "share_capital": r"(?<!,)(?<!,\s)share\s*capital(?!\s*&)",  # L, not O "liabilities, share capital &"
}
R3_YEAR_END_Q = re.compile(r"Year\s*end\s*date\s*\([^)\n]{0,15}\)\W*(?:See\s*Note\s*1\W{1,7}2)?", re.I)

# AR41 (working men's clubs). Release 2/3 paper and the online web form: rows A-L under the 4.2
# heading (BLOCK_START), ending at "5.1 Please select the audit option" or "Section 5". Release 1
# paper (April 2013): the same rows without L (employees) under "2.1 You must enter the figures
# below" (R3_START), ending at "3 The audit" / "3.1 Type of audit". Rows read: A members, B turnover
# (never C "Total income and expenditure"), G total assets, L employees.
AR41_FIELDS = {**{f: R3_FIELDS[f] for f in ("number_of_members", "turnover", "assets")},
               "number_of_employees": r"number\s*of\s*employees"}
AR41_END = re.compile(r"5\W{1,3}1\W*Please|Section\s*5", re.I)
AR41_R1_END = re.compile(r"3\W{0,3}(?:1\W*Type\s*of|The)\s*audit", re.I)
AR41_FOOTER = re.compile(r"Mutuals\W*AR\s?4\d\W*Wor\w*\s*Men", re.I)  # paper footer; OCR "AR 44", "Workina"
AR41_ONLINE = re.compile(r"Enter\W*0\W*where", re.I)  # web form guidance; paper says "Enter 'NIL'"
AR41_R1_YEAR_END_Q = re.compile(r"1\.2\s*Year\s*end\s*date\W*(?:Please\s*enter\s*year\s*below)?", re.I)
PICTURE = re.compile(r"<!--\s*Start of picture text\s*-->.*?<!--\s*End of picture text\s*-->", re.S | re.I)


def classify(text: str) -> str:
    """Modern AR30 is checked first: 2619RS (2020) holds a modern return and a 2014 copy."""
    if ((MODERN_TITLE.search(text) or FOOTER.search(text)) and not AR41.search(text)
            and (BLOCK_START.search(text) or SECTION4.search(text) or BLOCK_END.search(text))):
        return "ar30_modern"  # FOOTER: title page lost (122IP); SECTION4 / BLOCK_END: 4.2 heading lost (4681R, 8272R)
    if re.search(r"4\W{0,6}2\W*Has\s*your\s*society", text, re.I) or R3_FOOTER.search(text):
        return "ar30_2014"  # footer: 1159R, 4161, 1821RS, 7192, 7512 have a garbled "4.2 Has"
    if AR41.search(text):
        return "ar41"
    if AR5.search(text):
        return "ar5"
    if CY_TITLE.search(text):
        return "cu_cy_return"
    if re.search(r"credit\s+union", text[:CU_HEAD], re.I):
        return "credit_union"
    return "other"


def find_block(text: str, end_pattern: re.Pattern = BLOCK_END, start: re.Pattern = BLOCK_START) -> tuple[str, int]:
    """Raw text of the FIRST section 4.2 block and its end position in the document."""
    m = start.search(text)
    if not m:
        return "", 0
    end = end_pattern.search(text, m.end())
    stop = min(end.start() if end else len(text), m.end() + MAX_BLOCK)
    return text[m.end():stop], stop


def layout_of(text: str, block: str, block_end: int, ar41: bool = False) -> str:
    """online (web form), filled (PDF form typed into: tick boxes, no OCR marks) or scanned (paper
    form read by OCR; also any paper form with neither marker). Only text up to the end of the
    first block is looked at: 4253R has an online copy followed by a scanned one. AR41: online
    needs no paper footer and the "Enter '0'" guidance; filled needs the paper footer."""
    head = text[:block_end]
    if ar41:
        if not AR41_FOOTER.search(head):
            return "online" if AR41_ONLINE.search(head) else "scanned"
    elif not (IF_ANY.search(block) or FOOTER.search(head) or R3_FOOTER.search(head)):
        return "online"
    return "filled" if TICK_BOX.search(head) and not OCR_MARK.search(head) else "scanned"


def find_block_2014(text: str, end_pattern: re.Pattern = R3_END) -> tuple[str, int]:
    """Raw text of section 2.1 of the 2014 form (or AR41 Release 1) and its end position. With no
    block the end is the end of the document, so layout_of still sees the paper footers."""
    m = R3_START.search(text) or R3_START_FALLBACK.search(text)
    if not m:
        return "", len(text)
    end = end_pattern.search(text, m.end())
    stop = min(end.start() if end else len(text), m.end() + MAX_BLOCK)
    return text[m.end():stop], stop


def value_tokens(s: str) -> list[str]:
    return [t.strip() for t in TOKEN.findall(normalise_block(s)) if any(c.isalnum() for c in t)]


def fields_by_row(block: str, patterns: dict[str, str]) -> dict[str, str]:
    """Raw value text for each labelled row (field -> label pattern) found in a block: the 2014
    form's section 2.1 (R3_FIELDS) or AR41 rows (AR41_FIELDS).

    Rows are table lines or picture-text lines (split at <br>); no two rows shared a line in the
    2014 sample. The value is the rest of the row after the label (its last match: OCR sometimes
    repeats a label, 405IP); if that is empty, the next line with text, when it holds no letters
    (online AR41 such as 1096W puts the value under the label). A label on more than one row
    gives every value joined with " / ", which parse_value sends to review.
    """
    rows = re.split(r"\n|<br>", block)
    out: dict[str, str] = {}
    for field, pattern in patterns.items():
        vals = []
        for i, r in enumerate(rows):
            ms = list(re.finditer(pattern, r, re.I))
            if ms:
                toks = value_tokens(r[ms[-1].end():])
                if not toks:
                    nxt = next((t for t in map(value_tokens, rows[i + 1:]) if t), [])
                    toks = [] if any(c.isalpha() for t in nxt for c in t) else nxt
                vals.append(" ".join(toks))
        if vals:
            out[field] = " / ".join(vals)
    return out


def ar41_sequence(block: str) -> dict[str, str] | None:
    """Online AR41 prints the labels apart from the values (1001W). After the "Enter '0' where
    applicable" guidance, with picture text dropped (it can repeat values: 1097W), the numbers are
    rows A-L in order. Used only when there are exactly 12 and the form's own totals hold
    (G = K and E + F = G); otherwise None and the rows are matched by label instead."""
    g = re.search(r"where\s*applicable", block, re.I)
    nums = [t for t in value_tokens(PICTURE.sub(" ", block[g.end():] if g else block)) if re.search(r"\d", t)]
    if len(nums) != 12:
        return None
    v = [parse_value(n, "GBP", True) for n in (nums[4], nums[5], nums[6], nums[10])]
    if any(st not in {"parsed", "nil"} for _, st in v):
        return None
    e, f, total, k = (Decimal(x) for x, _ in v)
    if not e + f == total == k:
        return None
    return {"number_of_members": nums[0], "turnover": nums[1], "assets": nums[6], "number_of_employees": nums[11]}


def cy_value(rows: list[str], code: str, label: str = "") -> str:
    """Raw number on a credit union CY row: the first one written just before its row code
    ("1,402|A2", "5,981,493.01C16"); failing that, the number just after the label at the start
    of a cell (code misread by OCR: "|Total number of staff||2|Att|")."""
    pats = [rf"({NUM})\W*{code}(?!\d)"] + [rf"(?:^|\|)[^A-Za-z|]*(?i:{label})\W*({NUM})"] * bool(label)
    for pat in pats:
        m = next((m for r in rows if (m := re.search(pat, r))), None)
        if m:
            return m[1]
    return ""


def cu_totals_check(rows: list[str]) -> str:
    """pass when the CY return's own sums hold: C16 - D12 = E1 (total assets less total liabilities
    = net assets) and J13 - K18 = L1 (total income less total expenditure = profit before tax),
    each checked only where all three figures read; fail if one does not; blank if neither reads."""
    held = []
    for codes in (("C16", "D12", "E1"), ("J13", "K18", "L1")):
        v = [parse_value(cy_value(rows, c), "GBP", False) for c in codes]
        if all(st in {"parsed", "nil"} for _, st in v):
            a, b, c = (Decimal(x) for x, _ in v)
            held.append(a - b == c)
    return "" if not held else "pass" if all(held) else "fail"


def normalise_block(block: str) -> str:
    s = re.sub(r"\|[ \t]*\|[ \t]*$", f"| {EMPTY_CELL} |", block, flags=re.M)  # row ends in an empty cell
    s = re.sub(r"<[^>]*>|[*|#_\"]", " ", s)  # <br>, comments, bold, table pipes, headings
    s = NOISE.sub(" ", PAGE.sub(" ", FOOTER.sub(" ", s)))
    s = re.sub(r"(?:paid\s*)?on\s*shares", " ", IF_ANY.sub(" ", s), flags=re.I)
    return " ".join(s.split())


def field_tokens(block: str) -> dict[str, str]:
    """Raw value text for each field found in a normalised block.

    Tokens between a label and the next found label belong to it. A label with no token waits
    (stacked labels, 6365R): the next non-empty run fills waiting labels in order. Fewer tokens
    than waiting labels go to the nearest labels; surplus tokens are kept on the last label so
    the value goes to review instead of silently losing digits. A label whose table row ends in an
    empty cell (EMPTY_CELL) and nothing else before the next label is blank on the form: it does
    not wait, so it never borrows the next row's value (829RS).
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
        nxt = hits[i + 1][1] if i + 1 < len(hits) else ANY_LABEL.search(block, m.end())  # 1284RS repeats a label
        stop = nxt.start() if nxt else len(block)
        toks = [t.strip() for t in TOKEN.findall(block, m.end(), stop) if any(c.isalnum() for c in t) or t == EMPTY_CELL]
        if toks and set(toks) == {EMPTY_CELL}:
            continue
        toks = [t for t in toks if t != EMPTY_CELL]
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


def parse_value(raw: str, unit: str, typed: bool) -> tuple[str, str]:
    """(normalised value, status) for one raw token. Mirrors ar30_financials._parse_value.
    typed = online or filled layout (not OCR), where a letter or word zero can be trusted."""
    s = raw.replace("**", "").strip()
    if not s:
        return "", "missing"
    if re.fullmatch(r"N/?A|NOT\s+APPLICABLE", s, re.I):
        return "-9", "not_applicable"  # missing-data code, not a measurement
    if re.fullmatch(r"N\s*[Il1|]\s*L|NONE", s, re.I):
        return "0", "nil"
    if re.fullmatch(r"o{1,2}%?|zero", s, re.I):  # letter O or "Zero"; trusted only when typed, not OCR
        return ("0", "nil") if typed else ("", "review")
    if unit == "percent" and "£" in s:
        return "", "review"
    if re.search(r"\d\s*£", s):  # "1£179,522": AR41 box border read as a 1
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


def year_end_on_form(text: str, question: re.Pattern = YEAR_END_Q) -> str:
    """ISO date answered to "2.1 What date did the financial year ... end?" (or, with
    R3_YEAR_END_Q, the 2014 form's "1.2 Year end date (dd/mm/yyyy)"; credit unions: CY_YEAR_END_Q,
    CU_YEAR_END_Q), or blank.

    Online forms give dd/mm/yyyy (sometimes in a table cell); filled PDFs give eight digit boxes
    ("3 1 1 2 2 0 2 1"; the 2014 form "3 1 / 1 2 / 2 0 2 1"), on the next line or the same line.
    Scanned forms are usually garbage.
    """
    m = question.search(text)
    if not m:
        return ""
    after = re.sub(r"<[^>]*>|[*|#]", " ", text[m.end():m.end() + 150]).strip()
    d = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})\b", after)
    b = re.match(r"(\d)\s*(\d)\s*/?\s*(\d)\s*(\d)\s*/?\s*(\d)\s*(\d)\s*(\d)\s*(\d)\b", after)
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
    """Form type, layout, year-end and the six figures (modern section 4.2; the four on the 2014
    form's section 2.1; AR41 rows A, B, G, L; credit union CY rows, see CY_FIELDS) for one
    document. ar41_totals_check is pass/fail on online AR41 (see ar41_sequence), blank otherwise;
    cu_totals_check likewise for the CY return (see cu_totals_check)."""
    row: dict = {"form_type": classify(text), "layout": "", "year_end_on_form": ""}
    for f in FIELDS:
        row.update({f: "", f"{f}_status": "", f"{f}_raw": ""})
    row.update({"ar41_totals_check": "", "cu_totals_check": "", "confidence": ""})
    if row["form_type"] == "ar30_modern":
        block, block_end = find_block(text)
        if not block_end:  # 4.2 heading lost to OCR: from "Section 4 - Financial information", else no block
            block, block_end = find_block(text, start=SECTION4)
            block_end = block_end or len(text)  # so layout_of still sees the paper footers
        row["year_end_on_form"] = year_end_on_form(text)
        row["layout"] = layout_of(text, block, block_end)
        fields, raws = FIELDS, field_tokens(normalise_block(block))
    elif row["form_type"] == "ar30_2014":
        block, block_end = find_block_2014(text)
        row["year_end_on_form"] = year_end_on_form(text, R3_YEAR_END_Q)
        row["layout"] = layout_of(text, block, block_end)
        fields, raws = R3_FIELDS, fields_by_row(block, R3_FIELDS)
    elif row["form_type"] == "ar41":
        block, block_end = find_block(text, AR41_END)
        if block_end or not R3_START.search(text):  # Release 2/3 paper or online; or no figures (missing)
            fields = AR41_FIELDS
            row["year_end_on_form"] = year_end_on_form(text)
        else:  # Release 1 paper: no employees row
            block, block_end = find_block_2014(text, AR41_R1_END)
            fields = {f: p for f, p in AR41_FIELDS.items() if f != "number_of_employees"}
            row["year_end_on_form"] = year_end_on_form(text, AR41_R1_YEAR_END_Q)
        row["layout"] = layout_of(text, block, block_end, ar41=True)
        seq = ar41_sequence(block) if row["layout"] == "online" else None
        if row["layout"] == "online":
            row["ar41_totals_check"] = "pass" if seq else "fail"
        raws = seq or fields_by_row(block, fields)
    elif row["form_type"] == "cu_cy_return":
        m = CY_ONLINE.search(text) or CY_TITLE.search(text)  # the web-form copy if any: 116CU has a scan first
        assert m  # classify found the title
        row["layout"] = "online" if m.re is CY_ONLINE else "scanned"
        row["year_end_on_form"] = year_end_on_form(text, CY_YEAR_END_Q)  # header sits before the title on scans
        rows = re.split(r"\n|<br>", text[m.start():])
        row["cu_totals_check"] = cu_totals_check(rows)
        fields, raws = CY_FIELDS, {f: cy_value(rows, *CY_FIELDS[f]) for f in CY_FIELDS}
    elif row["form_type"] == "credit_union":  # accounts form: a cover page and the accounts, no figures asked
        row["year_end_on_form"] = year_end_on_form(text, CU_YEAR_END_Q)
        row.update({f"{f}_status": "not_on_form" for f in FIELDS})
        return row
    else:
        return row
    for f, (_, unit) in FIELDS.items():
        if f not in fields:
            row[f"{f}_status"] = "not_on_form"
            continue
        row[f"{f}_raw"] = raws.get(f, "")
        row[f], row[f"{f}_status"] = parse_value(row[f"{f}_raw"], unit, row["layout"] != "scanned")
    ok = (all(row[f"{f}_status"] in OK_STATUSES for f in FIELDS) and row["ar41_totals_check"] != "fail"
          and (row["form_type"] != "cu_cy_return" or row["cu_totals_check"] == "pass"))
    row["confidence"] = "high" if row["layout"] in {"online", "filled"} and ok else "review"
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
                     **{f"{f}_raw": e[f"{f}_raw"] for f in FIELDS}, "ar41_totals_check": e["ar41_totals_check"],
                     "cu_totals_check": e["cu_totals_check"], "confidence": e["confidence"]})
    cols = (["uid", "society_number", "doc_id", "catalogue_year_end", "form_type", "layout",
             "year_end_on_form", "year_end_matches_catalogue"]
            + [k for f in FIELDS for k in (f, f"{f}_status")] + [f"{f}_raw" for f in FIELDS]
            + ["ar41_totals_check", "cu_totals_check", "confidence"])
    return pd.DataFrame(rows, columns=cols)


def baseline_documents(baseline_dir: Path) -> pd.DataFrame:
    """The PDF pipeline's modern, releasable returns, one per (society number, year end)."""
    parse = pd.read_csv(baseline_dir / "parser-v4-parse.csv", dtype=str, keep_default_na=False,
                        usecols=["fca_registration_number", "fca_document_id", "document_date",
                                 "form_version", "release_status"])
    parse = parse[(parse["form_version"] == "modern") & (parse["release_status"] == "releasable")]
    return parse.drop_duplicates(["fca_registration_number", "document_date"], keep="first")


def baseline_keys(baseline_dir: Path) -> set[tuple[str, str]]:
    """(society number, year end) of each baseline return; empty if the folder is absent."""
    if not baseline_dir.exists():
        return set()
    b = baseline_documents(baseline_dir)
    return set(zip(b["fca_registration_number"], b["document_date"]))


def select_target(catalogue: pd.DataFrame, cached: list[bool], n: int) -> pd.DataFrame:
    """First n of: every cached row, then rows matching a baseline return (needs a
    `matches_baseline` column), then a seeded random fill. Adds `selected_as`."""
    is_cached = pd.Series(cached, index=catalogue.index)
    base = catalogue["matches_baseline"]
    return pd.concat([catalogue[is_cached].assign(selected_as="cached"),
                      catalogue[~is_cached & base].assign(selected_as="baseline"),
                      catalogue[~is_cached & ~base].sample(frac=1, random_state=SAMPLE_SEED)
                      .assign(selected_as="random")]).head(n)


def compare_baseline(ours: pd.DataFrame, baseline_dir: Path) -> pd.DataFrame:
    """Long table of our values against the PDF pipeline's parsed values, matched on
    (society number, year end). Only fields the baseline parsed are compared."""
    parse = baseline_documents(baseline_dir)
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


def form_summary(d: pd.DataFrame) -> dict:
    return {
        "by_layout": d["layout"].value_counts().to_dict(),
        "by_confidence": d["confidence"].value_counts().to_dict(),
        "year_end_matches_catalogue": d["year_end_matches_catalogue"].replace("", "blank")
        .value_counts().to_dict(),
        "field_status": {f: d[f"{f}_status"].value_counts().to_dict() for f in FIELDS},
    }


def run_summary(out: pd.DataFrame) -> dict:
    """Counts for all documents; layout, confidence, year-end and field status for modern AR30
    at the top level, for the 2014 form under "ar30_2014" and for AR41 under "ar41" (with the
    online totals check) and for the credit union CY return under "cu_cy_return"."""
    ar41 = out[out["form_type"] == "ar41"]
    cy = out[out["form_type"] == "cu_cy_return"]
    return {
        "documents_extracted": len(out),
        "by_selected_as": out["selected_as"].value_counts().to_dict(),
        "matches_baseline": int(out["matches_baseline"].sum()),
        "by_form_type": out["form_type"].value_counts().to_dict(),
        **form_summary(out[out["form_type"] == "ar30_modern"]),
        "ar30_2014": form_summary(out[out["form_type"] == "ar30_2014"]),
        "ar41": {**form_summary(ar41), "online_totals_check": ar41.loc[ar41["layout"] == "online",
                                                                        "ar41_totals_check"].value_counts().to_dict()},
        "cu_cy_return": {**form_summary(cy), "totals_check": cy["cu_totals_check"].replace("", "blank")
                         .value_counts().to_dict()},
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch FCA mutual society annual returns and extract AR30/AR41 financial figures.")
    ap.add_argument("--api-keys", type=Path, default=API_KEYS)
    ap.add_argument("--work-dir", type=Path, default=WORK_DIR)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--baseline-dir", type=Path, default=BASELINE_DIR,
                    help="PDF pipeline v4 build audit; the comparison is skipped if the folder is absent")
    ap.add_argument("--no-fetch", action="store_true",
                    help="extract from cached documents only (needs a cached catalogue; uncached rows skipped)")
    ap.add_argument("--min-year", type=int, default=MIN_YEAR, help="first catalogue year (default 2018)")
    size = ap.add_mutually_exclusive_group()
    size.add_argument("--limit", type=int, default=None,
                      help="process a reproducible random sample of N catalogue rows (spans years)")
    size.add_argument("--target", type=int, default=None,
                      help="process N rows in total: all cached rows, then baseline matches, then random")
    a = ap.parse_args()
    a.work_dir.mkdir(parents=True, exist_ok=True)
    key = "" if a.no_fetch else json.loads(a.api_keys.read_text())["prod"]  # never printed or logged

    catalogue = load_catalogue(key, a.work_dir, a.min_year)
    n_catalogue = len(catalogue)
    keys = baseline_keys(a.baseline_dir)
    pairs = list(zip(catalogue["charity_number"], catalogue["year_end_date"]))
    catalogue["matches_baseline"] = [k in keys for k in pairs]
    if a.target:
        docs = select_target(catalogue, [doc_path(a.work_dir, *k).exists() for k in pairs], a.target)
        print(f"selected by: {docs['selected_as'].value_counts().to_dict()}", flush=True)
    elif a.limit:
        docs = catalogue.sample(n=min(a.limit, n_catalogue), random_state=SAMPLE_SEED).assign(selected_as="random")
    else:
        docs = catalogue.assign(selected_as="all")
    docs = docs.sort_values("doc_id")
    print(f"catalogue documents: {n_catalogue:,} ({docs['charity_number'].nunique():,} societies in "
          f"selection); processing {len(docs):,}", flush=True)

    if not a.no_fetch:
        fetched, n_failed = fetch_docs(docs, key, a.work_dir)
        print(f"fetched this run: {fetched:,}; failures: {n_failed:,}", flush=True)

    out = extract_docs(docs, a.work_dir)
    sel = docs.set_index("doc_id")
    out.insert(3, "selected_as", out["doc_id"].map(sel["selected_as"]))
    out.insert(4, "matches_baseline", out["doc_id"].map(sel["matches_baseline"]).astype(bool))
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
