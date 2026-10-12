"""Checks for the regex extraction, context, name normalisation and tiers (no network, no data files)."""
import pandas as pd

from find_sc_company_numbers import extract_company_numbers, normalise_name, same_as_charity_number, score


def numbers(text: str) -> list[str]:
    return [d["number"] for d in extract_company_numbers(text)]


def test_keyword_company_context():
    (hit,) = extract_company_numbers("Company Registration Number: SC123456")
    assert hit["number"] == "SC123456"
    assert hit["number_context"] == "company"


def test_ocr_letter_o():
    assert numbers("Charity No: SCO00003") == ["SC000003"]


def test_all_letter_o_not_matched():
    assert numbers("SCOOOOOO") == []


def test_spacing():
    assert numbers("SC 012345") == ["SC012345"]


def test_preceded_by_letter():
    assert numbers("XSC123456") == []


def test_one_real_digit_needed():
    assert numbers("SCOOOOO1") == ["SC000001"]


def test_seven_digits_not_matched():
    assert numbers("SC1234567") == []


def test_markdown_noise():
    assert numbers("Company Number ~~:~~ **SC031517**") == ["SC031517"]


def test_nearest_keyword_wins():
    found = {d["number"]: d["number_context"] for d in
             extract_company_numbers("Company No. SC123456 Charity No. SC012345")}
    assert found == {"SC123456": "company", "SC012345": "charity"}


def test_charity_word_ignored_for_non_sc0():
    (hit,) = extract_company_numbers("Charity No SC123456")
    assert hit["number_context"] == "none"  # charity numbers always start SC0


def test_no_keyword_none():
    (hit,) = extract_company_numbers("Pencaitland Playgroup SC000003")
    assert hit["number_context"] == "none"


def test_repeat_mentions_collapse():
    found = extract_company_numbers("Company number SC049781. Registered as SC 049781 in Edinburgh.")
    assert len(found) == 1
    assert found[0]["n_mentions"] == 2
    assert found[0]["number_context"] == "company"


def test_name_normaliser():
    assert normalise_name("The Leith Foodbank Ltd") == normalise_name("LEITH FOODBANK LIMITED")


def test_own_charity_number():
    assert same_as_charity_number("SC000003", "SC000003") is True
    assert same_as_charity_number("SC123456", "SC000003") is False


def test_tiers():
    rows = [("GB-SC-SC000001", "Alpha Trust", "SC100001", "company"),
            ("GB-SC-SC000002", "Beta Trust", "SC010002", "charity"),
            ("GB-SC-SC000003", "Gamma Trust", "SC010003", "none"),   # SC0 with no keyword: not specific
            ("GB-SC-SC000004", "Delta Trust", "SC123456", "none")]   # not SC0: a company number by form
    cands = pd.DataFrame([{"uid": u, "charity_number": u[len("GB-SC-"):], "charity_name": name,
                           "charity_postcode": "EH1 1AA", "charity_removeddate": "", "doc_id": "",
                           "year_end_date": "2025-03-31", "company_number": n, "n_mentions": 1,
                           "number_context": ctx, "n_distinct_numbers_in_doc": 1, "snippet": ""}
                          for u, name, n, ctx in rows])
    ch = pd.DataFrame([{"ch_company_name": name.upper() + " LIMITED", "company_number": n, "ch_status": "active",
                        "ch_incorporation_date": "", "ch_dissolution_date": "", "ch_postcode": "EH1 1AA",
                        "ch_address": "", "ch_company_type": "private-limited-guarant-nsc"}
                       for _, name, n, _ in rows])
    links = pd.DataFrame(columns=["orgB_id_in_source", "orgA_uid"])
    scored = score(cands, ch, links, set(), {}, set())
    tier = dict(zip(scored["company_number"], scored["confidence"]))
    assert tier["SC100001"] == "high"
    assert tier["SC010002"] == "low"
    assert tier["SC010003"] != "high"
    assert tier["SC123456"] == "high"
