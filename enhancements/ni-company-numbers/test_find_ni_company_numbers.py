"""Checks for the regex extraction and name normalisation (no network, no data files)."""
from find_ni_company_numbers import extract_company_numbers, normalise_name, same_as_charity_number


def numbers(text: str) -> list[str]:
    return [d["number"] for d in extract_company_numbers(text)]


def test_keyword_registration_number():
    (hit,) = extract_company_numbers("Company Registration Number: NI049781")
    assert hit["number"] == "NI049781"
    assert hit["keyword_context"] is True


def test_five_digit_padded():
    assert numbers("a Company Limited by Guarantee (NI 49781)") == ["NI049781"]


def test_charity_numbers_not_matched():
    assert numbers("NIC101307") == []
    assert numbers("NIC 101307") == []


def test_markdown_strike_noise():
    assert numbers("Company Number ~~:~~ NI031517") == ["NI031517"]


def test_ocr_lowercase_l():
    assert numbers("Nl612345") == ["NI612345"]


def test_old_r0_form():
    assert numbers("R0000304") == ["R0000304"]


def test_preceded_by_letter():
    assert numbers("XN 48265") == []


def test_years_not_matched():
    assert numbers("year ended 31 March 2025") == []
    assert numbers("NI 2025") == []


def test_repeat_mentions_collapse():
    found = extract_company_numbers("Company number NI049781. Registered as NI 49781 in Belfast.")
    assert len(found) == 1
    assert found[0]["n_mentions"] == 2


def test_name_normaliser():
    assert normalise_name("The Antrim Foodbank Ltd") == normalise_name("ANTRIM FOODBANK LIMITED")


def test_own_charity_number():
    assert same_as_charity_number("NI110229", "110229") is True
    assert same_as_charity_number("NI049781", "101307") is False
