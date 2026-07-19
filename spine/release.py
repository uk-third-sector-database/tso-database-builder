"""Validation and safe packaging for a published TSCS Spine release.

The build directory contains many useful intermediate files.  This module
deliberately names every published file so that neither validation nor
packaging can accidentally depend on a wildcard.
"""

from __future__ import annotations

import csv
import hashlib
import re
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterator, List, Mapping, Sequence, Tuple


SPINE_FILENAME = "TSCS_spine.spine.csv"
MATCHES_FILENAME = "TSCS_spine.matches.csv"
SUPPLEMENTARY_FILENAME = "TSCS_spine.supplementary.csv"
SIC_FILENAME = "TSCS_spine.SIC_codes.csv"

GUIDANCE_HTML_FILENAME = "tcss-organisation-register-guidance.html"
GUIDANCE_PDF_FILENAME = "tcss-organisation-register-guidance.pdf"
LICENCE_FILENAME = "LICENCE.txt"
TRANSPORT_ZIP_FILENAME = "TSCS_spine.release.zip"

CSV_HEADERS: Mapping[str, Tuple[str, ...]] = {
    SPINE_FILENAME: (
        "uid",
        "organisationname",
        "normalisedname",
        "fulladdress",
        "city",
        "postcode",
        "registerdate",
        "removeddate",
        "source_register",
        "is_cic",
        "cso_type",
        "cso_subtype",
    ),
    MATCHES_FILENAME: (
        "uid",
        "orgA_id_in_source",
        "orgA_source",
        "orgA_uid",
        "orgB_id_in_source",
        "orgB_source",
        "orgB_uid",
        "match_type",
    ),
    SUPPLEMENTARY_FILENAME: (
        "uid",
        "organisationname",
        "normalisedname",
        "fulladdress",
        "city",
        "postcode",
        "registerdate",
        "removeddate",
        "source_register",
        "id_in_source",
    ),
    SIC_FILENAME: ("uid", "SIC"),
}

PAYLOAD_FILENAMES: Tuple[str, ...] = (
    SPINE_FILENAME,
    MATCHES_FILENAME,
    SUPPLEMENTARY_FILENAME,
    SIC_FILENAME,
    GUIDANCE_HTML_FILENAME,
    GUIDANCE_PDF_FILENAME,
    LICENCE_FILENAME,
)

UID_PREFIXES = (
    "CHC",
    "SC",
    "NIC",
    "COH",
    "COOP",
    "MPR",
    "SHR",
    "SHPE",
    "CIS",
    "CQC",
)
UID_RE = re.compile(
    r"^GB-(?:" + "|".join(UID_PREFIXES) + r")-[A-Za-z0-9][A-Za-z0-9._/-]*$"
)
DATE_RE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
SIC_RE = re.compile(r"^\d{4,5}$")
CSO_TYPES = frozenset(
    {"Charity", "CIC", "Co-operative / Mutual", "Other"}
)
OTHER_CSO_SUBTYPES = frozenset({
    "Housing Association",
    "Dormant Company",
    "Property Management Company",
    "Education Institution",
    "Sports Club",
    "Religious Organisation",
    "Arts Organisation",
    "Health Organisation",
    "Social Services Organisation",
    "Professional / Trade Body",
    "Membership Organisation",
    "Other Company Limited By Guarantee",
})
CSO_SUBTYPES = frozenset(
    {"Charity", "CIC", "Co-operative / Mutual"}
) | OTHER_CSO_SUBTYPES
SPINE_SOURCE_REGISTERS = frozenset({
    "Charity Commission for England and Wales",
    "Scottish Charity Register",
    "Charity Commission for Northern Ireland",
    "Companies House",
    "Co-operatives",
    "Mutuals Public Register",
    "Scottish Housing Regulator",
    "Social Housing England",
})
MATCH_TYPES = frozenset({
    "ftc",
    "oscr",
    "companyid - cqc",
    "charityno - cqc",
    "name - cqc",
    "name - crossborder",
    "companyid - coop mutual",
    "companyid - id_in_source",
    "name - housing",
    "name - care",
    "companyid - companyid",
})

SOURCE_UID_PREFIX: Mapping[str, str] = {
    "ccew": "CHC",
    "OSCR": "SC",
    "ccni": "NIC",
    "CH": "COH",
    "CoOps": "COOP",
    "mutuals": "MPR",
    "scottishhousingregulator": "SHR",
    "socialhousingengland": "SHPE",
    "careinspectoratescot": "CIS",
    "carequalitycommission": "CQC",
}

MAX_REPORTED_ERRORS = 100


class ReleaseValidationError(ValueError):
    """Raised when one or more release-contract checks fail."""

    def __init__(self, errors: Sequence[str], omitted: int = 0):
        self.errors = tuple(errors)
        self.omitted = omitted
        suffix = (
            f"\n- ... {omitted:,} additional error(s) omitted"
            if omitted
            else ""
        )
        message = (
            f"Release validation failed with "
            f"{len(self.errors) + omitted:,} error(s):\n- "
            + "\n- ".join(self.errors)
            + suffix
        )
        super().__init__(message)


class ReleasePackagingError(ValueError):
    """Raised when the requested package cannot be created safely."""


@dataclass(frozen=True)
class FileSummary:
    rows: int
    bytes: int
    sha256: str


@dataclass(frozen=True)
class ValidationResult:
    data_dir: Path
    files: Mapping[str, FileSummary]
    metrics: Mapping[str, int]
    warnings: Tuple[str, ...]


@dataclass(frozen=True)
class PackageResult:
    output_dir: Path
    payload_files: Tuple[Path, ...]
    transport_zip: Path | None
    validation: ValidationResult


class _Problems:
    def __init__(self, limit: int = MAX_REPORTED_ERRORS):
        self.limit = limit
        self.errors: List[str] = []
        self.omitted = 0

    def add(self, message: str) -> None:
        if len(self.errors) < self.limit:
            self.errors.append(message)
        else:
            self.omitted += 1

    def raise_if_any(self) -> None:
        if self.errors or self.omitted:
            raise ReleaseValidationError(self.errors, self.omitted)


def _sha256(path: Path) -> Tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            size += len(chunk)
            digest.update(chunk)
    return size, digest.hexdigest()


def _csv_rows(
    path: Path,
    expected_header: Sequence[str],
    problems: _Problems,
) -> Iterator[Tuple[int, Dict[str, str]]]:
    """Yield strict, logical CSV rows after checking the exact header/width."""

    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle, strict=True)
            try:
                header = next(reader)
            except StopIteration:
                problems.add(f"{path.name}: file is empty")
                return
            except csv.Error as exc:
                problems.add(f"{path.name}: cannot read header: {exc}")
                return

            if header != list(expected_header):
                problems.add(
                    f"{path.name}: header is {header!r}; expected "
                    f"{list(expected_header)!r}"
                )
                return

            logical_row = 1
            try:
                for values in reader:
                    logical_row += 1
                    if len(values) != len(expected_header):
                        problems.add(
                            f"{path.name}: logical row {logical_row} "
                            f"(ending on physical line {reader.line_num}) has "
                            f"{len(values)} field(s); expected "
                            f"{len(expected_header)}"
                        )
                        continue
                    yield logical_row, dict(zip(expected_header, values))
            except csv.Error as exc:
                problems.add(
                    f"{path.name}: malformed CSV near physical line "
                    f"{reader.line_num}: {exc}"
                )
    except UnicodeDecodeError as exc:
        problems.add(f"{path.name}: is not valid UTF-8: {exc}")
    except OSError as exc:
        problems.add(f"{path.name}: could not be read: {exc}")


def _valid_uid(uid: str) -> bool:
    return bool(UID_RE.fullmatch(uid))


def _uid_prefix(uid: str) -> str:
    parts = uid.split("-", 2)
    return parts[1] if len(parts) == 3 else ""


def _check_uid(
    filename: str,
    logical_row: int,
    field: str,
    uid: str,
    problems: _Problems,
    *,
    optional: bool = False,
) -> bool:
    if not uid:
        if not optional:
            problems.add(
                f"{filename}: logical row {logical_row} has blank {field}"
            )
        return optional
    if not _valid_uid(uid):
        problems.add(
            f"{filename}: logical row {logical_row} has invalid "
            f"{field} {uid!r}"
        )
        return False
    return True


def _check_date(
    filename: str,
    logical_row: int,
    field: str,
    value: str,
    problems: _Problems,
) -> datetime | None:
    if not value:
        return None
    if not DATE_RE.fullmatch(value):
        problems.add(
            f"{filename}: logical row {logical_row} has {field} "
            f"{value!r}; expected dd/mm/yyyy or blank"
        )
        return None
    try:
        return datetime.strptime(value, "%d/%m/%Y")
    except ValueError:
        problems.add(
            f"{filename}: logical row {logical_row} has impossible "
            f"{field} {value!r}"
        )
        return None


def _row_fingerprint(values: Sequence[str]) -> bytes:
    """Return an unambiguous, stable fingerprint for duplicate detection."""

    digest = hashlib.sha256()
    for value in values:
        encoded = value.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
    return digest.digest()


def _check_source_reference(
    filename: str,
    logical_row: int,
    source_field: str,
    source: str,
    uid_field: str,
    uid: str,
    problems: _Problems,
) -> None:
    expected_prefix = SOURCE_UID_PREFIX.get(source)
    if expected_prefix is None:
        problems.add(
            f"{filename}: logical row {logical_row} has unknown "
            f"{source_field} {source!r}"
        )
    elif _valid_uid(uid) and _uid_prefix(uid) != expected_prefix:
        problems.add(
            f"{filename}: logical row {logical_row} has {source_field} "
            f"{source!r} but {uid_field} {uid!r} does not use "
            f"GB-{expected_prefix}-"
        )


def validate_release(data_dir: Path | str) -> ValidationResult:
    """Validate the four canonical release CSVs.

    Other CSVs in *data_dir* are ignored with a warning.  This is intentional:
    a build work directory may contain intermediates, while the canonical
    filenames and package payload remain an exact whitelist.
    """

    data_dir = Path(data_dir)
    problems = _Problems()
    warnings: List[str] = []

    if not data_dir.is_dir():
        raise ReleaseValidationError(
            [f"data directory does not exist or is not a directory: {data_dir}"]
        )

    paths = {name: data_dir / name for name in CSV_HEADERS}
    for name, path in paths.items():
        if not path.is_file():
            problems.add(f"missing canonical release file: {name}")
    problems.raise_if_any()

    extra_csvs = sorted(
        path.name
        for path in data_dir.glob("*.csv")
        if path.name not in CSV_HEADERS
    )
    if extra_csvs:
        preview = ", ".join(extra_csvs[:8])
        if len(extra_csvs) > 8:
            preview += f", ... ({len(extra_csvs) - 8:,} more)"
        warnings.append(
            f"{len(extra_csvs):,} non-release CSV file(s) were ignored: "
            f"{preview}"
        )

    rows_by_file: Dict[str, int] = {name: 0 for name in CSV_HEADERS}
    metrics: Dict[str, int] = {}

    spine_uids = set()
    active_spine_rows = 0
    removed_spine_rows = 0
    blank_spine_names = 0
    removed_before_registered_rows = 0
    for logical_row, row in _csv_rows(
        paths[SPINE_FILENAME], CSV_HEADERS[SPINE_FILENAME], problems
    ):
        rows_by_file[SPINE_FILENAME] += 1
        uid = row["uid"]
        uid_valid = _check_uid(
            SPINE_FILENAME, logical_row, "uid", uid, problems
        )
        if uid_valid:
            if uid in spine_uids:
                problems.add(
                    f"{SPINE_FILENAME}: logical row {logical_row} duplicates "
                    f"spine uid {uid!r}"
                )
            else:
                spine_uids.add(uid)
        register_date = _check_date(
            SPINE_FILENAME,
            logical_row,
            "registerdate",
            row["registerdate"],
            problems,
        )
        removed_date = _check_date(
            SPINE_FILENAME,
            logical_row,
            "removeddate",
            row["removeddate"],
            problems,
        )
        if (
            register_date is not None
            and removed_date is not None
            and removed_date < register_date
        ):
            removed_before_registered_rows += 1
        if row["removeddate"]:
            removed_spine_rows += 1
        else:
            active_spine_rows += 1
        if not row["organisationname"].strip():
            blank_spine_names += 1
        cso_type = row["cso_type"].strip()
        cso_subtype = row["cso_subtype"].strip()
        is_cic = row["is_cic"].strip()
        source_register = row["source_register"].strip()
        if is_cic not in {"True", "False"}:
            problems.add(
                f"{SPINE_FILENAME}: logical row {logical_row} has is_cic "
                f"{row['is_cic']!r}; expected 'True' or 'False'"
            )
        if source_register not in SPINE_SOURCE_REGISTERS:
            problems.add(
                f"{SPINE_FILENAME}: logical row {logical_row} has "
                f"source_register {row['source_register']!r}; expected one "
                f"of {sorted(SPINE_SOURCE_REGISTERS)!r}"
            )
        if not cso_type:
            problems.add(
                f"{SPINE_FILENAME}: logical row {logical_row} has blank "
                f"cso_type"
            )
        elif cso_type not in CSO_TYPES:
            problems.add(
                f"{SPINE_FILENAME}: logical row {logical_row} has cso_type "
                f"{row['cso_type']!r}; expected one of {sorted(CSO_TYPES)!r}"
            )
        if not cso_subtype:
            problems.add(
                f"{SPINE_FILENAME}: logical row {logical_row} has blank "
                f"cso_subtype"
            )
        elif cso_subtype not in CSO_SUBTYPES:
            problems.add(
                f"{SPINE_FILENAME}: logical row {logical_row} has "
                f"cso_subtype {row['cso_subtype']!r}; expected one of "
                f"{sorted(CSO_SUBTYPES)!r}"
            )
        elif cso_type in {"Charity", "CIC", "Co-operative / Mutual"}:
            if cso_subtype != cso_type:
                problems.add(
                    f"{SPINE_FILENAME}: logical row {logical_row} has "
                    f"cso_type {cso_type!r} but cso_subtype "
                    f"{cso_subtype!r}; these types must pass through"
                )
        elif cso_type == "Other" and cso_subtype not in OTHER_CSO_SUBTYPES:
            problems.add(
                f"{SPINE_FILENAME}: logical row {logical_row} has Other "
                f"cso_type but incompatible cso_subtype {cso_subtype!r}"
            )
        if (cso_type == "CIC") != (is_cic == "True"):
            problems.add(
                f"{SPINE_FILENAME}: logical row {logical_row} has "
                f"inconsistent is_cic {is_cic!r} and cso_type "
                f"{cso_type!r}"
            )

    match_endpoints = set()
    match_keys: Dict[Tuple[str, str, str], int] = {}
    blank_match_references = 0
    for logical_row, row in _csv_rows(
        paths[MATCHES_FILENAME], CSV_HEADERS[MATCHES_FILENAME], problems
    ):
        rows_by_file[MATCHES_FILENAME] += 1
        uid = row["uid"]
        org_a = row["orgA_uid"]
        org_b = row["orgB_uid"]
        uid_valid = _check_uid(
            MATCHES_FILENAME,
            logical_row,
            "uid",
            uid,
            problems,
            optional=True,
        )
        org_a_valid = _check_uid(
            MATCHES_FILENAME,
            logical_row,
            "orgA_uid",
            org_a,
            problems,
        )
        org_b_valid = _check_uid(
            MATCHES_FILENAME,
            logical_row,
            "orgB_uid",
            org_b,
            problems,
        )

        for field in (
            "orgA_id_in_source",
            "orgA_source",
            "orgB_id_in_source",
            "orgB_source",
            "match_type",
        ):
            if not row[field].strip():
                problems.add(
                    f"{MATCHES_FILENAME}: logical row {logical_row} has "
                    f"blank {field}"
                )

        if row["match_type"].strip() not in MATCH_TYPES:
            problems.add(
                f"{MATCHES_FILENAME}: logical row {logical_row} has "
                f"match_type {row['match_type']!r}; expected one of "
                f"{sorted(MATCH_TYPES)!r}"
            )

        if org_a_valid:
            match_endpoints.add(org_a)
            if org_a not in spine_uids:
                problems.add(
                    f"{MATCHES_FILENAME}: logical row {logical_row} has "
                    f"orgA_uid {org_a!r}, which is not a spine uid"
                )
        if org_b_valid:
            match_endpoints.add(org_b)
        if org_a and org_b and org_a == org_b:
            problems.add(
                f"{MATCHES_FILENAME}: logical row {logical_row} is a "
                f"self-match for {org_a!r}"
            )

        if uid:
            if uid_valid and uid not in spine_uids:
                problems.add(
                    f"{MATCHES_FILENAME}: logical row {logical_row} has uid "
                    f"{uid!r}, which is not a spine uid"
                )
            if uid != org_a:
                problems.add(
                    f"{MATCHES_FILENAME}: logical row {logical_row} has uid "
                    f"{uid!r}; a nonblank uid must equal orgA_uid "
                    f"{org_a!r}"
                )
        else:
            blank_match_references += 1

        _check_source_reference(
            MATCHES_FILENAME,
            logical_row,
            "orgA_source",
            row["orgA_source"],
            "orgA_uid",
            org_a,
            problems,
        )
        _check_source_reference(
            MATCHES_FILENAME,
            logical_row,
            "orgB_source",
            row["orgB_source"],
            "orgB_uid",
            org_b,
            problems,
        )

        if org_a and org_b and row["match_type"]:
            pair = tuple(sorted((org_a, org_b)))
            key = (pair[0], pair[1], row["match_type"])
            previous_row = match_keys.get(key)
            if previous_row is not None:
                problems.add(
                    f"{MATCHES_FILENAME}: logical row {logical_row} repeats "
                    f"the unordered endpoint pair and match_type from "
                    f"logical row {previous_row}: {key!r}"
                )
            else:
                match_keys[key] = logical_row

    release_uids = spine_uids | match_endpoints

    supplementary_uids = set()
    supplementary_fingerprints: Dict[bytes, int] = {}
    empty_supplementary_rows = 0
    for logical_row, row in _csv_rows(
        paths[SUPPLEMENTARY_FILENAME],
        CSV_HEADERS[SUPPLEMENTARY_FILENAME],
        problems,
    ):
        rows_by_file[SUPPLEMENTARY_FILENAME] += 1
        fingerprint = _row_fingerprint(
            tuple(row[field] for field in CSV_HEADERS[SUPPLEMENTARY_FILENAME])
        )
        previous_row = supplementary_fingerprints.get(fingerprint)
        if previous_row is not None:
            problems.add(
                f"{SUPPLEMENTARY_FILENAME}: logical row {logical_row} is an "
                f"exact duplicate of logical row {previous_row}"
            )
        else:
            supplementary_fingerprints[fingerprint] = logical_row
        uid = row["uid"]
        uid_valid = _check_uid(
            SUPPLEMENTARY_FILENAME, logical_row, "uid", uid, problems
        )
        if uid_valid:
            supplementary_uids.add(uid)
            if uid not in release_uids:
                problems.add(
                    f"{SUPPLEMENTARY_FILENAME}: logical row {logical_row} "
                    f"references uid {uid!r}, which is outside the release "
                    f"uid universe"
                )
        _check_date(
            SUPPLEMENTARY_FILENAME,
            logical_row,
            "registerdate",
            row["registerdate"],
            problems,
        )
        _check_date(
            SUPPLEMENTARY_FILENAME,
            logical_row,
            "removeddate",
            row["removeddate"],
            problems,
        )
        content_fields = (
            "organisationname",
            "normalisedname",
            "fulladdress",
            "city",
            "postcode",
            "registerdate",
            "removeddate",
            "id_in_source",
        )
        if not any(row[field].strip() for field in content_fields):
            empty_supplementary_rows += 1

    sic_uids = set()
    sic_pairs: Dict[Tuple[str, str], int] = {}
    four_digit_sic_rows = 0
    five_digit_sic_rows = 0
    for logical_row, row in _csv_rows(
        paths[SIC_FILENAME], CSV_HEADERS[SIC_FILENAME], problems
    ):
        rows_by_file[SIC_FILENAME] += 1
        uid = row["uid"]
        sic = row["SIC"]
        uid_valid = _check_uid(
            SIC_FILENAME, logical_row, "uid", uid, problems
        )
        if uid_valid:
            sic_uids.add(uid)
            if uid not in release_uids:
                problems.add(
                    f"{SIC_FILENAME}: logical row {logical_row} references "
                    f"uid {uid!r}, which is outside the release uid universe"
                )
        if not SIC_RE.fullmatch(sic):
            problems.add(
                f"{SIC_FILENAME}: logical row {logical_row} has SIC "
                f"{sic!r}; expected one nonblank 4- or 5-digit code"
            )
        elif len(sic) == 4:
            four_digit_sic_rows += 1
        else:
            five_digit_sic_rows += 1

        if uid and sic:
            key = (uid, sic)
            previous_row = sic_pairs.get(key)
            if previous_row is not None:
                problems.add(
                    f"{SIC_FILENAME}: logical row {logical_row} duplicates "
                    f"uid/SIC pair from logical row {previous_row}: {key!r}"
                )
            else:
                sic_pairs[key] = logical_row

    for filename, row_count in rows_by_file.items():
        if row_count == 0:
            problems.add(f"{filename}: has no data rows")

    problems.raise_if_any()

    if blank_spine_names:
        warnings.append(
            f"{blank_spine_names:,} spine row(s) have a blank "
            f"organisationname"
        )
    if removed_before_registered_rows:
        warnings.append(
            f"{removed_before_registered_rows:,} spine row(s) have a "
            f"removeddate earlier than registerdate"
        )
    if blank_match_references:
        warnings.append(
            f"{blank_match_references:,} match row(s) have a blank optional "
            f"uid reference"
        )
    if empty_supplementary_rows:
        warnings.append(
            f"{empty_supplementary_rows:,} supplementary row(s) contain no "
            f"detail beyond uid/source metadata"
        )

    files: Dict[str, FileSummary] = {}
    for name, path in paths.items():
        size, digest = _sha256(path)
        files[name] = FileSummary(
            rows=rows_by_file[name], bytes=size, sha256=digest
        )

    metrics.update(
        {
            "spine_uids": len(spine_uids),
            "active_spine_rows": active_spine_rows,
            "removed_spine_rows": removed_spine_rows,
            "removed_before_registered_rows": (
                removed_before_registered_rows
            ),
            "match_endpoints": len(match_endpoints),
            "release_uids": len(release_uids),
            "supplementary_uids": len(supplementary_uids),
            "sic_uids": len(sic_uids),
            "four_digit_sic_rows": four_digit_sic_rows,
            "five_digit_sic_rows": five_digit_sic_rows,
        }
    )
    return ValidationResult(
        data_dir=data_dir.resolve(),
        files=files,
        metrics=metrics,
        warnings=tuple(warnings),
    )


def format_validation_report(result: ValidationResult) -> str:
    lines = [f"Release validation passed: {result.data_dir}"]
    for name in CSV_HEADERS:
        summary = result.files[name]
        lines.append(
            f"  {name}: {summary.rows:,} logical rows; "
            f"{summary.bytes:,} bytes; sha256 {summary.sha256}"
        )
    lines.extend(
        (
            f"  spine uids: {result.metrics['spine_uids']:,} "
            f"({result.metrics['active_spine_rows']:,} active; "
            f"{result.metrics['removed_spine_rows']:,} removed)",
            f"  release uid universe: {result.metrics['release_uids']:,}",
            f"  supplementary uids: "
            f"{result.metrics['supplementary_uids']:,}",
            f"  SIC uids: {result.metrics['sic_uids']:,} "
            f"({result.metrics['four_digit_sic_rows']:,} four-digit rows; "
            f"{result.metrics['five_digit_sic_rows']:,} five-digit rows)",
        )
    )
    if result.warnings:
        lines.append("Warnings:")
        lines.extend(f"  - {warning}" for warning in result.warnings)
    else:
        lines.append("Warnings: none")
    return "\n".join(lines)


def _check_package_input(
    path: Path,
    expected_name: str,
    description: str,
) -> None:
    if path.name != expected_name:
        raise ReleasePackagingError(
            f"{description} must be named {expected_name!r}, got "
            f"{path.name!r}"
        )
    if not path.is_file():
        raise ReleasePackagingError(
            f"{description} does not exist or is not a file: {path}"
        )
    if path.stat().st_size == 0:
        raise ReleasePackagingError(f"{description} is empty: {path}")


def _write_deterministic_zip(zip_path: Path, payload_dir: Path) -> None:
    """Write a byte-reproducible ZIP with no directory or wildcard members."""

    with zipfile.ZipFile(
        zip_path,
        mode="x",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for name in PAYLOAD_FILENAMES:
            source = payload_dir / name
            info = zipfile.ZipInfo(
                filename=name,
                date_time=(1980, 1, 1, 0, 0, 0),
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (0o100644 & 0xFFFF) << 16
            info.internal_attr = 0
            info.comment = b""
            info.extra = b""
            info.file_size = source.stat().st_size
            # ZipFile.open() otherwise receives no public per-member
            # compression-level argument.  ZipInfo uses this field internally.
            info._compresslevel = 9
            with source.open("rb") as source_handle:
                with archive.open(info, mode="w") as member:
                    shutil.copyfileobj(
                        source_handle, member, length=1024 * 1024
                    )


def prepare_release(
    data_dir: Path | str,
    guidance_html: Path | str,
    guidance_pdf: Path | str,
    licence_file: Path | str,
    output_dir: Path | str,
    *,
    create_zip: bool = True,
) -> PackageResult:
    """Validate and copy only the seven canonical public payload files.

    *output_dir* must not already exist.  It is populated through a temporary
    sibling and renamed only after every copy (and optional ZIP) succeeds.
    """

    data_dir = Path(data_dir)
    guidance_html = Path(guidance_html)
    guidance_pdf = Path(guidance_pdf)
    licence_file = Path(licence_file)
    output_dir = Path(output_dir)

    if output_dir.exists():
        raise ReleasePackagingError(
            f"output directory already exists; refusing to overwrite: "
            f"{output_dir}"
        )

    _check_package_input(
        guidance_html, GUIDANCE_HTML_FILENAME, "guidance HTML"
    )
    _check_package_input(
        guidance_pdf, GUIDANCE_PDF_FILENAME, "guidance PDF"
    )
    _check_package_input(licence_file, LICENCE_FILENAME, "licence")
    with guidance_pdf.open("rb") as handle:
        if handle.read(5) != b"%PDF-":
            raise ReleasePackagingError(
                f"guidance PDF does not start with a PDF signature: "
                f"{guidance_pdf}"
            )

    validation = validate_release(data_dir)

    try:
        guidance_text = guidance_html.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ReleasePackagingError(
            f"guidance HTML could not be read as UTF-8: {exc}"
        ) from exc
    expected_guidance_counts = (
        validation.files[SPINE_FILENAME].rows,
        validation.files[MATCHES_FILENAME].rows,
        validation.files[SUPPLEMENTARY_FILENAME].rows,
        validation.files[SIC_FILENAME].rows,
        validation.metrics["active_spine_rows"],
        validation.metrics["removed_spine_rows"],
    )
    missing_guidance_counts = sorted(
        {
            f"{count:,}"
            for count in expected_guidance_counts
            if f"{count:,}" not in guidance_text
        }
    )
    if missing_guidance_counts:
        raise ReleasePackagingError(
            "guidance HTML is stale: it does not contain release count(s) "
            + ", ".join(missing_guidance_counts)
        )

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary_dir = Path(
        tempfile.mkdtemp(
            prefix=f".{output_dir.name}.tmp-",
            dir=str(output_dir.parent),
        )
    )
    transport_zip: Path | None = None
    try:
        source_by_name = {
            SPINE_FILENAME: data_dir / SPINE_FILENAME,
            MATCHES_FILENAME: data_dir / MATCHES_FILENAME,
            SUPPLEMENTARY_FILENAME: data_dir / SUPPLEMENTARY_FILENAME,
            SIC_FILENAME: data_dir / SIC_FILENAME,
            GUIDANCE_HTML_FILENAME: guidance_html,
            GUIDANCE_PDF_FILENAME: guidance_pdf,
            LICENCE_FILENAME: licence_file,
        }
        for name in PAYLOAD_FILENAMES:
            shutil.copyfile(source_by_name[name], temporary_dir / name)

        if create_zip:
            _write_deterministic_zip(
                temporary_dir / TRANSPORT_ZIP_FILENAME, temporary_dir
            )

        # Guard the no-overwrite promise against a concurrent creator.
        if output_dir.exists():
            raise ReleasePackagingError(
                f"output directory appeared during packaging; refusing to "
                f"overwrite: {output_dir}"
            )
        temporary_dir.rename(output_dir)
        if create_zip:
            transport_zip = output_dir / TRANSPORT_ZIP_FILENAME
    except Exception:
        shutil.rmtree(temporary_dir, ignore_errors=True)
        raise

    return PackageResult(
        output_dir=output_dir.resolve(),
        payload_files=tuple(
            (output_dir / name).resolve() for name in PAYLOAD_FILENAMES
        ),
        transport_zip=(
            transport_zip.resolve() if transport_zip is not None else None
        ),
        validation=validation,
    )


def format_package_report(result: PackageResult) -> str:
    lines = [
        f"Release package created: {result.output_dir}",
        "Payload:",
    ]
    lines.extend(f"  {path.name}" for path in result.payload_files)
    if result.transport_zip is not None:
        size, digest = _sha256(result.transport_zip)
        lines.append(
            f"Transport ZIP: {result.transport_zip.name}; {size:,} bytes; "
            f"sha256 {digest}"
        )
    else:
        lines.append("Transport ZIP: not requested")
    return "\n".join(lines)
