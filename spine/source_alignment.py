"""Population-level validation against the latest authoritative registers.

The ordinary release checks validate the internal consistency of the four
published CSVs.  They cannot detect a historically plausible but stale status,
for example an active charity whose final spine row still carries an old
removal date.  This module provides that separate source-alignment release
gate.

Run it after building ``TSCS_spine.spine.csv`` and before packaging a release::

    python -m spine.source_alignment \
      --spine ../public_spine_data/TSCS_spine.spine.csv \
      --matches ../public_spine_data/TSCS_spine.matches.csv \
      --ccew ../raw_data/ccew/ccew-publicextract.jul2026.csv \
      --oscr ../raw_data/oscr/CharityExport-17-Jul-2026.csv \
      --ccni ../raw_data/ccni/register_charitydetails_2026_07_18.csv \
      --companies-house ../raw_data/CH.all.csv

The CCEW, OSCR and CCNI arguments must name the current register snapshots,
not their historical/removal extracts. The Companies House argument is the
processed chronological ``CH.all.csv`` input; only organisations seen in its
newest monthly bulk snapshot or a later dated refresh are treated as current.
CE-prefix CIO status is deferred to the newer CCEW snapshot. Exit status is
zero only when every organisation which is active in its latest authoritative
source record resolves to a final spine row with a blank ``removeddate``.
Direct UIDs resolve to themselves; absorbed UIDs resolve through nonblank
``matches.uid`` values. Association-only match rows have a blank ``uid`` and
are deliberately ignored.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Iterable, Iterator, Mapping, Sequence, TextIO


class SourceAlignmentInputError(ValueError):
    """Raised when an input cannot support a trustworthy alignment check."""


@dataclass(frozen=True)
class SourceAlignmentResult:
    """Alignment metrics for one authoritative register."""

    source: str
    active_source_uids: int
    active_direct_spine_uids: int
    active_effective_source_uids: int
    active_effective_parent_uids: int
    unresolved_source_uids: tuple[str, ...]
    false_removed_links: tuple[tuple[str, str], ...]

    @property
    def unresolved_count(self) -> int:
        return len(self.unresolved_source_uids)

    @property
    def false_removed_source_count(self) -> int:
        return len(self.false_removed_links)

    @property
    def false_removed_direct_source_count(self) -> int:
        return sum(
            source_uid == parent_uid
            for source_uid, parent_uid in self.false_removed_links
        )

    @property
    def false_removed_uids(self) -> tuple[str, ...]:
        """Unique effective final parent UIDs with stale removal dates."""

        return tuple(sorted({parent for _, parent in self.false_removed_links}))

    @property
    def false_removed_count(self) -> int:
        """Unique false-removed effective parent count for this source."""

        return len(self.false_removed_uids)


@dataclass(frozen=True)
class SourceAlignmentReport:
    """Complete population-level status-alignment result."""

    spine_rows: int
    results: tuple[SourceAlignmentResult, ...]

    @property
    def unresolved_count(self) -> int:
        return sum(result.unresolved_count for result in self.results)

    @property
    def false_removed_source_count(self) -> int:
        return sum(
            result.false_removed_source_count for result in self.results
        )

    @property
    def false_removed_uids(self) -> tuple[str, ...]:
        """Unique false-removed final parents across all source registers."""

        return tuple(
            sorted({
                uid
                for result in self.results
                for uid in result.false_removed_uids
            })
        )

    @property
    def false_removed_count(self) -> int:
        return len(self.false_removed_uids)

    @property
    def passed(self) -> bool:
        return self.false_removed_count == 0 and self.unresolved_count == 0


def _clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def _rows(
    path: Path | str,
    required_fields: Iterable[str],
    *,
    encoding: str = "utf-8-sig",
) -> Iterator[Mapping[str, str]]:
    """Yield dictionaries after validating that the required fields exist."""

    path = Path(path)
    required = set(required_fields)
    try:
        handle = path.open("r", encoding=encoding, newline="")
    except (OSError, UnicodeError) as exc:
        raise SourceAlignmentInputError(f"Cannot open {path}: {exc}") from exc

    with handle:
        try:
            reader = csv.DictReader(handle)
            fields = set(reader.fieldnames or ())
            missing = sorted(required - fields)
            if missing:
                raise SourceAlignmentInputError(
                    f"{path} is missing required column(s): "
                    + ", ".join(missing)
                )
            yield from reader
        except (csv.Error, UnicodeError) as exc:
            raise SourceAlignmentInputError(
                f"Cannot parse {path} as CSV: {exc}"
            ) from exc


def load_final_spine(path: Path | str) -> Dict[str, str]:
    """Return direct spine UID -> final removed date, rejecting duplicates."""

    result: Dict[str, str] = {}
    for row in _rows(path, ("uid", "removeddate")):
        uid = _clean(row["uid"])
        if not uid:
            raise SourceAlignmentInputError(f"{path} contains a blank spine UID")
        if uid in result:
            raise SourceAlignmentInputError(
                f"{path} contains duplicate spine UID {uid!r}"
            )
        result[uid] = _clean(row["removeddate"])
    if not result:
        raise SourceAlignmentInputError(f"{path} contains no spine rows")
    return result


def load_absorption_parents(
    path: Path | str,
    final_spine: Mapping[str, str],
) -> Dict[str, str]:
    """Return consolidated endpoint UID -> effective final spine parent.

    Only rows with a nonblank ``uid`` describe consolidation.  A blank
    ``matches.uid`` is an association/link only and must never reassign the
    status of either endpoint.
    """

    parents: Dict[str, str] = {}
    for row in _rows(path, ("uid", "orgA_uid", "orgB_uid")):
        parent = _clean(row["uid"])
        if not parent:
            continue
        org_a = _clean(row["orgA_uid"])
        org_b = _clean(row["orgB_uid"])
        if not org_a or not org_b:
            raise SourceAlignmentInputError(
                f"{path} has a nonblank matches.uid but a blank endpoint"
            )
        if parent not in (org_a, org_b):
            raise SourceAlignmentInputError(
                f"{path} maps {org_a!r} and {org_b!r} to unrelated "
                f"matches.uid {parent!r}"
            )
        if parent not in final_spine:
            raise SourceAlignmentInputError(
                f"{path} maps an endpoint to {parent!r}, which is absent "
                "from the final spine"
            )

        for endpoint in (org_a, org_b, parent):
            if (
                endpoint in final_spine
                and endpoint != parent
            ):
                raise SourceAlignmentInputError(
                    f"{path} marks direct final spine UID {endpoint!r} as "
                    f"absorbed into {parent!r}"
                )
            previous = parents.get(endpoint)
            if previous is not None and previous != parent:
                raise SourceAlignmentInputError(
                    f"{path} maps endpoint {endpoint!r} to conflicting "
                    f"parents {previous!r} and {parent!r}"
                )
            parents[endpoint] = parent
    return parents


def _numeric_identifier(value: object, field: str, path: Path | str) -> str:
    """Normalise integer-looking register identifiers without losing padding."""

    identifier = _clean(value)
    if identifier.endswith(".0") and identifier[:-2].isdigit():
        identifier = identifier[:-2]
    if not identifier or not identifier.isdigit():
        raise SourceAlignmentInputError(
            f"{path} contains invalid {field} {value!r}"
        )
    return identifier


def active_ccew_uids(path: Path | str) -> set[str]:
    """Return active primary (linked-charity zero) CCEW organisation UIDs."""

    required = (
        "registered_charity_number",
        "linked_charity_number",
        "charity_registration_status",
        "date_of_removal",
    )
    active = set()
    primary_rows = 0
    for row in _rows(path, required):
        linked = _numeric_identifier(
            row["linked_charity_number"],
            "linked_charity_number",
            path,
        )
        if int(linked) != 0:
            continue
        primary_rows += 1
        status = _clean(row["charity_registration_status"]).casefold()
        removed = bool(_clean(row["date_of_removal"]))
        if status not in {"registered", "removed"}:
            raise SourceAlignmentInputError(
                f"{path} contains unexpected CCEW primary status "
                f"{row['charity_registration_status']!r}"
            )
        if (status == "removed") != removed:
            number = _clean(row["registered_charity_number"])
            raise SourceAlignmentInputError(
                f"{path} has contradictory status/removal fields for CCEW "
                f"charity {number!r}"
            )
        if not removed:
            number = _numeric_identifier(
                row["registered_charity_number"],
                "registered_charity_number",
                path,
            )
            active.add(f"GB-CHC-{number}")
    if primary_rows == 0:
        raise SourceAlignmentInputError(
            f"{path} contains no CCEW primary linked-charity-zero rows"
        )
    return active


def active_oscr_uids(path: Path | str) -> set[str]:
    """Return UIDs from an OSCR current-register export.

    A removed-register export is rejected instead of producing a misleading
    zero-sized active population.
    """

    active = set()
    for row in _rows(path, ("Charity Number", "Charity Status")):
        status = _clean(row["Charity Status"]).casefold()
        if status == "removed" or _clean(row.get("Ceased Date")):
            raise SourceAlignmentInputError(
                f"{path} contains removed OSCR records; pass the current "
                "CharityExport file, not CharityExport-Removed"
            )
        number = _clean(row["Charity Number"]).upper()
        if not number.startswith("SC") or not number[2:].isdigit():
            raise SourceAlignmentInputError(
                f"{path} contains invalid OSCR Charity Number "
                f"{row['Charity Number']!r}"
            )
        active.add(f"GB-SC-{number}")
    if not active:
        raise SourceAlignmentInputError(
            f"{path} contains no current OSCR records"
        )
    return active


def active_ccni_uids(
    path: Path | str,
    *,
    encoding: str = "latin-1",
) -> set[str]:
    """Return non-Removed UIDs from the latest CCNI register export."""

    active = set()
    seen = 0
    for row in _rows(
        path,
        ("Reg charity number", "Status"),
        encoding=encoding,
    ):
        seen += 1
        if _clean(row["Status"]).casefold() == "removed":
            continue
        number = _numeric_identifier(
            row["Reg charity number"], "Reg charity number", path
        )
        active.add(f"GB-NIC-{number}")
    if seen == 0:
        raise SourceAlignmentInputError(f"{path} contains no CCNI records")
    return active


def parse_iteration(value: object) -> date:
    """Parse CH chronology tags using start-of-period semantics.

    ``YYYY`` and ``MM/YYYY`` represent the first day of that year/month.
    A dated refresh should therefore use ``DD/MM/YYYY`` so that it outranks a
    monthly bulk snapshot from the same month.
    """

    text = _clean(value)
    formats = (
        ("%d/%m/%Y", None),
        ("%m/%Y", 1),
        ("%Y", 1),
    )
    for format_string, default_day in formats:
        try:
            parsed = datetime.strptime(text, format_string).date()
        except ValueError:
            continue
        if format_string == "%Y":
            return date(parsed.year, 1, 1)
        if default_day is not None:
            return date(parsed.year, parsed.month, default_day)
        return parsed
    raise SourceAlignmentInputError(
        f"Invalid Companies House iteration {value!r}; expected YYYY, "
        "MM/YYYY or DD/MM/YYYY"
    )


def active_companies_house_uids(path: Path | str) -> set[str]:
    """Return CH UIDs whose latest authoritative processed row is active.

    ``CH.all.csv`` also contains historical bootstrap observations (currently
    tagged 2000 and 2022). A blank removal date on one of those rows means
    that its status was unknown at that historical cut, not that Companies
    House confirms it is active today. The current population is therefore
    limited to organisations observed in the newest monthly bulk snapshot or
    a later date-specific refresh.

    CE-prefixed records are English/Welsh charitable incorporated
    organisations. Their legal charity status is taken from the newer CCEW
    snapshot, matching the build's source-precedence rule, so their older
    Companies House bulk status is not checked a second time here.

    Equal-date rows are collapsed conservatively: a removal wins the tie.
    This prevents duplicated name/detail rows from making a genuinely removed
    company look active.
    """

    latest: Dict[str, tuple[date, bool]] = {}
    latest_monthly_snapshot: date | None = None
    for row in _rows(path, ("uid", "iteration", "removeddate")):
        uid = _clean(row["uid"])
        if not uid.startswith("GB-COH-") or not uid[len("GB-COH-") :]:
            raise SourceAlignmentInputError(
                f"{path} contains invalid Companies House UID {uid!r}"
            )
        try:
            iteration = parse_iteration(row["iteration"])
        except SourceAlignmentInputError as exc:
            raise SourceAlignmentInputError(f"{path}: {exc}") from exc
        if _clean(row["iteration"]).count("/") == 1:
            if (
                latest_monthly_snapshot is None
                or iteration > latest_monthly_snapshot
            ):
                latest_monthly_snapshot = iteration
        removed = bool(_clean(row["removeddate"]))
        previous = latest.get(uid)
        if previous is None or iteration > previous[0]:
            latest[uid] = (iteration, removed)
        elif iteration == previous[0]:
            latest[uid] = (iteration, previous[1] or removed)
    if not latest:
        raise SourceAlignmentInputError(
            f"{path} contains no Companies House rows"
        )
    if latest_monthly_snapshot is None:
        raise SourceAlignmentInputError(
            f"{path} contains no MM/YYYY Companies House bulk snapshot; "
            "current active status cannot be distinguished from historical "
            "bootstrap rows"
        )
    return {
        uid
        for uid, (latest_iteration, latest_removed) in latest.items()
        if (
            latest_iteration >= latest_monthly_snapshot
            and not latest_removed
            and not uid.startswith("GB-COH-CE")
        )
    }


def _compare_source(
    source: str,
    active_uids: set[str],
    final_spine: Mapping[str, str],
    absorption_parents: Mapping[str, str],
) -> SourceAlignmentResult:
    direct = active_uids.intersection(final_spine)
    effective = {
        uid: (
            uid
            if uid in final_spine
            else absorption_parents.get(uid, "")
        )
        for uid in active_uids
    }
    unresolved = tuple(sorted(
        uid for uid, parent in effective.items() if not parent
    ))
    resolved = {
        uid: parent
        for uid, parent in effective.items()
        if parent
    }
    false_removed_links = tuple(
        sorted(
            (uid, parent)
            for uid, parent in resolved.items()
            if final_spine[parent]
        )
    )
    return SourceAlignmentResult(
        source=source,
        active_source_uids=len(active_uids),
        active_direct_spine_uids=len(direct),
        active_effective_source_uids=len(resolved),
        active_effective_parent_uids=len(set(resolved.values())),
        unresolved_source_uids=unresolved,
        false_removed_links=false_removed_links,
    )


def check_source_alignment(
    *,
    spine: Path | str,
    matches: Path | str,
    ccew: Path | str,
    oscr: Path | str,
    ccni: Path | str,
    companies_house: Path | str,
    ccni_encoding: str = "latin-1",
) -> SourceAlignmentReport:
    """Compare current source status with direct or absorbed final rows."""

    final_spine = load_final_spine(spine)
    absorption_parents = load_absorption_parents(matches, final_spine)
    sources = (
        ("CCEW", active_ccew_uids(ccew)),
        ("OSCR", active_oscr_uids(oscr)),
        (
            "CCNI",
            active_ccni_uids(ccni, encoding=ccni_encoding),
        ),
        (
            "Companies House",
            active_companies_house_uids(companies_house),
        ),
    )
    return SourceAlignmentReport(
        spine_rows=len(final_spine),
        results=tuple(
            _compare_source(
                source,
                active,
                final_spine,
                absorption_parents,
            )
            for source, active in sources
        ),
    )


def format_report(
    report: SourceAlignmentReport,
    *,
    max_examples: int = 10,
) -> str:
    """Return a compact human-readable pass/fail report."""

    status = "PASS" if report.passed else "FAIL"
    lines = [
        f"Source-alignment gate: {status}",
        f"Final spine rows: {report.spine_rows:,}",
        "",
        (
            "Source | active source UIDs | direct coverage | effective "
            "coverage | effective parents | unresolved | false-removed "
            "source UIDs | false-removed parents"
        ),
        "--- | ---: | ---: | ---: | ---: | ---: | ---: | ---:",
    ]
    for result in report.results:
        lines.append(
            f"{result.source} | {result.active_source_uids:,} | "
            f"{result.active_direct_spine_uids:,} | "
            f"{result.active_effective_source_uids:,} | "
            f"{result.active_effective_parent_uids:,} | "
            f"{result.unresolved_count:,} | "
            f"{result.false_removed_source_count:,} | "
            f"{result.false_removed_count:,}"
        )
    lines.extend((
        "",
        f"Total unresolved active source UIDs: {report.unresolved_count:,}",
        (
            "Total false-removed active source UIDs: "
            f"{report.false_removed_source_count:,}"
        ),
        (
            "Unique false-removed effective parents: "
            f"{report.false_removed_count:,}"
        ),
    ))
    for result in report.results:
        if not result.false_removed_links:
            continue
        examples = ", ".join(
            (
                parent_uid
                if source_uid == parent_uid
                else f"{source_uid} -> {parent_uid}"
            )
            for source_uid, parent_uid
            in result.false_removed_links[:max_examples]
        )
        omitted = result.false_removed_source_count - max_examples
        suffix = f" (+{omitted:,} more)" if omitted > 0 else ""
        lines.append(f"{result.source} examples: {examples}{suffix}")
    for result in report.results:
        if not result.unresolved_source_uids:
            continue
        examples = ", ".join(
            result.unresolved_source_uids[:max_examples]
        )
        omitted = result.unresolved_count - max_examples
        suffix = f" (+{omitted:,} more)" if omitted > 0 else ""
        lines.append(
            f"{result.source} unresolved examples: {examples}{suffix}"
        )
    return "\n".join(lines)


def _json_report(report: SourceAlignmentReport) -> str:
    payload = {
        "passed": report.passed,
        "spine_rows": report.spine_rows,
        "unresolved_source_count": report.unresolved_count,
        "false_removed_source_count": report.false_removed_source_count,
        "false_removed_parent_count": report.false_removed_count,
        "false_removed_parent_uids": report.false_removed_uids,
        "sources": [
            {
                "source": result.source,
                "active_source_uids": result.active_source_uids,
                "active_direct_spine_uids": result.active_direct_spine_uids,
                "active_effective_source_uids": (
                    result.active_effective_source_uids
                ),
                "active_effective_parent_uids": (
                    result.active_effective_parent_uids
                ),
                "unresolved_source_count": result.unresolved_count,
                "unresolved_source_uids": result.unresolved_source_uids,
                "false_removed_source_count": (
                    result.false_removed_source_count
                ),
                "false_removed_direct_source_count": (
                    result.false_removed_direct_source_count
                ),
                "false_removed_parent_count": result.false_removed_count,
                "false_removed_parent_uids": result.false_removed_uids,
                "false_removed_links": [
                    {
                        "source_uid": source_uid,
                        "effective_parent_uid": parent_uid,
                    }
                    for source_uid, parent_uid
                    in result.false_removed_links
                ],
            }
            for result in report.results
        ],
    }
    return json.dumps(payload, indent=2)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Fail when a currently active authoritative-register record "
            "is unresolved or its direct/absorbing final spine row has a "
            "nonblank removeddate."
        )
    )
    parser.add_argument("--spine", required=True, type=Path)
    parser.add_argument(
        "--matches",
        required=True,
        type=Path,
        help=(
            "Final TSCS matches CSV; only rows with nonblank uid resolve "
            "absorbed source records"
        ),
    )
    parser.add_argument("--ccew", required=True, type=Path)
    parser.add_argument("--oscr", required=True, type=Path)
    parser.add_argument("--ccni", required=True, type=Path)
    parser.add_argument(
        "--companies-house",
        required=True,
        type=Path,
        help="Processed chronological CH.all.csv input",
    )
    parser.add_argument(
        "--ccni-encoding",
        default="latin-1",
        help="CCNI CSV encoding (default: latin-1)",
    )
    parser.add_argument(
        "--max-examples",
        type=int,
        default=10,
        help="Maximum example UIDs printed per failing source (default: 10)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit a machine-readable JSON report",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    """CLI entry point: 0 passes, 1 finds stale removals, 2 rejects inputs."""

    args = _parser().parse_args(argv)
    if args.max_examples < 0:
        print("--max-examples must be zero or greater", file=stderr)
        return 2
    try:
        report = check_source_alignment(
            spine=args.spine,
            matches=args.matches,
            ccew=args.ccew,
            oscr=args.oscr,
            ccni=args.ccni,
            companies_house=args.companies_house,
            ccni_encoding=args.ccni_encoding,
        )
    except SourceAlignmentInputError as exc:
        print(f"Source-alignment input error: {exc}", file=stderr)
        return 2

    output = (
        _json_report(report)
        if args.as_json
        else format_report(report, max_examples=args.max_examples)
    )
    print(output, file=stdout)
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
