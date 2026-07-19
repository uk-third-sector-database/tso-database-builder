'''Suppress bootstrap-echo company-number rows from a freshly built matches file.

CCEW's extracts do not publish company numbers for most charity/CIO records,
so bootstrap_base_files back-fills each charity's companyid from the published
release itself - primarily from its unique ftc-linked GB-COH partner. A
from-raw rebuild then re-fires the 'companyid - id_in_source' matching rule on
those planted numbers, re-emitting the prior release's ftc links as if they
were independent regulator-published identifier evidence (the July 2026 trial
rebuild produced 40,427 such rows). The evidence is circular: the second row
derives entirely from the first.

This step removes those rows. A built 'companyid - id_in_source' row is
suppressed when all three hold:

1. the same (pair, match type) row is NOT in the prior release's matches file
   - rows the prior release itself published are continuity, not echo;
2. the pair IS linked in the prior release's matches file by some other rule
   (in practice ftc) - the row restates a known link rather than adding one;
3. the pair keeps at least one other evidence row in the built file, so
   suppression never disconnects a pair or removes a uid from the release's
   uid universe (seed-supplementary's universe is therefore unaffected).

Known limitation: if a future extract genuinely starts publishing a company
number for a pair the prior release linked via ftc, its row is still
suppressed - the link itself is always retained via the ftc row, only the
identifier-evidence row is lost. Revisit if CCEW's extracts start carrying
CE company numbers (143 of ~40k in the July 2026 extract).

Suppressed rows are written next to the output as <name>.suppressed-echo.csv
for inspection; the untouched input is kept as <name>.preecho.csv. Run AFTER
build-spine, in either order with seed-supplementary:
    python cli.py suppress-echo-matches TSCS_spine.matches.csv \
        <prior_release>/TSCS_spine.matches.csv
'''

import csv
import os
import tempfile
from collections import Counter

ECHO_MATCH_TYPE = 'companyid - id_in_source'


def read_csv_rows(filename):
    '''Returns (header, rows) with rows as lists of field values.'''
    with open(filename, newline='', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = next(reader)
        return header, [row for row in reader if row]


def _column_indices(header, filename, columns):
    try:
        return [header.index(c) for c in columns]
    except ValueError:
        raise ValueError(
            'suppress-echo-matches: %s is missing one of the columns %s '
            '(header: %s)' % (filename, columns, header))


def partition_echo_rows(built_header, built_rows, prior_header, prior_rows,
                        built_name='built', prior_name='prior'):
    '''Pure partition: returns (kept_rows, suppressed_rows, counts). Pairs are
    compared unordered on (orgA_uid, orgB_uid).'''

    a_i, b_i, mt_i = _column_indices(
        built_header, built_name, ['orgA_uid', 'orgB_uid', 'match_type'])
    pa_i, pb_i, pmt_i = _column_indices(
        prior_header, prior_name, ['orgA_uid', 'orgB_uid', 'match_type'])

    prior_pairs = set()
    prior_exact = set()
    for row in prior_rows:
        pair = tuple(sorted((row[pa_i], row[pb_i])))
        prior_pairs.add(pair)
        prior_exact.add((pair, row[pmt_i]))

    evidence = Counter(tuple(sorted((row[a_i], row[b_i]))) for row in built_rows)

    kept, suppressed = [], []
    counts = {'built': len(built_rows), 'prior': len(prior_rows),
              'suppressed': 0, 'kept_sole_evidence': 0}
    for row in built_rows:
        pair = tuple(sorted((row[a_i], row[b_i])))
        if (row[mt_i] == ECHO_MATCH_TYPE
                and (pair, ECHO_MATCH_TYPE) not in prior_exact
                and pair in prior_pairs):
            if evidence[pair] > 1:
                suppressed.append(row)
                counts['suppressed'] += 1
                continue
            counts['kept_sole_evidence'] += 1
        kept.append(row)
    return kept, suppressed, counts


def _write_atomic(path, header, rows):
    out_dir = os.path.dirname(os.path.abspath(path))
    fd, tmp_path = tempfile.mkstemp(suffix='.csv', dir=out_dir)
    try:
        with os.fdopen(fd, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
    except BaseException:
        os.remove(tmp_path)
        raise
    return tmp_path


def suppress_echo_matches(built_matches_csv, prior_matches_csv):
    '''Reads both files, partitions, and atomically replaces the built matches
    file, keeping the original as <name>.preecho.csv and the suppressed rows
    as <name>.suppressed-echo.csv.'''

    built_header, built_rows = read_csv_rows(built_matches_csv)
    prior_header, prior_rows = read_csv_rows(prior_matches_csv)

    kept, suppressed, counts = partition_echo_rows(
        built_header, built_rows, prior_header, prior_rows,
        built_matches_csv, prior_matches_csv)

    backup = built_matches_csv.replace('.csv', '.preecho.csv')
    if os.path.exists(backup):
        raise RuntimeError(
            'suppress-echo-matches: backup %s already exists - this file '
            'appears to have been processed already. Remove the backup to '
            're-run.' % backup)
    sidecar = built_matches_csv.replace('.csv', '.suppressed-echo.csv')

    tmp_sidecar = _write_atomic(sidecar, built_header, suppressed)
    tmp_main = _write_atomic(built_matches_csv, built_header, kept)
    try:
        os.replace(tmp_sidecar, sidecar)
        os.replace(built_matches_csv, backup)
        os.replace(tmp_main, built_matches_csv)
    except BaseException:
        for p in (tmp_sidecar, tmp_main):
            if os.path.exists(p):
                os.remove(p)
        raise

    print('suppress-echo-matches: suppressed %(suppressed)s of %(built)s built '
          'rows as bootstrap echo (%(kept_sole_evidence)s candidate rows kept '
          'as their pair\'s sole evidence); prior file had %(prior)s rows.'
          % counts)
    print('suppress-echo-matches: wrote %s rows to %s (original kept as %s, '
          'suppressed rows in %s)' % (len(kept), built_matches_csv, backup, sidecar))
    return counts
