'''Seed a freshly built supplementary file with a published release's rows.

A from-raw rebuild can only emit the historical name/address variants that
exist in its (partly bootstrapped) inputs, so it loses variant rows that
earlier pipeline runs accumulated from register snapshots which can no
longer be re-downloaded. The July 2026 trial rebuild produced 697,656
supplementary rows against published v1.0's 872,084 for this reason.

This step closes that gap: it unions the prior release's supplementary rows
into the freshly built file, keeping only rows whose organisation is still
represented in the freshly built release and skipping rows the rebuild
already has. "Represented" means the uid appears in the built spine OR in
any uid column of the built matches file: by convention an absorbed
organisation's supplementary rows keep the absorbed organisation's own uid,
with the matches file linking it to the surviving spine organisation (the
rebuilt supplementary itself contains ~124k such rows).
Seeded rows are placed directly after the organisation's existing block so
each uid's rows stay contiguous; organisations with no existing block are
appended at the end in uid order. The output is deterministic and the write
is atomic (temp file, then replace, with the pre-seed file kept as backup).

Run AFTER build-spine, BEFORE packaging a release:
    python cli.py seed-supplementary TSCS_spine.supplementary.csv \
        TSCS_spine.spine.csv TSCS_spine.matches.csv \
        <prior_release>/TSCS_spine.supplementary.csv
'''

import csv
import os
import tempfile


def read_csv_rows(filename):
    '''Returns (header, rows) with rows as lists of field values.'''
    with open(filename, newline='', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = next(reader)
        return header, [row for row in reader if row]


def merge_supplementary_rows(base_header, base_rows, prior_header, prior_rows,
                             release_uids):
    '''Pure merge: returns (merged_rows, counts). Rows are lists; the uid is
    the first field. Prior rows are dropped when the organisation is absent
    from release_uids (the built spine's uids plus every uid in the built
    matches file) or when an identical row already exists (in the base file
    or already seeded).'''

    if prior_header != base_header:
        raise ValueError(
            'seed-supplementary: column mismatch between built file %s and '
            'prior release file %s - refusing to merge' % (base_header, prior_header))

    seen = {tuple(row) for row in base_rows}
    counts = {'base': len(base_rows), 'prior': len(prior_rows),
              'seeded': 0, 'duplicate': 0, 'org_not_in_release': 0}

    to_seed = {}  # uid -> rows, insertion-ordered
    for row in prior_rows:
        uid = row[0]
        if uid not in release_uids:
            counts['org_not_in_release'] += 1
            continue
        key = tuple(row)
        if key in seen:
            counts['duplicate'] += 1
            continue
        seen.add(key)
        to_seed.setdefault(uid, []).append(row)
        counts['seeded'] += 1

    last_index = {}
    for i, row in enumerate(base_rows):
        last_index[row[0]] = i

    merged = []
    for i, row in enumerate(base_rows):
        merged.append(row)
        uid = row[0]
        if last_index[uid] == i and uid in to_seed:
            merged.extend(to_seed.pop(uid))

    # organisations in the spine with prior-release history but no row in
    # the freshly built file: append their blocks in uid order
    for uid in sorted(to_seed):
        merged.extend(to_seed[uid])

    return merged, counts


def release_uid_universe(built_spine_csv, built_matches_csv):
    '''Every uid the built release knows: spine uids plus the uid, orgA_uid
    and orgB_uid columns of the matches file (absorbed organisations keep
    their own uid in the supplementary file, linked via matches).'''
    with open(built_spine_csv, newline='', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        next(reader)
        uids = {row[0] for row in reader if row}
    with open(built_matches_csv, newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            uids.update((row['uid'], row['orgA_uid'], row['orgB_uid']))
    uids.discard('')
    return uids


def seed_supplementary(built_supplementary_csv, built_spine_csv,
                       built_matches_csv, prior_supplementary_csv):
    '''Reads the four files, merges, and atomically replaces the built
    supplementary file, keeping the original as <name>.preseed.csv.'''

    release_uids = release_uid_universe(built_spine_csv, built_matches_csv)

    base_header, base_rows = read_csv_rows(built_supplementary_csv)
    prior_header, prior_rows = read_csv_rows(prior_supplementary_csv)

    merged, counts = merge_supplementary_rows(
        base_header, base_rows, prior_header, prior_rows, release_uids)

    backup = built_supplementary_csv.replace('.csv', '.preseed.csv')
    if os.path.exists(backup):
        raise RuntimeError(
            'seed-supplementary: backup %s already exists - this file appears '
            'to have been seeded already. Remove the backup to re-run.' % backup)

    out_dir = os.path.dirname(os.path.abspath(built_supplementary_csv))
    fd, tmp_path = tempfile.mkstemp(suffix='.csv', dir=out_dir)
    try:
        with os.fdopen(fd, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(base_header)
            writer.writerows(merged)
        os.replace(built_supplementary_csv, backup)
        os.replace(tmp_path, built_supplementary_csv)
    except BaseException:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise

    print('seed-supplementary: %(base)s built rows + %(seeded)s seeded from the '
          'prior release (of %(prior)s prior rows: %(duplicate)s already present, '
          '%(org_not_in_release)s organisation no longer represented in the '
          'release).' % counts)
    print('seed-supplementary: wrote %s rows to %s (pre-seed file kept as %s)'
          % (len(merged), built_supplementary_csv, backup))
    return counts
