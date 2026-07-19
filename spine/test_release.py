import csv
import hashlib
import zipfile
from pathlib import Path

import pytest

from spine.release import (
    CSV_HEADERS,
    GUIDANCE_HTML_FILENAME,
    GUIDANCE_PDF_FILENAME,
    LICENCE_FILENAME,
    MATCHES_FILENAME,
    PAYLOAD_FILENAMES,
    SIC_FILENAME,
    SPINE_FILENAME,
    SUPPLEMENTARY_FILENAME,
    TRANSPORT_ZIP_FILENAME,
    ReleasePackagingError,
    ReleaseValidationError,
    prepare_release,
    validate_release,
)


def write_csv(path, header, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def make_valid_release(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    write_csv(
        data_dir / SPINE_FILENAME,
        CSV_HEADERS[SPINE_FILENAME],
        [
            [
                "GB-CHC-1",
                "ALPHA TRUST",
                "ALPHA TRUST",
                "1 HIGH STREET",
                "LONDON",
                "E1 1AA",
                "01/02/2003",
                "",
                "Charity Commission for England and Wales",
                "False",
                "Charity",
                "Charity",
            ],
            [
                "GB-COH-00000002",
                "BETA CIC",
                "BETA CIC",
                "2 HIGH STREET",
                "LEEDS",
                "LS1 1AA",
                "29/02/2024",
                "05/06/2025",
                "Companies House",
                "True",
                "CIC",
                "CIC",
            ],
        ],
    )
    write_csv(
        data_dir / MATCHES_FILENAME,
        CSV_HEADERS[MATCHES_FILENAME],
        [
            [
                "GB-CHC-1",
                "1-0",
                "ccew",
                "GB-CHC-1",
                "SC000003",
                "OSCR",
                "GB-SC-SC000003",
                "name - crossborder",
            ],
            [
                "",
                "00000002",
                "CH",
                "GB-COH-00000002",
                "CQC-9",
                "carequalitycommission",
                "GB-CQC-CQC-9",
                "companyid - cqc",
            ],
        ],
    )
    write_csv(
        data_dir / SUPPLEMENTARY_FILENAME,
        CSV_HEADERS[SUPPLEMENTARY_FILENAME],
        [
            [
                "GB-SC-SC000003",
                "ALPHA TRUST SCOTLAND",
                "ALPHA TRUST SCOTLAND",
                "3 HIGH STREET",
                "EDINBURGH",
                "EH1 1AA",
                "03/04/2005",
                "",
                "Office of the Scottish Charity Regulator",
                "SC000003",
            ]
        ],
    )
    write_csv(
        data_dir / SIC_FILENAME,
        CSV_HEADERS[SIC_FILENAME],
        [
            ["GB-CHC-1", "88990"],
            ["GB-CQC-CQC-9", "1234"],
        ],
    )
    return data_dir


def make_guidance_files(tmp_path):
    guidance_dir = tmp_path / "guidance"
    guidance_dir.mkdir()
    html = guidance_dir / GUIDANCE_HTML_FILENAME
    html.write_text(
        "<!doctype html><title>TSCS guidance</title>"
        "<p>Spine 2; matches 2; supplementary 1; SIC 2; "
        "active 1; removed 1.</p>\n",
        "utf-8",
    )
    pdf = guidance_dir / GUIDANCE_PDF_FILENAME
    pdf.write_bytes(b"%PDF-1.4\n%%EOF\n")
    licence = guidance_dir / LICENCE_FILENAME
    licence.write_text("Open licence terms.\n", "utf-8")
    return html, pdf, licence


def read_csv_rows(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.reader(handle))


def test_validate_release_reports_logical_counts_hashes_and_uid_universe(
    tmp_path,
):
    data_dir = make_valid_release(tmp_path)

    result = validate_release(data_dir)

    assert result.files[SPINE_FILENAME].rows == 2
    assert result.files[MATCHES_FILENAME].rows == 2
    assert result.files[SUPPLEMENTARY_FILENAME].rows == 1
    assert result.files[SIC_FILENAME].rows == 2
    assert result.metrics["spine_uids"] == 2
    assert result.metrics["release_uids"] == 4
    assert result.metrics["active_spine_rows"] == 1
    assert result.metrics["removed_spine_rows"] == 1
    assert result.metrics["four_digit_sic_rows"] == 1
    assert result.metrics["five_digit_sic_rows"] == 1
    expected_hash = hashlib.sha256(
        (data_dir / SPINE_FILENAME).read_bytes()
    ).hexdigest()
    assert result.files[SPINE_FILENAME].sha256 == expected_hash
    assert any("blank optional uid" in warning for warning in result.warnings)


def test_validate_release_handles_embedded_newlines_as_one_logical_row(
    tmp_path,
):
    data_dir = make_valid_release(tmp_path)
    rows = read_csv_rows(data_dir / SUPPLEMENTARY_FILENAME)
    rows[1][3] = "LINE ONE\nLINE TWO"
    write_csv(
        data_dir / SUPPLEMENTARY_FILENAME,
        CSV_HEADERS[SUPPLEMENTARY_FILENAME],
        rows[1:],
    )

    result = validate_release(data_dir)

    assert result.files[SUPPLEMENTARY_FILENAME].rows == 1


def test_validate_release_warns_when_removal_predates_registration(tmp_path):
    data_dir = make_valid_release(tmp_path)
    rows = read_csv_rows(data_dir / SPINE_FILENAME)
    rows[1][7] = "31/12/2002"
    write_csv(
        data_dir / SPINE_FILENAME,
        CSV_HEADERS[SPINE_FILENAME],
        rows[1:],
    )

    result = validate_release(data_dir)

    assert result.metrics["removed_before_registered_rows"] == 1
    assert any(
        "removeddate earlier than registerdate" in warning
        for warning in result.warnings
    )


def test_validate_release_rejects_structure_dates_and_references(tmp_path):
    data_dir = make_valid_release(tmp_path)

    spine_rows = read_csv_rows(data_dir / SPINE_FILENAME)
    spine_rows[1][6] = "31/02/2024"
    write_csv(
        data_dir / SPINE_FILENAME,
        CSV_HEADERS[SPINE_FILENAME],
        spine_rows[1:],
    )

    match_rows = read_csv_rows(data_dir / MATCHES_FILENAME)
    match_rows.append(
        [
            "GB-CHC-1",
            "SC000003",
            "OSCR",
            "GB-SC-SC000003",
            "1-0",
            "ccew",
            "GB-CHC-1",
            "name - crossborder",
        ]
    )
    write_csv(
        data_dir / MATCHES_FILENAME,
        CSV_HEADERS[MATCHES_FILENAME],
        match_rows[1:],
    )

    supplementary_rows = read_csv_rows(
        data_dir / SUPPLEMENTARY_FILENAME
    )
    supplementary_rows.append(
        [
            "GB-CHC-999",
            "OUTSIDE",
            "OUTSIDE",
            "",
            "",
            "",
            "",
            "",
            "Test",
            "",
        ]
    )
    write_csv(
        data_dir / SUPPLEMENTARY_FILENAME,
        CSV_HEADERS[SUPPLEMENTARY_FILENAME],
        supplementary_rows[1:],
    )

    sic_rows = read_csv_rows(data_dir / SIC_FILENAME)
    sic_rows.append(["GB-CHC-1", "12345, 67890"])
    write_csv(
        data_dir / SIC_FILENAME,
        CSV_HEADERS[SIC_FILENAME],
        sic_rows[1:],
    )

    with pytest.raises(ReleaseValidationError) as exc_info:
        validate_release(data_dir)

    message = str(exc_info.value)
    assert "impossible registerdate" in message
    assert "not a spine uid" in message
    assert "repeats the unordered endpoint pair and match_type" in message
    assert "outside the release uid universe" in message
    assert "one nonblank 4- or 5-digit code" in message


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("cso_type", "", "blank cso_type"),
        ("cso_type", "Company", "expected one of"),
        ("cso_subtype", "", "blank cso_subtype"),
        ("cso_subtype", "Registered charity", "expected one of"),
        ("cso_subtype", "CIC", "must pass through"),
        ("is_cic", "yes", "expected 'True' or 'False'"),
        ("source_register", "Unknown register", "expected one of"),
    ],
)
def test_validate_release_enforces_cso_classification(
    tmp_path, field, value, message
):
    data_dir = make_valid_release(tmp_path)
    rows = read_csv_rows(data_dir / SPINE_FILENAME)
    rows[1][CSV_HEADERS[SPINE_FILENAME].index(field)] = value
    write_csv(
        data_dir / SPINE_FILENAME,
        CSV_HEADERS[SPINE_FILENAME],
        rows[1:],
    )

    with pytest.raises(ReleaseValidationError, match=message):
        validate_release(data_dir)


def test_validate_release_rejects_unknown_match_type(tmp_path):
    data_dir = make_valid_release(tmp_path)
    rows = read_csv_rows(data_dir / MATCHES_FILENAME)
    rows[1][-1] = "manual guess"
    write_csv(
        data_dir / MATCHES_FILENAME,
        CSV_HEADERS[MATCHES_FILENAME],
        rows[1:],
    )

    with pytest.raises(ReleaseValidationError, match="match_type"):
        validate_release(data_dir)


@pytest.mark.parametrize(
    ("filename", "bad_header"),
    [
        (SPINE_FILENAME, ("uid",)),
        (MATCHES_FILENAME, tuple(reversed(CSV_HEADERS[MATCHES_FILENAME]))),
        (SUPPLEMENTARY_FILENAME, CSV_HEADERS[SUPPLEMENTARY_FILENAME][:-1]),
        (SIC_FILENAME, ("SIC", "uid")),
    ],
)
def test_validate_release_rejects_noncanonical_headers(
    tmp_path, filename, bad_header
):
    data_dir = make_valid_release(tmp_path)
    write_csv(data_dir / filename, bad_header, [])

    with pytest.raises(ReleaseValidationError, match="header is"):
        validate_release(data_dir)


def test_validate_release_rejects_width_duplicate_uid_and_duplicate_sic(
    tmp_path,
):
    data_dir = make_valid_release(tmp_path)

    with (data_dir / SPINE_FILENAME).open(
        "a", encoding="utf-8", newline=""
    ) as handle:
        csv.writer(handle).writerow(["GB-CHC-1"])
    with (data_dir / SIC_FILENAME).open(
        "a", encoding="utf-8", newline=""
    ) as handle:
        csv.writer(handle).writerow(["GB-CHC-1", "88990"])

    with pytest.raises(ReleaseValidationError) as exc_info:
        validate_release(data_dir)

    message = str(exc_info.value)
    assert "has 1 field(s); expected 12" in message
    assert "duplicates uid/SIC pair" in message

    # A complete duplicate spine row exercises the uid uniqueness check.
    spine_rows = read_csv_rows(data_dir / SPINE_FILENAME)
    write_csv(
        data_dir / SPINE_FILENAME,
        CSV_HEADERS[SPINE_FILENAME],
        [spine_rows[1], spine_rows[1]],
    )
    with pytest.raises(ReleaseValidationError, match="duplicates spine uid"):
        validate_release(data_dir)


def test_validate_release_rejects_exact_duplicate_supplementary_row(tmp_path):
    data_dir = make_valid_release(tmp_path)
    rows = read_csv_rows(data_dir / SUPPLEMENTARY_FILENAME)
    write_csv(
        data_dir / SUPPLEMENTARY_FILENAME,
        CSV_HEADERS[SUPPLEMENTARY_FILENAME],
        [rows[1], rows[1]],
    )

    with pytest.raises(ReleaseValidationError, match="exact duplicate"):
        validate_release(data_dir)


def test_prepare_release_is_deterministic_and_uses_exact_member_whitelist(
    tmp_path,
):
    data_dir = make_valid_release(tmp_path)
    html, pdf, licence = make_guidance_files(tmp_path)
    # This must never leak into either payload directory or transport ZIP.
    (data_dir / "TSCS_spine.matches.preecho.csv").write_text(
        "not,published\n", "utf-8"
    )

    first = prepare_release(
        data_dir, html, pdf, licence, tmp_path / "release-one"
    )
    second = prepare_release(
        data_dir, html, pdf, licence, tmp_path / "release-two"
    )

    expected_directory_members = set(PAYLOAD_FILENAMES) | {
        TRANSPORT_ZIP_FILENAME
    }
    assert {path.name for path in first.output_dir.iterdir()} == (
        expected_directory_members
    )
    with zipfile.ZipFile(first.transport_zip) as archive:
        assert archive.namelist() == list(PAYLOAD_FILENAMES)
    assert first.transport_zip.read_bytes() == second.transport_zip.read_bytes()


def test_prepare_release_rejects_stale_guidance_counts(tmp_path):
    data_dir = make_valid_release(tmp_path)
    html, pdf, licence = make_guidance_files(tmp_path)
    html.write_text("<!doctype html><p>Old release: 999,999</p>\n", "utf-8")

    with pytest.raises(ReleasePackagingError, match="guidance HTML is stale"):
        prepare_release(
            data_dir, html, pdf, licence, tmp_path / "stale-release"
        )


def test_prepare_release_refuses_overwrite_and_can_omit_zip(tmp_path):
    data_dir = make_valid_release(tmp_path)
    html, pdf, licence = make_guidance_files(tmp_path)
    output_dir = tmp_path / "release"

    result = prepare_release(
        data_dir,
        html,
        pdf,
        licence,
        output_dir,
        create_zip=False,
    )
    assert result.transport_zip is None
    assert {path.name for path in output_dir.iterdir()} == set(
        PAYLOAD_FILENAMES
    )

    with pytest.raises(ReleasePackagingError, match="refusing to overwrite"):
        prepare_release(data_dir, html, pdf, licence, output_dir)
