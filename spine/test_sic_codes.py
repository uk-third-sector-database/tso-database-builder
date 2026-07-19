import pandas as pd
import pytest

from handler.all_companies_house import (
    api_scrape_iteration,
    extract_sic_codes,
    iteration_rank,
    main_process,
    sic_codes_lookup,
)
from spine.add_cso_type import add_cso_type_to_spine, prepare_primary_sic


def test_extract_sic_codes_keeps_token_order_and_legacy_codes():
    value = "82990 - current activity, 8899, None, 94120"
    assert extract_sic_codes(value) == ["82990", "8899", "94120"]


def test_api_refresh_uses_daily_iteration_precision():
    path = "ch_adv_scrape_api_refresh_2026-07-18.csv"

    assert api_scrape_iteration(path) == "18/07/2026"
    assert iteration_rank("18/07/2026") > iteration_rank("07/2026")
    assert iteration_rank("07/2026") > iteration_rank("2022")


def test_ch_preparation_does_not_write_unused_cic_sidecar(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    main_process(tmp_path / "ch.all.csv")

    assert not (tmp_path / "all_CICs.txt").exists()


def test_sic_lookup_uses_latest_snapshot_and_own_codes_first(tmp_path):
    ch_file = tmp_path / "ch.csv"
    matches_file = tmp_path / "matches.csv"
    output_file = tmp_path / "sic.csv"

    pd.DataFrame([
        {"uid": "GB-COH-A", "SIC": "11111", "iteration": "01/2025"},
        {"uid": "GB-COH-A", "SIC": "22222", "iteration": "07/2026"},
        {
            "uid": "GB-COH-A",
            "SIC": "3333, 44444 - latest activity, 44444",
            "iteration": "18/07/2026",
        },
        {"uid": "GB-COH-B", "SIC": "66666, None", "iteration": "07/2026"},
        {"uid": "GB-COH-P", "SIC": "55555", "iteration": "07/2026"},
        {"uid": "GB-COH-U", "SIC": "7777", "iteration": "07/2026"},
        {"uid": "GB-COH-N", "SIC": "None", "iteration": "07/2026"},
    ]).to_csv(ch_file, index=False)

    pd.DataFrame([
        {"uid": "GB-COH-P", "orgB_uid": "GB-COH-A"},
        {"uid": "GB-COH-P", "orgB_uid": "GB-COH-A"},
        {"uid": "GB-COH-P", "orgB_uid": "GB-COH-B"},
        {"uid": "", "orgB_uid": "GB-COH-U"},
    ]).to_csv(matches_file, index=False)

    sic_codes_lookup(ch_file, matches_file, output_file)

    assert pd.read_csv(output_file, dtype=str).to_dict("records") == [
        {"uid": "GB-COH-P", "SIC": "55555"},
        {"uid": "GB-COH-P", "SIC": "3333"},
        {"uid": "GB-COH-P", "SIC": "44444"},
        {"uid": "GB-COH-P", "SIC": "66666"},
        {"uid": "GB-COH-U", "SIC": "7777"},
    ]


def test_sic_lookup_rejects_ambiguous_absorbing_parent(tmp_path):
    ch_file = tmp_path / "ch.csv"
    matches_file = tmp_path / "matches.csv"
    output_file = tmp_path / "sic.csv"

    pd.DataFrame([
        {"uid": "GB-COH-A", "SIC": "82990", "iteration": "07/2026"},
    ]).to_csv(ch_file, index=False)
    pd.DataFrame([
        {"uid": "GB-CHC-1", "orgB_uid": "GB-COH-A"},
        {"uid": "GB-CHC-2", "orgB_uid": "GB-COH-A"},
    ]).to_csv(matches_file, index=False)

    with pytest.raises(RuntimeError, match="GB-COH-A"):
        sic_codes_lookup(ch_file, matches_file, output_file)


def test_primary_sic_skips_legacy_four_digit_code():
    sic_raw = pd.DataFrame([
        {"uid": "GB-COH-1", "SIC": "9491"},
        {"uid": "GB-COH-1", "SIC": "94910"},
        {"uid": "GB-COH-2", "SIC": "01110"},
    ])

    result = prepare_primary_sic(sic_raw)

    assert result.to_dict("records") == [
        {"uid": "GB-COH-1", "primary_sic": 94910, "sic_div": 94},
        {"uid": "GB-COH-2", "primary_sic": 1110, "sic_div": 1},
    ]


def test_cso_subtype_uses_first_five_digit_code(tmp_path):
    spine_file = tmp_path / "spine.csv"
    sic_file = tmp_path / "sic.csv"
    output_file = tmp_path / "classified.csv"

    pd.DataFrame([
        {
            "uid": "GB-COH-1",
            "organisationname": "Generic Limited",
            "source_register": "Companies House",
            "is_cic": False,
        }
    ]).to_csv(spine_file, index=False)
    pd.DataFrame([
        {"uid": "GB-COH-1", "SIC": "9491"},
        {"uid": "GB-COH-1", "SIC": "94910"},
    ]).to_csv(sic_file, index=False)

    add_cso_type_to_spine(spine_file, sic_file, output_file)

    result = pd.read_csv(output_file)
    assert result.loc[0, "cso_subtype"] == "Religious Organisation"


def test_cso_subtype_preserves_first_matching_rule(tmp_path):
    spine_file = tmp_path / "spine.csv"
    sic_file = tmp_path / "sic.csv"
    output_file = tmp_path / "classified.csv"

    pd.DataFrame([
        {
            "uid": "GB-COH-1",
            "organisationname": "Alpha School",
            "source_register": "Companies House",
            "is_cic": False,
        }
    ]).to_csv(spine_file, index=False)
    pd.DataFrame([
        {"uid": "GB-COH-1", "SIC": "94910"},
    ]).to_csv(sic_file, index=False)

    add_cso_type_to_spine(spine_file, sic_file, output_file)

    result = pd.read_csv(output_file)
    assert result.loc[0, "cso_subtype"] == "Education Institution"


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Alpha School", "Education Institution"),
        ("Alpha Football Club", "Sports Club"),
        ("Alpha Church", "Religious Organisation"),
        ("City of Alpha Choir", "Arts Organisation"),
        ("Alpha Guarantee Company", "Other Company Limited By Guarantee"),
    ],
)
def test_cso_subtype_name_rules_work_without_five_digit_sic(
    tmp_path, name, expected
):
    spine_file = tmp_path / "spine.csv"
    sic_file = tmp_path / "sic.csv"
    output_file = tmp_path / "classified.csv"

    pd.DataFrame([
        {
            "uid": "GB-COH-1",
            "organisationname": name,
            "source_register": "Companies House",
            "is_cic": False,
        }
    ]).to_csv(spine_file, index=False)
    # Four-digit legacy SIC values remain published provenance but are
    # deliberately excluded from the SIC-2007 subtype rules.
    pd.DataFrame([
        {"uid": "GB-COH-1", "SIC": "9491"},
    ]).to_csv(sic_file, index=False)

    add_cso_type_to_spine(spine_file, sic_file, output_file)

    result = pd.read_csv(output_file)
    assert result.loc[0, "cso_subtype"] == expected
