"""Find that Charity: "same-as" relationships lookup (David Kane).

Source      : https://raw.githubusercontent.com/drkane/charity-lookups/refs/heads/master/relationships/_sameas.csv
              (owner-confirmed source, July 2026; the charity-lookups
              repository behind findthatcharity.uk)
Product     : cross-register organisation identifier links, including
              the CCEW Register of Mergers rows
Output      : <raw_root>/FTC_data/dkane_relationships_sameas.csv

This re-derives the lost linkage file listed in RUNBOOK 3.1. The
download already uses the exact column names the build needs -
org_id_a, org_id_b, source (plus relationship, valid_from, valid_to and
name columns, which the build ignores) - with GB-CHC-/GB-SC-/GB-NIC-/
GB-COH- style identifiers, so it is saved as-is after validation.
spine/build_public_spine.py read_dkane_sameas() detects charity mergers
by looking for 'merger' in the source column; the download's
"Charity Commission Register of Mergers" rows satisfy that test.
"""

import argparse
import csv
import io

from .common import DEFAULT_RAW_ROOT, http_get, resolve_outdir

SAMEAS_URL = ('https://raw.githubusercontent.com/drkane/charity-lookups/'
              'refs/heads/master/relationships/_sameas.csv')


def download_sameas(outdir=None):
    """Download the same-as lookup and validate it against what the
    spine build expects. Returns the path written."""
    folder = resolve_outdir(outdir, 'FTC_data')
    print(f'Downloading {SAMEAS_URL}')
    resp = http_get(SAMEAS_URL)
    print(f'  got {len(resp.content):,} bytes')

    text = resp.content.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(text))
    for needed in ['org_id_a', 'org_id_b', 'source']:
        if needed not in (reader.fieldnames or []):
            raise RuntimeError(
                f'Column {needed!r} missing - the file layout has '
                f'changed. Columns: {reader.fieldnames}')

    n_rows = n_merger = n_gb = 0
    for row in reader:
        n_rows += 1
        if 'merger' in (row['source'] or '').lower():
            n_merger += 1
        if row['org_id_a'].startswith('GB-') and \
                row['org_id_b'].startswith('GB-'):
            n_gb += 1
    print(f'  {n_rows:,} link rows; {n_gb:,} GB-to-GB; '
          f'{n_merger:,} Register of Mergers rows')
    if n_merger == 0:
        raise RuntimeError(
            'No Register of Mergers rows found - the merger logic in '
            'the spine build would silently stop working. Check the '
            'source file.')

    out = folder / 'dkane_relationships_sameas.csv'
    out.write_bytes(resp.content)
    print(f'  wrote {out}')
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Download the Find that Charity same-as linkage file '
                    '(dkane_relationships_sameas.csv)')
    parser.add_argument('--outdir', default=None,
                        help=f'raw-data root (default {DEFAULT_RAW_ROOT})')
    args = parser.parse_args()
    download_sameas(outdir=args.outdir)
