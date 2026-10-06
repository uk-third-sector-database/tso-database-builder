"""Adjudicate the differences between two Spine (Organisation Register) releases.

Given a prior release directory and a new release directory (each holding the four
public release files TSCS_spine.spine.csv, TSCS_spine.matches.csv,
TSCS_spine.supplementary.csv and TSCS_spine.SIC_codes.csv), this script works out
what changed and, crucially, *where every disappearing organisation went*: an
organisation that leaves the spine should reappear as the junior partner of a
match row, not simply vanish.

It writes a markdown report (delta-report.md) and a set of supporting CSVs into
OUT_DIR.  Nothing is read except the four release files, so the comparison is
reproducible from published artefacts alone.

Usage:
    python compare_releases.py PRIOR_DIR NEW_DIR OUT_DIR
"""

from __future__ import annotations

import os
import sys
from collections import Counter

import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SPINE_FILE = "TSCS_spine.spine.csv"
MATCHES_FILE = "TSCS_spine.matches.csv"
SUPP_FILE = "TSCS_spine.supplementary.csv"
SIC_FILE = "TSCS_spine.SIC_codes.csv"

RELEASE_FILES = [SPINE_FILE, MATCHES_FILE, SUPP_FILE, SIC_FILE]

# Longest prefixes first so that GB-COH-NI wins over GB-COH-.
UID_PREFIXES = [
    "GB-NIC-",
    "GB-COH-NI",
    "GB-COH-",
    "GB-MPR-",
    "GB-SC-",
    "GB-CHC-",
    "GB-SHR-",
    "GB-SHPE-",
    "GB-COOP-",
]

SPINE_COMPARE_FIELDS = [
    "organisationname",
    "normalisedname",
    "postcode",
    "registerdate",
    "removeddate",
    "is_cic",
    "cso_type",
    "cso_subtype",
]

SUPP_COMPARE_FIELDS = [
    "organisationname",
    "normalisedname",
    "fulladdress",
    "city",
    "postcode",
    "registerdate",
    "removeddate",
    "source_register",
    "id_in_source",
]

MATCH_COLS = [
    "uid",
    "orgA_id_in_source",
    "orgA_source",
    "orgA_uid",
    "orgB_id_in_source",
    "orgB_source",
    "orgB_uid",
    "match_type",
]

NEW_MATCH_TYPES = ["name - ni charity", "merge via bridge"]

BRIDGE_TYPE = "merge via bridge"

SAMPLE_ROWS = 30


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def read_release_csv(directory, filename, usecols=None):
    """Read one release CSV as plain strings (blank stays blank, never NaN)."""
    path = os.path.join(directory, filename)
    if not os.path.isfile(path):
        raise SystemExit("Missing release file: %s" % path)
    frame = pd.read_csv(
        path,
        dtype=str,
        keep_default_na=False,
        na_values=[],
        usecols=usecols,
        low_memory=False,
    )
    frame.columns = [str(c) for c in frame.columns]
    return frame


def load_release(directory):
    """Load the four release files of one release directory."""
    return {
        "spine": read_release_csv(directory, SPINE_FILE),
        "matches": read_release_csv(directory, MATCHES_FILE),
        "supplementary": read_release_csv(directory, SUPP_FILE),
        "sic": read_release_csv(directory, SIC_FILE),
    }


def uid_prefix(uid):
    """Map a uid onto its register prefix, e.g. GB-NIC-123456 -> GB-NIC-."""
    text = "" if uid is None else str(uid)
    for prefix in UID_PREFIXES:
        if text.startswith(prefix):
            return prefix
    return "other"


def norm_postcode(value):
    """Postcode comparison key: upper case, whitespace stripped out."""
    return "".join(str(value).split()).upper()


def fmt_int(value):
    return "{:,}".format(int(value))


def fmt_delta(value):
    value = int(value)
    return ("+" if value > 0 else "") + "{:,}".format(value)


def counter_table(counter, key_header, prior=None, new=None):
    """Render a Counter (or two) as a markdown table, sorted for determinism."""
    if prior is not None and new is not None:
        keys = sorted(set(prior) | set(new))
        lines = ["| %s | prior | new | delta |" % key_header, "| --- | ---: | ---: | ---: |"]
        for key in keys:
            p = int(prior.get(key, 0))
            n = int(new.get(key, 0))
            lines.append("| %s | %s | %s | %s |" % (key, fmt_int(p), fmt_int(n), fmt_delta(n - p)))
        return "\n".join(lines)
    keys = sorted(counter)
    lines = ["| %s | n |" % key_header, "| --- | ---: |"]
    for key in keys:
        lines.append("| %s | %s |" % (key, fmt_int(counter[key])))
    if not keys:
        lines.append("| (none) | 0 |")
    return "\n".join(lines)


def frame_table(frame, max_rows=SAMPLE_ROWS):
    """Render a small dataframe as a markdown table."""
    if len(frame) == 0:
        return "_(none)_"
    shown = frame.head(max_rows)
    header = "| " + " | ".join(str(c) for c in shown.columns) + " |"
    rule = "| " + " | ".join("---" for _ in shown.columns) + " |"
    lines = [header, rule]
    for _, row in shown.iterrows():
        cells = [str(row[c]).replace("|", "/") for c in shown.columns]
        lines.append("| " + " | ".join(cells) + " |")
    if len(frame) > max_rows:
        lines.append("")
        lines.append("_... %s of %s rows shown._" % (fmt_int(max_rows), fmt_int(len(frame))))
    return "\n".join(lines)


def write_csv(frame, out_dir, name, sort_cols=None):
    """Write a CSV deterministically (sorted, stable) and return its row count."""
    if sort_cols:
        present = [c for c in sort_cols if c in frame.columns]
        if present:
            frame = frame.sort_values(present, kind="mergesort")
    frame = frame.reset_index(drop=True)
    frame.to_csv(os.path.join(out_dir, name), index=False, encoding="utf-8")
    return len(frame)


def row_key_counts(frame, cols):
    """Multiset of whole rows, so duplicated rows are compared honestly."""
    if len(frame) == 0:
        return Counter()
    keys = frame[cols].agg("\x1f".join, axis=1)
    return Counter(keys.tolist())


def counts_to_frame(counter, cols):
    """Turn a row-key multiset back into a dataframe."""
    records = []
    for key in sorted(counter):
        n = counter[key]
        parts = key.split("\x1f")
        for _ in range(n):
            records.append(parts)
    if not records:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(records, columns=cols)


# ---------------------------------------------------------------------------
# Section 1 - headline counts
# ---------------------------------------------------------------------------


def section_headline_counts(prior, new):
    """Row counts of all four files, plus the active/removed split of the spine."""
    lines = ["## 1. Headline counts", ""]
    lines.append("| file | prior rows | new rows | delta |")
    lines.append("| --- | ---: | ---: | ---: |")
    labels = [
        ("spine", SPINE_FILE),
        ("matches", MATCHES_FILE),
        ("supplementary", SUPP_FILE),
        ("sic", SIC_FILE),
    ]
    for key, filename in labels:
        p = len(prior[key])
        n = len(new[key])
        lines.append("| %s | %s | %s | %s |" % (filename, fmt_int(p), fmt_int(n), fmt_delta(n - p)))

    lines.append("")
    lines.append("### Spine active / removed split")
    lines.append("")
    lines.append("| status | prior | new | delta |")
    lines.append("| --- | ---: | ---: | ---: |")
    stats = {}
    for tag, rel in (("prior", prior), ("new", new)):
        removed = (rel["spine"]["removeddate"].str.strip() != "").sum()
        stats[tag] = {"active": len(rel["spine"]) - removed, "removed": removed}
    for status in ("active", "removed"):
        p = stats["prior"][status]
        n = stats["new"][status]
        lines.append("| %s | %s | %s | %s |" % (status, fmt_int(p), fmt_int(n), fmt_delta(n - p)))

    lines.append("")
    lines.append("### Distinct uids")
    lines.append("")
    lines.append("| set | prior | new | delta |")
    lines.append("| --- | ---: | ---: | ---: |")
    for label, key, col in [
        ("spine uids", "spine", "uid"),
        ("supplementary uids", "supplementary", "uid"),
        ("SIC uids", "sic", "uid"),
    ]:
        p = prior[key][col].nunique()
        n = new[key][col].nunique()
        lines.append("| %s | %s | %s | %s |" % (label, fmt_int(p), fmt_int(n), fmt_delta(n - p)))

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Section 2 - spine uids removed, and where they went
# ---------------------------------------------------------------------------


def section_spine_uids_removed(prior, new, out_dir):
    """Spine uids that left, and the match row that explains each departure."""
    prior_spine = prior["spine"]
    new_uids = set(new["spine"]["uid"])
    gone = prior_spine[~prior_spine["uid"].isin(new_uids)].copy()

    new_matches = new["matches"]
    filled = new_matches[new_matches["uid"].str.strip() != ""]
    blank = new_matches[new_matches["uid"].str.strip() == ""]

    # Absorbing rows: the departed uid now sits in the orgB slot of a live cluster.
    absorb = filled[filled["orgB_uid"].isin(set(gone["uid"]))]
    absorb_group = (
        absorb.groupby("orgB_uid")
        .agg(
            absorbed_into=("uid", lambda s: "; ".join(sorted(set(s)))),
            absorbing_match_types=("match_type", lambda s: "; ".join(sorted(set(s)))),
            n_absorbing_rows=("uid", "size"),
        )
        .reset_index()
        .rename(columns={"orgB_uid": "uid"})
    )

    blank_only = set(blank["orgB_uid"]) | set(blank["orgA_uid"])
    elsewhere = set(filled["orgA_uid"]) | set(filled["uid"])

    gone = gone.merge(absorb_group, on="uid", how="left")
    for col in ("absorbed_into", "absorbing_match_types"):
        gone[col] = gone[col].fillna("")
    gone["n_absorbing_rows"] = gone["n_absorbing_rows"].fillna(0).astype(int)

    def classify(row):
        if row["n_absorbing_rows"] > 0:
            return "absorbed"
        if row["uid"] in blank_only:
            return "association only (blank-uid rows)"
        if row["uid"] in elsewhere:
            return "present in new matches, not as orgB"
        return "LOST"

    gone["status"] = gone.apply(classify, axis=1)
    gone["uid_prefix"] = gone["uid"].map(uid_prefix)
    gone["explanation"] = gone.apply(
        lambda r: (
            "absorbed into %s via %s" % (r["absorbed_into"], r["absorbing_match_types"])
            if r["status"] == "absorbed"
            else r["status"]
        ),
        axis=1,
    )

    out = gone[
        [
            "uid",
            "uid_prefix",
            "organisationname",
            "normalisedname",
            "postcode",
            "source_register",
            "registerdate",
            "removeddate",
            "cso_type",
            "status",
            "absorbed_into",
            "absorbing_match_types",
            "n_absorbing_rows",
            "explanation",
        ]
    ].copy()
    n_rows = write_csv(out, out_dir, "spine-uids-removed.csv", sort_cols=["uid_prefix", "uid"])

    lost = out[out["status"] == "LOST"]

    lines = ["## 2. Spine uids removed (present in prior, absent in new)", ""]
    lines.append("Removed spine uids: **%s** (CSV: spine-uids-removed.csv, %s rows)" % (fmt_int(len(out)), fmt_int(n_rows)))
    lines.append("")
    lines.append("### Where they went")
    lines.append("")
    lines.append(counter_table(Counter(out["status"]), "status"))
    lines.append("")
    if len(lost) == 0:
        lines.append("**No LOST uids** - every departed uid is explained by the new match file.")
    else:
        lines.append("**WARNING: %s LOST uid(s)** - not explained by any new match row." % fmt_int(len(lost)))
        lines.append("")
        lines.append(frame_table(lost[["uid", "organisationname", "source_register", "removeddate"]]))
    lines.append("")
    lines.append("### By uid prefix")
    lines.append("")
    lines.append(counter_table(Counter(out["uid_prefix"]), "uid prefix"))
    lines.append("")
    lines.append("### By uid prefix x status")
    lines.append("")
    cross = Counter(zip(out["uid_prefix"], out["status"]))
    lines.append(
        counter_table(Counter({"%s / %s" % (a, b): n for (a, b), n in cross.items()}), "uid prefix / status")
    )
    lines.append("")
    lines.append("### By absorbing match_type (one count per absorbing match row)")
    lines.append("")
    lines.append(counter_table(Counter(absorb["match_type"]), "match_type"))
    lines.append("")
    lines.append("### Absorbing uid prefix (who absorbed them)")
    lines.append("")
    absorbed = out[out["status"] == "absorbed"]
    lines.append(counter_table(Counter(absorbed["absorbed_into"].map(uid_prefix)), "absorbing uid prefix"))
    lines.append("")
    return "\n".join(lines), out


# ---------------------------------------------------------------------------
# Section 3 - spine uids added
# ---------------------------------------------------------------------------


def section_spine_uids_added(prior, new, out_dir):
    """Spine uids that appeared: for a like-for-like rebuild this should be zero."""
    prior_uids = set(prior["spine"]["uid"])
    new_spine = new["spine"]
    added = new_spine[~new_spine["uid"].isin(prior_uids)].copy()
    added["uid_prefix"] = added["uid"].map(uid_prefix)

    prior_supp_uids = set(prior["supplementary"]["uid"])
    prior_match_uids = (
        set(prior["matches"]["uid"]) | set(prior["matches"]["orgA_uid"]) | set(prior["matches"]["orgB_uid"])
    )
    added["seen_in_prior_supplementary"] = added["uid"].isin(prior_supp_uids)
    added["seen_in_prior_matches"] = added["uid"].isin(prior_match_uids)

    out = added[
        [
            "uid",
            "uid_prefix",
            "organisationname",
            "normalisedname",
            "postcode",
            "source_register",
            "registerdate",
            "removeddate",
            "cso_type",
            "seen_in_prior_supplementary",
            "seen_in_prior_matches",
        ]
    ].copy()
    write_csv(out, out_dir, "spine-uids-added.csv", sort_cols=["uid_prefix", "uid"])

    lines = ["## 3. Spine uids added (absent in prior, present in new)", ""]
    lines.append("Added spine uids: **%s** (CSV: spine-uids-added.csv)" % fmt_int(len(out)))
    lines.append("")
    if len(out):
        lines.append(counter_table(Counter(out["uid_prefix"]), "uid prefix"))
        lines.append("")
        lines.append("Of these, %s were already known to the prior supplementary file and %s to the prior match file." % (
            fmt_int(int(out["seen_in_prior_supplementary"].sum())),
            fmt_int(int(out["seen_in_prior_matches"].sum())),
        ))
        lines.append("")
        lines.append(frame_table(out[["uid", "organisationname", "source_register", "registerdate", "removeddate"]]))
    else:
        lines.append("None - the new release introduces no spine uid that the prior release did not have.")
    lines.append("")
    return "\n".join(lines), out


# ---------------------------------------------------------------------------
# Section 4 - match rows added / removed, and bridge merges
# ---------------------------------------------------------------------------


def _bridge_merges(prior, new, added_frame, out_dir):
    """Detail every 'merge via bridge' row and the bridge evidence behind it."""
    new_matches = new["matches"]
    bridges = new_matches[new_matches["match_type"] == BRIDGE_TYPE].copy()
    if len(bridges) == 0:
        write_csv(
            pd.DataFrame(
                columns=[
                    "survivor_uid",
                    "survivor_name",
                    "survivor_source",
                    "survivor_normalisedname",
                    "loser_uid",
                    "loser_name",
                    "loser_source",
                    "loser_normalisedname",
                    "normalisedname_differs",
                    "bridge_orgB_uids",
                    "bridge_match_types",
                    "n_bridge_records",
                ]
            ),
            out_dir,
            "bridge-merges.csv",
        )
        return "No `merge via bridge` rows in the new release.", pd.DataFrame()

    prior_spine = prior["spine"].set_index("uid")
    new_spine = new["spine"].set_index("uid")

    def look_up(uid, field):
        if uid in prior_spine.index:
            return str(prior_spine.at[uid, field])
        if uid in new_spine.index:
            return str(new_spine.at[uid, field])
        return ""

    # Match rows that are new versus the prior release, keyed by survivor uid.
    added_keys = set(
        added_frame[MATCH_COLS].agg("\x1f".join, axis=1).tolist() if len(added_frame) else []
    )
    new_matches = new_matches.copy()
    new_matches["_key"] = new_matches[MATCH_COLS].agg("\x1f".join, axis=1)
    new_matches["_is_added"] = new_matches["_key"].isin(added_keys)

    records = []
    for _, row in bridges.iterrows():
        survivor = row["uid"] if row["uid"].strip() else row["orgA_uid"]
        loser = row["orgB_uid"]
        siblings = new_matches[
            (new_matches["uid"] == survivor)
            & (new_matches["orgB_uid"] != loser)
            & (new_matches["_is_added"])
        ]
        s_norm = look_up(survivor, "normalisedname")
        l_norm = look_up(loser, "normalisedname")
        records.append(
            {
                "survivor_uid": survivor,
                "survivor_name": look_up(survivor, "organisationname"),
                "survivor_source": look_up(survivor, "source_register"),
                "survivor_normalisedname": s_norm,
                "loser_uid": loser,
                "loser_name": look_up(loser, "organisationname"),
                "loser_source": look_up(loser, "source_register"),
                "loser_normalisedname": l_norm,
                "normalisedname_differs": s_norm != l_norm,
                "bridge_orgB_uids": "; ".join(sorted(set(siblings["orgB_uid"]))),
                "bridge_match_types": "; ".join(sorted(set(siblings["match_type"]))),
                "n_bridge_records": len(siblings),
            }
        )

    out = pd.DataFrame(records)
    write_csv(out, out_dir, "bridge-merges.csv", sort_cols=["survivor_uid", "loser_uid"])

    differ = out[out["normalisedname_differs"]]
    text = [
        "`merge via bridge` rows: **%s** (CSV: bridge-merges.csv)" % fmt_int(len(out)),
        "",
        "Bridge merges where survivor and loser normalisednames differ: **%s**" % fmt_int(len(differ)),
        "",
        frame_table(
            out[["survivor_uid", "survivor_name", "loser_uid", "loser_name", "bridge_match_types", "n_bridge_records"]]
        ),
    ]
    if len(differ):
        text.append("")
        text.append("Name-mismatch bridge merges:")
        text.append("")
        text.append(frame_table(differ[["survivor_uid", "survivor_normalisedname", "loser_uid", "loser_normalisedname"]]))
    return "\n".join(text), out


def section_match_rows(prior, new, out_dir):
    """Whole-row added/removed match rows, split by match_type and uid prefix."""
    prior_counts = row_key_counts(prior["matches"], MATCH_COLS)
    new_counts = row_key_counts(new["matches"], MATCH_COLS)

    added_counts = Counter()
    removed_counts = Counter()
    for key, n in new_counts.items():
        diff = n - prior_counts.get(key, 0)
        if diff > 0:
            added_counts[key] = diff
    for key, n in prior_counts.items():
        diff = n - new_counts.get(key, 0)
        if diff > 0:
            removed_counts[key] = diff

    added = counts_to_frame(added_counts, MATCH_COLS)
    removed = counts_to_frame(removed_counts, MATCH_COLS)

    for frame in (added, removed):
        if len(frame):
            frame["orgA_prefix"] = frame["orgA_uid"].map(uid_prefix)
            frame["orgB_prefix"] = frame["orgB_uid"].map(uid_prefix)
        else:
            frame["orgA_prefix"] = []
            frame["orgB_prefix"] = []

    write_csv(added, out_dir, "match-rows-added.csv", sort_cols=["match_type", "uid", "orgB_uid"])
    write_csv(removed, out_dir, "match-rows-removed.csv", sort_cols=["match_type", "uid", "orgB_uid"])

    lines = ["## 4. Match rows", ""]
    lines.append(
        "Match rows added: **%s**; removed: **%s** (CSVs: match-rows-added.csv, match-rows-removed.csv)"
        % (fmt_int(len(added)), fmt_int(len(removed)))
    )
    lines.append("")
    lines.append("### match_type totals")
    lines.append("")
    lines.append(
        counter_table(None, "match_type", Counter(prior["matches"]["match_type"]), Counter(new["matches"]["match_type"]))
    )
    lines.append("")
    lines.append("### Added rows by match_type")
    lines.append("")
    lines.append(counter_table(Counter(added["match_type"]) if len(added) else Counter(), "match_type"))
    lines.append("")
    lines.append("### Removed rows by match_type")
    lines.append("")
    lines.append(counter_table(Counter(removed["match_type"]) if len(removed) else Counter(), "match_type"))
    lines.append("")

    lines.append("### New match types introduced by this release")
    lines.append("")
    prior_types = set(prior["matches"]["match_type"])
    lines.append("| match_type | rows in new | present in prior? |")
    lines.append("| --- | ---: | --- |")
    new_type_counts = Counter(new["matches"]["match_type"])
    for mtype in NEW_MATCH_TYPES:
        lines.append(
            "| %s | %s | %s |" % (mtype, fmt_int(new_type_counts.get(mtype, 0)), "yes" if mtype in prior_types else "no")
        )
    lines.append("")

    lines.append("### Pre-existing match types: rows added / removed")
    lines.append("")
    lines.append("Rows carrying a match_type that already existed in the prior release, but whose row content is new.")
    lines.append("")
    pre_added = added[~added["match_type"].isin(NEW_MATCH_TYPES)] if len(added) else added
    pre_removed = removed[~removed["match_type"].isin(NEW_MATCH_TYPES)] if len(removed) else removed
    lines.append(
        "Pre-existing-type rows added: **%s**; removed: **%s**" % (fmt_int(len(pre_added)), fmt_int(len(pre_removed)))
    )
    lines.append("")
    if len(pre_added):
        cross = Counter(
            "%s | orgA %s -> orgB %s" % (t, a, b)
            for t, a, b in zip(pre_added["match_type"], pre_added["orgA_prefix"], pre_added["orgB_prefix"])
        )
        lines.append("Added, by match_type and uid prefix pair:")
        lines.append("")
        lines.append(counter_table(cross, "match_type / prefixes"))
        lines.append("")
    if len(pre_removed):
        cross = Counter(
            "%s | orgA %s -> orgB %s" % (t, a, b)
            for t, a, b in zip(pre_removed["match_type"], pre_removed["orgA_prefix"], pre_removed["orgB_prefix"])
        )
        lines.append("Removed, by match_type and uid prefix pair:")
        lines.append("")
        lines.append(counter_table(cross, "match_type / prefixes"))
        lines.append("")

    lines.append("### Bridge merges")
    lines.append("")
    bridge_text, _ = _bridge_merges(prior, new, added, out_dir)
    lines.append(bridge_text)
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Section 5 - field level changes for surviving spine uids
# ---------------------------------------------------------------------------


def classify_removeddate(prior_value, new_value):
    """Label a removeddate change in plain terms."""
    had = str(prior_value).strip() != ""
    has = str(new_value).strip() != ""
    if had and not has:
        return "revived"
    if not had and has:
        return "newly removed"
    return "date changed"


def section_field_changes(prior, new, out_dir):
    """Field-by-field changes for the uids present in both releases."""
    cols = ["uid"] + SPINE_COMPARE_FIELDS
    left = prior["spine"][cols].drop_duplicates(subset=["uid"], keep="first")
    right = new["spine"][cols].drop_duplicates(subset=["uid"], keep="first")
    merged = left.merge(right, on="uid", how="inner", suffixes=("_prior", "_new"))

    records = []
    per_field = Counter()
    for field in SPINE_COMPARE_FIELDS:
        mask = merged[field + "_prior"] != merged[field + "_new"]
        per_field[field] = int(mask.sum())
        if not mask.any():
            continue
        block = merged.loc[mask, ["uid", field + "_prior", field + "_new"]].copy()
        block.columns = ["uid", "prior_value", "new_value"]
        block["field"] = field
        if field == "removeddate":
            block["removeddate_change_class"] = [
                classify_removeddate(p, n) for p, n in zip(block["prior_value"], block["new_value"])
            ]
        else:
            block["removeddate_change_class"] = ""
        records.append(block)

    if records:
        changed = pd.concat(records, ignore_index=True)
    else:
        changed = pd.DataFrame(columns=["uid", "prior_value", "new_value", "field", "removeddate_change_class"])
    changed["uid_prefix"] = changed["uid"].map(uid_prefix) if len(changed) else []
    changed = changed[["uid", "uid_prefix", "field", "prior_value", "new_value", "removeddate_change_class"]]
    write_csv(changed, out_dir, "spine-field-changes.csv", sort_cols=["field", "uid"])

    lines = ["## 5. Field changes for surviving spine uids", ""]
    lines.append("Spine uids present in both releases: **%s**" % fmt_int(len(merged)))
    lines.append("")
    lines.append("Uids with at least one changed field: **%s**" % fmt_int(changed["uid"].nunique() if len(changed) else 0))
    lines.append("")
    lines.append("CSV: spine-field-changes.csv (one row per uid x field that changed)")
    lines.append("")
    lines.append(counter_table(per_field, "field"))
    lines.append("")
    rd = changed[changed["field"] == "removeddate"]
    lines.append("### removeddate changes classified")
    lines.append("")
    lines.append(counter_table(Counter(rd["removeddate_change_class"]) if len(rd) else Counter(), "class"))
    lines.append("")
    if len(changed):
        lines.append("### Sample of changed rows")
        lines.append("")
        sample = changed.sort_values(["field", "uid"], kind="mergesort")
        lines.append(frame_table(sample))
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Section 6 - supplementary
# ---------------------------------------------------------------------------


def section_supplementary(prior, new, out_dir):
    """Supplementary rows added/removed by source register, and unsettled uids."""
    cols = ["uid"] + SUPP_COMPARE_FIELDS
    prior_supp = prior["supplementary"][cols]
    new_supp = new["supplementary"][cols]

    prior_counts = row_key_counts(prior_supp, cols)
    new_counts = row_key_counts(new_supp, cols)

    added_counts = Counter()
    removed_counts = Counter()
    for key, n in new_counts.items():
        diff = n - prior_counts.get(key, 0)
        if diff > 0:
            added_counts[key] = diff
    for key, n in prior_counts.items():
        diff = n - new_counts.get(key, 0)
        if diff > 0:
            removed_counts[key] = diff

    added = counts_to_frame(added_counts, cols)
    removed = counts_to_frame(removed_counts, cols)
    write_csv(added, out_dir, "supplementary-rows-added.csv", sort_cols=["source_register", "uid"])
    write_csv(removed, out_dir, "supplementary-rows-removed.csv", sort_cols=["source_register", "uid"])

    touched = sorted(set(added["uid"]) | set(removed["uid"]))
    changed_uids = pd.DataFrame({"uid": touched})
    if len(changed_uids):
        changed_uids["uid_prefix"] = changed_uids["uid"].map(uid_prefix)
        changed_uids["rows_added"] = changed_uids["uid"].map(Counter(added["uid"])).fillna(0).astype(int)
        changed_uids["rows_removed"] = changed_uids["uid"].map(Counter(removed["uid"])).fillna(0).astype(int)
    else:
        for col in ("uid_prefix", "rows_added", "rows_removed"):
            changed_uids[col] = []
    write_csv(changed_uids, out_dir, "supplementary-uids-changed.csv", sort_cols=["uid"])

    lines = ["## 6. Supplementary file", ""]
    lines.append(
        "Supplementary rows added: **%s**; removed: **%s**" % (fmt_int(len(added)), fmt_int(len(removed)))
    )
    lines.append("")
    lines.append("Uids whose supplementary rows changed in any way: **%s** (CSV: supplementary-uids-changed.csv)" % fmt_int(len(changed_uids)))
    lines.append("")
    lines.append("CSVs: supplementary-rows-added.csv, supplementary-rows-removed.csv")
    lines.append("")
    lines.append("### Added rows by source_register")
    lines.append("")
    lines.append(counter_table(Counter(added["source_register"]) if len(added) else Counter(), "source_register"))
    lines.append("")
    lines.append("### Removed rows by source_register")
    lines.append("")
    lines.append(counter_table(Counter(removed["source_register"]) if len(removed) else Counter(), "source_register"))
    lines.append("")
    lines.append("### Changed uids by prefix")
    lines.append("")
    lines.append(counter_table(Counter(changed_uids["uid_prefix"]) if len(changed_uids) else Counter(), "uid prefix"))
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Section 7 - SIC codes
# ---------------------------------------------------------------------------


def section_sic(prior, new, out_dir):
    """SIC file row delta and the uids that gained or lost SIC coverage."""
    prior_sic = prior["sic"]
    new_sic = new["sic"]
    prior_uids = set(prior_sic["uid"])
    new_uids = set(new_sic["uid"])

    gained = sorted(new_uids - prior_uids)
    lost = sorted(prior_uids - new_uids)

    gained_frame = pd.DataFrame({"uid": gained})
    lost_frame = pd.DataFrame({"uid": lost})
    for frame in (gained_frame, lost_frame):
        frame["uid_prefix"] = frame["uid"].map(uid_prefix) if len(frame) else []
    gained_frame["direction"] = "gained" if len(gained_frame) else []
    lost_frame["direction"] = "lost" if len(lost_frame) else []
    combined = pd.concat([gained_frame, lost_frame], ignore_index=True)
    write_csv(combined, out_dir, "sic-uids-changed.csv", sort_cols=["direction", "uid"])

    lines = ["## 7. SIC codes file", ""]
    lines.append(
        "| measure | prior | new | delta |\n| --- | ---: | ---: | ---: |\n| rows | %s | %s | %s |\n| distinct uids | %s | %s | %s |"
        % (
            fmt_int(len(prior_sic)),
            fmt_int(len(new_sic)),
            fmt_delta(len(new_sic) - len(prior_sic)),
            fmt_int(len(prior_uids)),
            fmt_int(len(new_uids)),
            fmt_delta(len(new_uids) - len(prior_uids)),
        )
    )
    lines.append("")
    lines.append("Uids gained: **%s**; uids lost: **%s** (CSV: sic-uids-changed.csv)" % (fmt_int(len(gained)), fmt_int(len(lost))))
    lines.append("")
    if len(combined):
        cross = Counter(
            "%s / %s" % (d, p) for d, p in zip(combined["direction"], combined["uid_prefix"])
        )
        lines.append(counter_table(cross, "direction / uid prefix"))
        lines.append("")
        lines.append(frame_table(combined))
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Section 8 - Northern Ireland
# ---------------------------------------------------------------------------


def section_northern_ireland(prior, new, out_dir):
    """NI-specific adjudication: which NI charities absorbed which NI companies."""
    new_matches = new["matches"]
    ni = new_matches[
        new_matches["uid"].str.startswith("GB-NIC-") & new_matches["orgB_uid"].str.startswith("GB-COH-NI")
    ].copy()

    pairs = (
        ni.groupby(["uid", "orgB_uid"])["match_type"]
        .apply(lambda s: "; ".join(sorted(set(s))))
        .reset_index()
        .rename(columns={"uid": "charity_uid", "orgB_uid": "company_uid", "match_type": "match_types"})
    )

    def evidence(types):
        parts = set(t.strip() for t in types.split(";"))
        has_id = "companyid - id_in_source" in parts
        has_name = "name - ni charity" in parts
        if has_id and has_name:
            return "both"
        if has_id:
            return "companyid only"
        if has_name:
            return "name only"
        return "other (%s)" % types

    pairs["evidence"] = pairs["match_types"].map(evidence) if len(pairs) else []

    prior_spine = prior["spine"].drop_duplicates(subset=["uid"], keep="first").set_index("uid")
    new_spine = new["spine"].drop_duplicates(subset=["uid"], keep="first").set_index("uid")

    def from_spine(frame, uid, field):
        if uid in frame.index:
            return str(frame.at[uid, field])
        return ""

    if len(pairs):
        pairs["charity_name"] = [from_spine(new_spine, u, "organisationname") for u in pairs["charity_uid"]]
        pairs["charity_postcode"] = [from_spine(new_spine, u, "postcode") for u in pairs["charity_uid"]]
        pairs["charity_normalisedname"] = [from_spine(new_spine, u, "normalisedname") for u in pairs["charity_uid"]]
        pairs["company_name"] = [from_spine(prior_spine, u, "organisationname") for u in pairs["company_uid"]]
        pairs["company_postcode"] = [from_spine(prior_spine, u, "postcode") for u in pairs["company_uid"]]
        pairs["company_normalisedname"] = [from_spine(prior_spine, u, "normalisedname") for u in pairs["company_uid"]]
        pairs["postcode_agrees"] = [
            norm_postcode(c) == norm_postcode(k) if norm_postcode(c) and norm_postcode(k) else None
            for c, k in zip(pairs["charity_postcode"], pairs["company_postcode"])
        ]
        pairs["name_agrees"] = pairs["charity_normalisedname"] == pairs["company_normalisedname"]
    else:
        for col in (
            "charity_name",
            "charity_postcode",
            "charity_normalisedname",
            "company_name",
            "company_postcode",
            "company_normalisedname",
            "postcode_agrees",
            "name_agrees",
        ):
            pairs[col] = []

    write_csv(pairs, out_dir, "ni-charity-company-absorptions.csv", sort_cols=["charity_uid", "company_uid"])

    # Charities absorbing two or more companies.
    multi = (
        pairs.groupby("charity_uid")
        .agg(
            n_companies=("company_uid", "nunique"),
            companies=("company_uid", lambda s: "; ".join(sorted(set(s)))),
            evidence_set=("evidence", lambda s: "; ".join(sorted(set(s)))),
        )
        .reset_index()
    )
    multi = multi[multi["n_companies"] >= 2].copy()
    if len(multi):
        multi["charity_name"] = [from_spine(new_spine, u, "organisationname") for u in multi["charity_uid"]]
    else:
        multi["charity_name"] = []
    write_csv(multi, out_dir, "ni-charities-multi-company.csv", sort_cols=["charity_uid"])

    # NI charities that were removed in the prior spine but are active in the new one.
    prior_nic = prior["spine"][prior["spine"]["uid"].str.startswith("GB-NIC-")]
    new_nic = new["spine"][new["spine"]["uid"].str.startswith("GB-NIC-")]
    prior_removed = set(prior_nic.loc[prior_nic["removeddate"].str.strip() != "", "uid"])
    new_active = set(new_nic.loc[new_nic["removeddate"].str.strip() == "", "uid"])
    revived_uids = sorted(prior_removed & new_active)
    revived = pd.DataFrame({"uid": revived_uids})
    if len(revived):
        revived["organisationname"] = [from_spine(new_spine, u, "organisationname") for u in revived["uid"]]
        revived["prior_removeddate"] = [from_spine(prior_spine, u, "removeddate") for u in revived["uid"]]
        revived["new_registerdate"] = [from_spine(new_spine, u, "registerdate") for u in revived["uid"]]
        pair_map = pairs.groupby("charity_uid")["company_uid"].apply(lambda s: "; ".join(sorted(set(s))))
        revived["absorbed_companies"] = revived["uid"].map(pair_map).fillna("")
    else:
        for col in ("organisationname", "prior_removeddate", "new_registerdate", "absorbed_companies"):
            revived[col] = []
    write_csv(revived, out_dir, "ni-charities-revived.csv", sort_cols=["uid"])

    lines = ["## 8. Northern Ireland", ""]
    lines.append(
        "GB-NIC charities absorbing at least one GB-COH-NI company in the new match file: **%s** (pairs: %s)"
        % (fmt_int(pairs["charity_uid"].nunique() if len(pairs) else 0), fmt_int(len(pairs)))
    )
    lines.append("")
    lines.append("CSV: ni-charity-company-absorptions.csv")
    lines.append("")
    lines.append("### Evidence combination (charity-company pairs)")
    lines.append("")
    lines.append(counter_table(Counter(pairs["evidence"]) if len(pairs) else Counter(), "evidence"))
    lines.append("")
    lines.append("### Evidence combination (distinct charities, strongest evidence held)")
    lines.append("")
    if len(pairs):
        rank = {"both": 3, "companyid only": 2, "name only": 1}
        best = pairs.assign(_r=pairs["evidence"].map(lambda e: rank.get(e, 0))).sort_values(
            ["_r", "charity_uid", "company_uid"], ascending=[False, True, True], kind="mergesort"
        )
        best = best.drop_duplicates(subset=["charity_uid"], keep="first")
        lines.append(counter_table(Counter(best["evidence"]), "evidence"))
    else:
        lines.append(counter_table(Counter(), "evidence"))
    lines.append("")
    lines.append("### Charities absorbing 2+ companies")
    lines.append("")
    lines.append("Count: **%s** (CSV: ni-charities-multi-company.csv)" % fmt_int(len(multi)))
    lines.append("")
    if len(multi):
        lines.append(frame_table(multi[["charity_uid", "charity_name", "n_companies", "companies", "evidence_set"]]))
        lines.append("")
    lines.append("### Postcode agreement, charity vs absorbed company")
    lines.append("")
    if len(pairs):
        comparable = pairs[pairs["postcode_agrees"].notna()]
        agree = int(comparable["postcode_agrees"].sum()) if len(comparable) else 0
        total = len(comparable)
        rate = (100.0 * agree / total) if total else 0.0
        lines.append("| measure | n |")
        lines.append("| --- | ---: |")
        lines.append("| pairs | %s |" % fmt_int(len(pairs)))
        lines.append("| pairs with both postcodes present | %s |" % fmt_int(total))
        lines.append("| postcodes agree | %s |" % fmt_int(agree))
        lines.append("| postcodes disagree | %s |" % fmt_int(total - agree))
        lines.append("| agreement rate | %.1f%% |" % rate)
        lines.append("")
        lines.append("Agreement rate by evidence combination:")
        lines.append("")
        lines.append("| evidence | comparable pairs | agree | rate |")
        lines.append("| --- | ---: | ---: | ---: |")
        for ev in sorted(set(comparable["evidence"])) if len(comparable) else []:
            sub = comparable[comparable["evidence"] == ev]
            a = int(sub["postcode_agrees"].sum())
            lines.append("| %s | %s | %s | %.1f%% |" % (ev, fmt_int(len(sub)), fmt_int(a), 100.0 * a / len(sub)))
        lines.append("")
    else:
        lines.append("_(no pairs)_")
        lines.append("")
    lines.append("### GB-NIC charities removed in prior spine but active in new")
    lines.append("")
    lines.append("Count: **%s** (CSV: ni-charities-revived.csv)" % fmt_int(len(revived)))
    lines.append("")
    if len(revived):
        lines.append(frame_table(revived))
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def build_report(prior_dir, new_dir, out_dir):
    """Run every section and write delta-report.md plus its supporting CSVs."""
    os.makedirs(out_dir, exist_ok=True)

    print("Loading prior release: %s" % prior_dir)
    prior = load_release(prior_dir)
    print("Loading new release:   %s" % new_dir)
    new = load_release(new_dir)

    parts = ["# Spine release delta report", ""]
    parts.append("| | |")
    parts.append("| --- | --- |")
    parts.append("| prior release | `%s` |" % prior_dir)
    parts.append("| new release | `%s` |" % new_dir)
    parts.append("| output | `%s` |" % out_dir)
    parts.append("")

    print("Section 1: headline counts")
    parts.append(section_headline_counts(prior, new))
    print("Section 2: spine uids removed")
    text, _ = section_spine_uids_removed(prior, new, out_dir)
    parts.append(text)
    print("Section 3: spine uids added")
    text, _ = section_spine_uids_added(prior, new, out_dir)
    parts.append(text)
    print("Section 4: match rows")
    parts.append(section_match_rows(prior, new, out_dir))
    print("Section 5: field changes")
    parts.append(section_field_changes(prior, new, out_dir))
    print("Section 6: supplementary")
    parts.append(section_supplementary(prior, new, out_dir))
    print("Section 7: SIC codes")
    parts.append(section_sic(prior, new, out_dir))
    print("Section 8: Northern Ireland")
    parts.append(section_northern_ireland(prior, new, out_dir))

    report = "\n".join(parts).rstrip() + "\n"
    report_path = os.path.join(out_dir, "delta-report.md")
    with open(report_path, "w", encoding="utf-8", newline="\r\n") as handle:
        handle.write(report)
    print("Wrote %s (%s lines)" % (report_path, fmt_int(report.count("\n"))))
    return report_path


def main(argv):
    if len(argv) != 4:
        print(__doc__)
        return 2
    prior_dir, new_dir, out_dir = argv[1], argv[2], argv[3]
    build_report(prior_dir, new_dir, out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
