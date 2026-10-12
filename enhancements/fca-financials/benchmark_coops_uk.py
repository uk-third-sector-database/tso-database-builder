"""Benchmark our FCA annual return figures (members, turnover, employees) against Co-ops UK open data.

Co-ops UK figures are largely transcribed from the same FCA returns, so agreement checks our
transcription, not the truth. Our rows are joined to Co-ops UK on (society number, exact year end).
No network; reads local files only.

Usage: python benchmark_coops_uk.py [--ours ...] [--catalogue ...] [--orgs ...] [--economy ...] [--out-dir ...]
"""
from __future__ import annotations

import argparse
import json
import math
import re
from decimal import Decimal
from pathlib import Path

import pandas as pd

from find_fca_financials import format_decimal, write_csv_atomic, write_text_atomic  # import has no side effects

SCRIPT_DIR = Path(__file__).resolve().parent
OURS = SCRIPT_DIR / "output" / "fca_ar30_financials.csv"
CATALOGUE = SCRIPT_DIR / "work" / "catalogue_gb_mpr.csv"
ORGS = SCRIPT_DIR / "co-ops-uk-data" / "open_data_organisations_2026_10.csv"
ECONOMY = SCRIPT_DIR / "co-ops-uk-data" / "open_data_economy_2025.csv"
OUT_DIR = SCRIPT_DIR / "output"

COMPARE = {"number_of_members": "Memberships", "turnover": "Turnover", "number_of_employees": "Employees"}
VALUE_STATUSES = {"parsed", "nil"}  # not_applicable ("-9") is a missing-data code, so counts as ours_missing
NEAR_DAYS = 31
SAMPLE_N = 60
SAMPLE_SEED = 42


# ---------- society numbers ----------
def society_key(number: str) -> str:
    """Join key: spaces removed, upper case, leading zeros of the number dropped; suffix KEPT.

    Both sources write the register's own suffixed numbers (1001W, 2619RS, 441IP, 89CU, 7625R;
    4,868 of the 7,020 Co-ops UK FCA numbers carry a suffix, the rest are plain like 4329).
    The suffix marks a separate register, and plain N and NR are different societies (our
    catalogue holds both 4026 and 4026R; stripping a trailing R makes 153 such pairs collide in
    ours and 271 in Co-ops UK), so the suffix cannot be dropped. Neither source showed spaces,
    lower case or leading zeros; normalising them costs nothing.
    """
    return re.sub(r"^0+(?=\d)", "", re.sub(r"\s+", "", str(number)).upper())


def digits_of(key: str) -> str:
    return re.match(r"\d*", key).group(0)  # type: ignore[union-attr]  # \d* always matches


def ambiguous_keys(keys: pd.Series, ids: pd.Series) -> set[str]:
    """Keys that map to more than one distinct id."""
    n = pd.DataFrame({"key": keys.to_numpy(), "id": ids.to_numpy()}).groupby("key")["id"].nunique()
    return set(n[n > 1].index)


# ---------- Co-ops UK economy file ----------
def dedupe_economy(econ: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """One row per (CUK id, year end); rows with no year end dropped. Blank = missing, "0" = a value,
    "123.0" = 123. A field whose non-blank values differ across duplicate rows (stale carry-forward
    across economic years) is flagged {field}_inconsistent and not compared; a blank next to a
    value is not a disagreement (the value is kept)."""
    e = pd.DataFrame({"cuk_id": econ["CUK Organisation ID"].str.strip(),
                      "year_end": pd.to_datetime(econ["Year End Date"].str.strip().str[:10], errors="coerce")
                      .dt.strftime("%Y-%m-%d")})
    for f, col in COMPARE.items():
        e[f] = pd.to_numeric(econ[col].str.replace(",", "").str.strip(), errors="coerce")
    no_ye = e["year_end"].isna()
    g = e[~no_ye].groupby(["cuk_id", "year_end"])
    out = g[list(COMPARE)].first()  # first non-blank value
    n = g[list(COMPARE)].nunique()  # distinct non-blank values
    for f in COMPARE:
        out[f"{f}_inconsistent"] = n[f] > 1
    out = out.reset_index()
    stats = {"economy_rows": len(e), "economy_rows_no_year_end": int(no_ye.sum()),
             "economy_society_years": len(out),
             "economy_society_years_duplicated": int((g.size() > 1).sum()),
             "economy_inconsistent": {f: int(out[f"{f}_inconsistent"].sum()) for f in COMPARE}}
    return out, stats


# ---------- join ----------
def join(ours: pd.DataFrame, catalogue: pd.DataFrame, orgs: pd.DataFrame,
         econ: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Our rows matched to Co-ops UK on (key, exact year end), plus join counts. econ is deduped.
    Ambiguous keys (one key -> several of our catalogue numbers, or several FCA CUK organisations)
    are dropped from both sides."""
    fca = orgs[orgs["Registrar"].str.strip() == "FCA"]
    fca = pd.DataFrame({"key": fca["Registered Number"].map(society_key),
                        "cuk_id": fca["CUK Organisation ID"].str.strip(), "registered_name": fca["Registered Name"]})
    amb_ours = ambiguous_keys(catalogue["charity_number"].map(society_key), catalogue["charity_number"])
    amb_cuk = ambiguous_keys(fca["key"], fca["cuk_id"])
    ours = ours.assign(key=ours["society_number"].map(society_key))
    n_rows, n_societies = len(ours), ours["key"].nunique()
    excluded = ours["key"].isin(amb_ours | amb_cuk)
    ours = ours[~excluded].merge(fca[~fca["key"].isin(amb_cuk)], on="key", how="left")
    in_cuk = ours["cuk_id"].notna()
    matched = ours.merge(econ, left_on=["cuk_id", "catalogue_year_end"], right_on=["cuk_id", "year_end"])

    unmatched = ours[in_cuk & ~ours["doc_id"].isin(matched["doc_id"])]
    near = unmatched.merge(econ[["cuk_id", "year_end"]], on="cuk_id")
    days = (pd.to_datetime(near["catalogue_year_end"], errors="coerce")
            - pd.to_datetime(near["year_end"], errors="coerce")).abs().dt.days
    cuk_digits = set(fca["key"].map(digits_of)) - {""}
    not_in = ours.loc[~in_cuk, "key"].drop_duplicates()
    counts = {
        "our_rows": n_rows, "our_societies": n_societies, "cuk_fca_organisations": len(fca),
        "ambiguous_keys_in_our_catalogue": len(amb_ours), "ambiguous_keys_in_cuk": len(amb_cuk),
        "our_rows_excluded_ambiguous": int(excluded.sum()),
        "our_societies_in_cuk": int(ours.loc[in_cuk, "key"].nunique()),
        "our_societies_not_in_cuk": len(not_in),
        "of_which_number_in_cuk_with_other_suffix": int(not_in.map(digits_of).isin(cuk_digits).sum()),
        "our_rows_society_in_cuk": int(in_cuk.sum()),
        "rows_matched_exact_year_end": len(matched),
        "rows_society_in_cuk_no_year_end_match": len(unmatched),
        "of_which_cuk_year_end_within_31_days": int(near.loc[days <= NEAR_DAYS, "doc_id"].nunique()),
    }
    return matched, counts


# ---------- compare ----------
def outcome(field: str, ours: float, status: str, cuk: float, inconsistent: bool) -> str:
    """Outcome for one field of one matched row (ours and cuk are numbers or NaN)."""
    if status == "not_on_form":
        return "not_on_form"
    if inconsistent:
        return "cuk_inconsistent"
    if pd.isna(cuk):
        return "cuk_missing"
    if status not in VALUE_STATUSES or pd.isna(ours):
        return "ours_missing"
    if round(ours, 2) == round(cuk, 2):
        return "agree_exact"
    if field == "turnover":
        if cuk % 1000 == 0 and math.floor(ours / 1000 + 0.5) * 1000 == cuk:
            return "agree_rounded"
        if abs(ours - cuk) <= 0.01 * abs(cuk):
            return "agree_1pct"
    return "disagree"


def fmt(v: float) -> str:
    return "" if pd.isna(v) else format_decimal(Decimal(str(v)))


def compare(matched: pd.DataFrame) -> pd.DataFrame:
    """One row per matched document: both values and the outcome per field."""
    out = matched[["doc_id", "society_number", "cuk_id", "registered_name", "catalogue_year_end",
                   "form_type", "layout", "confidence"]].copy()
    for f in COMPARE:
        ours_n = pd.to_numeric(matched[f], errors="coerce")
        out[f"ours_{f}"] = matched[f]
        out[f"ours_{f}_status"] = matched[f"{f}_status"]
        out[f"cuk_{f}"] = matched[f"{f}_cuk"].map(fmt)
        out[f"{f}_outcome"] = [outcome(f, o, s, c, i) for o, s, c, i in
                               zip(ours_n, matched[f"{f}_status"], matched[f"{f}_cuk"], matched[f"{f}_inconsistent"])]
    return out


def outcome_counts(rows: pd.DataFrame) -> dict:
    return {f: {k: int(v) for k, v in rows[f"{f}_outcome"].value_counts().items()} for f in COMPARE}


def main() -> None:
    ap = argparse.ArgumentParser(description="Compare our FCA return figures with Co-ops UK open data.")
    ap.add_argument("--ours", type=Path, default=OURS)
    ap.add_argument("--catalogue", type=Path, default=CATALOGUE)
    ap.add_argument("--orgs", type=Path, default=ORGS)
    ap.add_argument("--economy", type=Path, default=ECONOMY)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    a = ap.parse_args()
    read = lambda p, cols=None: pd.read_csv(p, dtype=str, keep_default_na=False, usecols=cols)  # noqa: E731

    ours = read(a.ours)
    catalogue = read(a.catalogue, ["charity_number"])
    orgs = read(a.orgs, ["CUK Organisation ID", "Registered Number", "Registrar", "Registered Name"])
    econ, econ_stats = dedupe_economy(read(a.economy))
    econ = econ.rename(columns={f: f"{f}_cuk" for f in COMPARE})  # our columns keep their names

    matched, counts = join(ours, catalogue, orgs, econ)
    rows = compare(matched)
    summary = {"join": {**counts, **econ_stats}, "outcomes": outcome_counts(rows),
               **{f"by_{c}": {str(v): outcome_counts(g) for v, g in rows.groupby(c)}
                  for c in ("form_type", "layout", "confidence")}}
    dis = rows[(rows[[f"{f}_outcome" for f in COMPARE]] == "disagree").any(axis=1)]
    sample = dis.sample(n=min(SAMPLE_N, len(dis)), random_state=SAMPLE_SEED).sort_values("doc_id")

    a.out_dir.mkdir(parents=True, exist_ok=True)
    write_csv_atomic(rows, a.out_dir / "coops_uk_benchmark_rows.csv")
    write_csv_atomic(sample, a.out_dir / "coops_uk_disagreements_sample.csv")
    write_text_atomic(a.out_dir / "coops_uk_benchmark_summary.json", json.dumps(summary, indent=2))
    print(json.dumps(summary["join"], indent=2), json.dumps(summary["outcomes"], indent=2), sep="\n", flush=True)


if __name__ == "__main__":
    main()
