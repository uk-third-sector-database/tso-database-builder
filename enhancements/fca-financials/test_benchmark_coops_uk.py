"""Checks for the Co-ops UK benchmark (no network, no data files; all frames made up)."""
import math

import pandas as pd

from benchmark_coops_uk import COMPARE, ambiguous_keys, dedupe_economy, join, outcome, society_key

NAN = math.nan


def econ_frame(rows: list[tuple]) -> pd.DataFrame:
    """rows: (CUK id, year end, Turnover, Memberships, Employees) as Co-ops UK strings."""
    return pd.DataFrame(rows, columns=["CUK Organisation ID", "Year End Date", "Turnover", "Memberships", "Employees"])


def test_society_key():
    assert society_key(" 0441ip ") == "441IP"
    assert society_key("1001W") == "1001W" and society_key("4329") == "4329"
    assert society_key("7625R") != society_key("7625")  # different societies on the register


def test_ambiguous_keys():
    assert ambiguous_keys(pd.Series(["12", "12", "13"]), pd.Series(["R1", "R2", "R3"])) == {"12"}
    assert ambiguous_keys(pd.Series(["12", "12"]), pd.Series(["R1", "R1"])) == set()


def test_dedupe_inconsistent_blank_and_zero():
    e, stats = dedupe_economy(econ_frame([
        ("R1", "2023-12-31 00:00:00", "100", "5", ""),
        ("R1", "2023-12-31 00:00:00", "200", "5.0", "0"),  # turnover disagrees; members 5 == 5.0
        ("R1", "", "1", "1", "1"),  # no year end: dropped
    ]))
    assert stats["economy_rows_no_year_end"] == 1 and len(e) == 1
    r = e.iloc[0]
    assert r["year_end"] == "2023-12-31"
    assert bool(r["turnover_inconsistent"]) and not r["number_of_members_inconsistent"]
    assert r["number_of_employees"] == 0 and not r["number_of_employees_inconsistent"]  # blank + "0" -> 0


def test_turnover_outcomes():
    t = lambda ours, cuk, status="parsed", inc=False: outcome("turnover", ours, status, cuk, inc)  # noqa: E731
    assert t(123456, 123456.0) == "agree_exact"
    assert t(123456, 123000) == "agree_rounded"
    assert t(100500, 100000) == "agree_1pct"  # rounds to 101,000, so not agree_rounded
    assert t(150000, 100000) == "disagree"
    assert t(NAN, 100000, "review") == "ours_missing"
    assert t(-9, 100000, "not_applicable") == "ours_missing"
    assert t(100000, NAN) == "cuk_missing"
    assert t(100000, 1, inc=True) == "cuk_inconsistent"
    assert t(NAN, 100000, "not_on_form") == "not_on_form"
    assert outcome("number_of_members", 123456, "parsed", 123000, False) == "disagree"  # no rounding rule


def test_blank_versus_zero():
    assert outcome("number_of_employees", 0, "nil", 0.0, False) == "agree_exact"
    assert outcome("number_of_employees", 0, "nil", NAN, False) == "cuk_missing"


def test_join_excludes_ambiguous_and_counts_near_misses():
    ours = pd.DataFrame({"society_number": ["1001W", "4026", "8000R"], "doc_id": ["d1", "d2", "d3"],
                         "catalogue_year_end": ["2023-12-31", "2023-12-31", "2023-03-31"]})
    catalogue = pd.DataFrame({"charity_number": ["1001W", "4026", "04026", "8000R"]})  # 4026 ambiguous in ours
    orgs = pd.DataFrame({"CUK Organisation ID": ["R1", "R2", "R3"], "Registered Number": ["1001W", "4026", "8000R"],
                         "Registrar": ["FCA", "FCA", "FCA"], "Registered Name": ["A", "B", "C"]})
    econ, _ = dedupe_economy(econ_frame([("R1", "2023-12-31 00:00:00", "1", "2", "3"),
                                         ("R2", "2023-12-31 00:00:00", "1", "2", "3"),
                                         ("R3", "2023-04-01 00:00:00", "1", "2", "3")]))
    econ = econ.rename(columns={f: f"{f}_cuk" for f in COMPARE})
    matched, c = join(ours, catalogue, orgs, econ)
    assert matched["doc_id"].tolist() == ["d1"] and matched["registered_name"].tolist() == ["A"]
    assert c["ambiguous_keys_in_our_catalogue"] == 1 and c["our_rows_excluded_ambiguous"] == 1
    assert c["rows_society_in_cuk_no_year_end_match"] == 1 and c["of_which_cuk_year_end_within_31_days"] == 1
