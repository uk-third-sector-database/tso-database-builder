import csv
import io

import pytest

from spine.source_alignment import (
    SourceAlignmentInputError,
    active_ccew_uids,
    active_companies_house_uids,
    check_source_alignment,
    load_absorption_parents,
    main,
    parse_iteration,
)


def write_csv(path, fields, rows, encoding="utf-8"):
    with path.open("w", newline="", encoding=encoding) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def make_sources(tmp_path):
    spine = tmp_path / "TSCS_spine.spine.csv"
    write_csv(
        spine,
        ("uid", "removeddate"),
        (
            {"uid": "GB-CHC-1", "removeddate": "01/01/2020"},
            {"uid": "GB-CHC-2", "removeddate": "01/01/2020"},
            {"uid": "GB-SC-SC1", "removeddate": ""},
            {"uid": "GB-NIC-1", "removeddate": "02/02/2020"},
            {"uid": "GB-NIC-2", "removeddate": "02/02/2020"},
            {"uid": "GB-COH-1", "removeddate": "03/03/2020"},
            {"uid": "GB-COH-2", "removeddate": "03/03/2020"},
        ),
    )

    matches = tmp_path / "TSCS_spine.matches.csv"
    write_csv(
        matches,
        ("uid", "orgA_uid", "orgB_uid"),
        (
            # A real consolidation: the active source child resolves to the
            # removed effective parent and must be flagged.
            {
                "uid": "GB-CHC-2",
                "orgA_uid": "GB-CHC-2",
                "orgB_uid": "GB-CHC-3",
            },
            # Association-only: the blank uid must not absorb GB-CHC-999.
            {
                "uid": "",
                "orgA_uid": "GB-CHC-2",
                "orgB_uid": "GB-CHC-999",
            },
        ),
    )

    ccew = tmp_path / "ccew.csv"
    ccew_fields = (
        "registered_charity_number",
        "linked_charity_number",
        "charity_registration_status",
        "date_of_removal",
    )
    write_csv(
        ccew,
        ccew_fields,
        (
            # Active primary: violation.
            {
                "registered_charity_number": "1",
                "linked_charity_number": "0",
                "charity_registration_status": "Registered",
                "date_of_removal": "",
            },
            # Removed primary: not part of the active comparison.
            {
                "registered_charity_number": "2",
                "linked_charity_number": "0",
                "charity_registration_status": "Removed",
                "date_of_removal": "2020-01-01",
            },
            # Active linked branch: not the authoritative primary -0 row.
            {
                "registered_charity_number": "2",
                "linked_charity_number": "1",
                "charity_registration_status": "Registered",
                "date_of_removal": "",
            },
            # Active and genuinely absorbed through a nonblank matches.uid.
            {
                "registered_charity_number": "3",
                "linked_charity_number": "0",
                "charity_registration_status": "Registered",
                "date_of_removal": "",
            },
            # Active and association-linked only: it remains unresolved.
            {
                "registered_charity_number": "999",
                "linked_charity_number": "0",
                "charity_registration_status": "Registered",
                "date_of_removal": "",
            },
        ),
    )

    oscr = tmp_path / "oscr.csv"
    write_csv(
        oscr,
        ("Charity Number", "Charity Status"),
        ({"Charity Number": "SC1", "Charity Status": "Active"},),
    )

    ccni = tmp_path / "ccni.csv"
    write_csv(
        ccni,
        ("Reg charity number", "Status"),
        (
            {"Reg charity number": "1", "Status": "Received: on time"},
            {"Reg charity number": "2", "Status": "Removed"},
        ),
        encoding="latin-1",
    )

    companies_house = tmp_path / "CH.all.csv"
    write_csv(
        companies_house,
        ("uid", "iteration", "removeddate"),
        (
            # A date-specific active refresh outranks a monthly removed row.
            {
                "uid": "GB-COH-1",
                "iteration": "07/2026",
                "removeddate": "01/07/2026",
            },
            {
                "uid": "GB-COH-1",
                "iteration": "18/07/2026",
                "removeddate": "",
            },
            # Equal-date removal wins, so this is not active.
            {
                "uid": "GB-COH-2",
                "iteration": "07/2026",
                "removeddate": "",
            },
            {
                "uid": "GB-COH-2",
                "iteration": "07/2026",
                "removeddate": "03/07/2026",
            },
        ),
    )
    return spine, matches, ccew, oscr, ccni, companies_house


def test_population_gate_resolves_absorbed_but_not_association_only(tmp_path):
    paths = make_sources(tmp_path)

    report = check_source_alignment(
        spine=paths[0],
        matches=paths[1],
        ccew=paths[2],
        oscr=paths[3],
        ccni=paths[4],
        companies_house=paths[5],
    )

    assert not report.passed
    assert report.false_removed_source_count == 4
    assert report.false_removed_count == 4
    assert report.unresolved_count == 1
    by_source = {result.source: result for result in report.results}
    assert by_source["CCEW"].false_removed_links == (
        ("GB-CHC-1", "GB-CHC-1"),
        ("GB-CHC-3", "GB-CHC-2"),
    )
    assert by_source["CCEW"].false_removed_uids == (
        "GB-CHC-1",
        "GB-CHC-2",
    )
    assert by_source["CCEW"].unresolved_source_uids == ("GB-CHC-999",)
    assert by_source["OSCR"].false_removed_uids == ()
    assert by_source["CCNI"].false_removed_uids == ("GB-NIC-1",)
    assert by_source["Companies House"].false_removed_uids == (
        "GB-COH-1",
    )
    assert by_source["CCEW"].active_source_uids == 3
    assert by_source["CCEW"].active_direct_spine_uids == 1
    assert by_source["CCEW"].active_effective_source_uids == 2
    assert by_source["CCEW"].active_effective_parent_uids == 2


def test_absorption_loader_skips_blank_uid_and_rejects_conflicts(tmp_path):
    final = {
        "GB-CHC-1": "",
        "GB-CHC-2": "",
    }
    association = tmp_path / "association.csv"
    write_csv(
        association,
        ("uid", "orgA_uid", "orgB_uid"),
        (
            {
                "uid": "",
                "orgA_uid": "GB-CHC-1",
                "orgB_uid": "GB-CQC-1",
            },
        ),
    )
    assert load_absorption_parents(association, final) == {}

    conflicting = tmp_path / "conflicting.csv"
    write_csv(
        conflicting,
        ("uid", "orgA_uid", "orgB_uid"),
        (
            {
                "uid": "GB-CHC-1",
                "orgA_uid": "GB-CHC-1",
                "orgB_uid": "GB-CHC-999",
            },
            {
                "uid": "GB-CHC-2",
                "orgA_uid": "GB-CHC-2",
                "orgB_uid": "GB-CHC-999",
            },
        ),
    )
    with pytest.raises(SourceAlignmentInputError, match="conflicting parents"):
        load_absorption_parents(conflicting, final)


def test_ch_iteration_parsing_and_conservative_ties(tmp_path):
    assert str(parse_iteration("2022")) == "2022-01-01"
    assert str(parse_iteration("07/2026")) == "2026-07-01"
    assert str(parse_iteration("18/07/2026")) == "2026-07-18"

    path = tmp_path / "CH.all.csv"
    write_csv(
        path,
        ("uid", "iteration", "removeddate"),
        (
            {"uid": "GB-COH-1", "iteration": "2022", "removeddate": ""},
            {
                "uid": "GB-COH-1",
                "iteration": "07/2026",
                "removeddate": "01/07/2026",
            },
            {
                "uid": "GB-COH-1",
                "iteration": "18/07/2026",
                "removeddate": "",
            },
            {"uid": "GB-COH-2", "iteration": "07/2026", "removeddate": ""},
            {
                "uid": "GB-COH-2",
                "iteration": "07/2026",
                "removeddate": "02/07/2026",
            },
        ),
    )

    assert active_companies_house_uids(path) == {"GB-COH-1"}


def test_ch_historical_bootstrap_blank_status_is_not_current_active(tmp_path):
    path = tmp_path / "CH.all.csv"
    write_csv(
        path,
        ("uid", "iteration", "removeddate"),
        (
            {
                "uid": "GB-COH-CE000001",
                "iteration": "2022",
                "removeddate": "",
            },
            {
                "uid": "GB-COH-1",
                "iteration": "07/2026",
                "removeddate": "",
            },
        ),
    )

    assert active_companies_house_uids(path) == {"GB-COH-1"}


def test_ch_ce_cio_status_is_deferred_to_ccew(tmp_path):
    path = tmp_path / "CH.all.csv"
    write_csv(
        path,
        ("uid", "iteration", "removeddate"),
        (
            {
                "uid": "GB-COH-CE000001",
                "iteration": "07/2026",
                "removeddate": "",
            },
            {
                "uid": "GB-COH-1",
                "iteration": "07/2026",
                "removeddate": "",
            },
        ),
    )

    assert active_companies_house_uids(path) == {"GB-COH-1"}


def test_ch_gate_requires_a_monthly_bulk_snapshot(tmp_path):
    path = tmp_path / "CH.all.csv"
    write_csv(
        path,
        ("uid", "iteration", "removeddate"),
        (
            {
                "uid": "GB-COH-1",
                "iteration": "18/07/2026",
                "removeddate": "",
            },
        ),
    )

    with pytest.raises(SourceAlignmentInputError, match="no MM/YYYY"):
        active_companies_house_uids(path)


def test_ccew_rejects_contradictory_current_status(tmp_path):
    path = tmp_path / "ccew.csv"
    write_csv(
        path,
        (
            "registered_charity_number",
            "linked_charity_number",
            "charity_registration_status",
            "date_of_removal",
        ),
        (
            {
                "registered_charity_number": "1",
                "linked_charity_number": "0",
                "charity_registration_status": "Registered",
                "date_of_removal": "2020-01-01",
            },
        ),
    )

    with pytest.raises(
        SourceAlignmentInputError, match="contradictory status/removal"
    ):
        active_ccew_uids(path)


def test_cli_returns_one_for_alignment_failure(tmp_path):
    paths = make_sources(tmp_path)
    stdout = io.StringIO()
    stderr = io.StringIO()
    result = main(
        [
            "--spine",
            str(paths[0]),
            "--matches",
            str(paths[1]),
            "--ccew",
            str(paths[2]),
            "--oscr",
            str(paths[3]),
            "--ccni",
            str(paths[4]),
            "--companies-house",
            str(paths[5]),
        ],
        stdout=stdout,
        stderr=stderr,
    )

    assert result == 1
    assert "Source-alignment gate: FAIL" in stdout.getvalue()
    assert "Total unresolved active source UIDs: 1" in stdout.getvalue()
    assert "Total false-removed active source UIDs: 4" in stdout.getvalue()
    assert "Unique false-removed effective parents: 4" in stdout.getvalue()
    assert stderr.getvalue() == ""


def test_bad_ch_iteration_is_an_input_error(tmp_path):
    path = tmp_path / "CH.all.csv"
    write_csv(
        path,
        ("uid", "iteration", "removeddate"),
        (
            {
                "uid": "GB-COH-1",
                "iteration": "July 2026",
                "removeddate": "",
            },
        ),
    )

    with pytest.raises(SourceAlignmentInputError, match="expected YYYY"):
        active_companies_house_uids(path)
