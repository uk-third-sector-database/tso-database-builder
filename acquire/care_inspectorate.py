"""Care Inspectorate Scotland: MDSF / datastore extract.

Source page : https://www.careinspectorate.com/index.php/publications-statistics/93-public/datastore
Product     : the periodic "datastore" CSV of all registered care
              services (published roughly monthly/quarterly; each
              snapshot has its own library page linking a CSV on S3,
              e.g. .../datastore/260531datastoreexternal.csv)
Output      : <raw_root>/CareInspectScot/MDSF_data_YYYY.csv   (default)
              or, with --monthly-name,
              <raw_root>/CareInspectScot/MDSF_data.MonYYYY.csv

Both names are accepted by handler/preprocess.py. The default yearly
name matches the RUNBOOK convention but only allows one snapshot per
year in the folder; use --monthly-name if you download more often than
yearly, so earlier snapshots are not shadowed.

The module lists the datastore library pages, picks the most recent
snapshot by the date in the page address (several date spellings are
in use: 31-03-2026, 30-april-2026, 30nov2025 ...), then downloads the
CSV linked from that page.
"""

import argparse
import re
from datetime import datetime

from .common import DEFAULT_RAW_ROOT, http_get, resolve_outdir

INDEX_PAGE = ('https://www.careinspectorate.com/index.php/'
              'publications-statistics/93-public/datastore')
BASE = 'https://www.careinspectorate.com'


def _parse_slug_date(slug):
    """Date out of a datastore page slug, e.g. 'datastore-31-03-2026',
    'datastore-30-april-2026', 'datastore-30nov2025'. None if unparsed."""
    tail = slug.rsplit('datastore-', 1)[-1]
    for fmt in ('%d-%m-%Y', '%d-%B-%Y', '%d-%b-%Y', '%d%b%Y', '%d%B%Y'):
        try:
            return datetime.strptime(tail, fmt)
        except ValueError:
            continue
    return None


def find_latest_snapshot():
    """Return (page_url, snapshot_datetime) of the newest datastore page."""
    resp = http_get(INDEX_PAGE, timeout=60)
    pages = set(re.findall(
        r'href="(/resources-data/[^"]*datastore-[^"]+)"', resp.text))
    dated = []
    for p in pages:
        d = _parse_slug_date(p)
        if d:
            dated.append((d, p))
    if not dated:
        raise RuntimeError(
            f'No dated datastore pages found on {INDEX_PAGE}')
    d, p = max(dated)
    return BASE + p, d


def download_datastore(outdir=None, monthly_name=False):
    """Download the latest Care Inspectorate datastore CSV.
    Returns the path written."""
    folder = resolve_outdir(outdir, 'CareInspectScot')
    page_url, snap = find_latest_snapshot()
    print(f'Latest datastore snapshot: {snap:%d %b %Y} ({page_url})')

    page = http_get(page_url, timeout=60).text
    m = re.search(r'href="(https?://[^"]+\.csv)"', page)
    if not m:
        raise RuntimeError(f'No CSV link found on {page_url}')
    csv_url = m.group(1)
    print(f'Downloading {csv_url}')
    resp = http_get(csv_url)

    header = resp.content.split(b'\n', 1)[0].decode('utf-8',
                                                    errors='replace')
    if 'CSNumber' not in header and 'CaseNumber' not in header:
        raise RuntimeError(
            'Neither CSNumber nor CaseNumber in the download header - '
            'the datastore layout has changed; handler/preprocess.py '
            'may need a new column variant. Header: ' + header[:300])

    if monthly_name:
        out = folder / f'MDSF_data.{snap:%b%Y}.csv'
    else:
        out = folder / f'MDSF_data_{snap:%Y}.csv'
    out.write_bytes(resp.content)
    n_rows = resp.content.count(b'\n') - 1
    print(f'  saved {len(resp.content):,} bytes (~{n_rows:,} rows) -> {out}')
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Download the latest Care Inspectorate Scotland '
                    'datastore (MDSF) CSV')
    parser.add_argument('--outdir', default=None,
                        help=f'raw-data root (default {DEFAULT_RAW_ROOT})')
    parser.add_argument('--monthly-name', action='store_true',
                        help='save as MDSF_data.MonYYYY.csv (month '
                             'precision) instead of MDSF_data_YYYY.csv')
    args = parser.parse_args()
    download_datastore(outdir=args.outdir, monthly_name=args.monthly_name)
