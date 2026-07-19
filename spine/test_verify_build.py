import csv

import pytest
from click.testing import CliRunner

from cli import cli
from spine.verify_build import RepresentationError, verify_representation


def _write_csv(path, header, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def _make_files(tmp_path, *, include_second_uid):
    infile = tmp_path / "source.spine.csv"
    _write_csv(
        infile,
        ["uid", "source"],
        [
            ["GB-CHC-1", "ccew"],
            ["GB-COH-2", "CH"],
            ["GB-CQC-ignored", "carequalitycommission"],
        ],
    )

    output_base = tmp_path / "TSCS_spine"
    spine_rows = [["GB-CHC-1"]]
    if include_second_uid:
        spine_rows.append(["GB-COH-2"])
    _write_csv(
        tmp_path / "TSCS_spine.spine.csv",
        ["uid"],
        spine_rows,
    )
    _write_csv(
        tmp_path / "TSCS_spine.matches.csv",
        ["orgA_uid", "orgB_uid"],
        [["", ""]],
    )
    return infile, output_base


def test_verify_representation_succeeds_when_every_input_uid_is_present(
    tmp_path,
):
    infile, output_base = _make_files(tmp_path, include_second_uid=True)

    missing = verify_representation([infile], output_base)

    assert missing == set()


def test_verify_representation_raises_with_the_missing_uids(tmp_path):
    infile, output_base = _make_files(tmp_path, include_second_uid=False)

    with pytest.raises(RepresentationError) as exc_info:
        verify_representation([infile], output_base)

    assert exc_info.value.missing_uids == {"GB-COH-2"}
    assert "1 input organisation UID(s)" in str(exc_info.value)


def test_check_spine_cli_exits_nonzero_when_an_input_uid_is_missing(tmp_path):
    infile, output_base = _make_files(tmp_path, include_second_uid=False)

    result = CliRunner().invoke(
        cli,
        ["check-spine", str(infile), "-o", str(output_base)],
    )

    assert result.exit_code != 0
    assert "GB-COH-2" in result.output


def test_check_spine_cli_rejects_an_empty_input_list():
    result = CliRunner().invoke(cli, ["check-spine"])

    assert result.exit_code != 0
    assert "at least one source spine input is required" in result.output
