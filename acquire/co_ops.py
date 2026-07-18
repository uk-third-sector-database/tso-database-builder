"""Co-operatives UK: open data on co-operative organisations.

Source page : https://www.uk.coop/resources/open-data
Product     : "open_data_organisations_YYYY_MM.csv" (full organisations
              open-data file, refreshed periodically)
Output      : <raw_root>/co_ops/coops_opendata_YYYY_MM.csv

The page links the current organisations CSV directly. YYYY_MM in the
output name is taken from Co-operatives UK's own filename (falling back
to today), because the preprocess step parses the snapshot month from
the last two _-separated parts of the name. A UTF-8 byte-order mark, if
present, is stripped so the first column name survives the preprocess
step's plain-UTF8 reader.
"""

import argparse
import re
from datetime import date

from .common import (DEFAULT_RAW_ROOT, http_get, resolve_outdir,
                     strip_utf8_bom)

OPEN_DATA_PAGE = 'https://www.uk.coop/resources/open-data'


def find_organisations_csv():
    """Find the current organisations open-data CSV link on the page.
    Returns (absolute_url, 'YYYY_MM' tag)."""
    resp = http_get(OPEN_DATA_PAGE, timeout=60)
    links = re.findall(
        r'href="(https?://[^"]*open_data_organisations[^"]*\.csv)"',
        resp.text)
    if not links:
        raise RuntimeError(
            f'No open_data_organisations CSV link found on '
            f'{OPEN_DATA_PAGE}')
    url = links[0]
    m = re.search(r'(\d{4})_(\d{2})\.csv$', url)
    tag = f'{m.group(1)}_{m.group(2)}' if m else f'{date.today():%Y_%m}'
    return url, tag


def download_open_data(outdir=None):
    """Download the Co-operatives UK organisations open-data CSV.
    Returns the path written."""
    folder = resolve_outdir(outdir, 'co_ops')
    url, tag = find_organisations_csv()
    print(f'Downloading {url}')
    resp = http_get(url)
    data = strip_utf8_bom(resp.content)
    header = data.split(b'\n', 1)[0].decode('utf-8', errors='replace')
    for needed in ['CUK Organisation ID', 'Registered Number',
                   'Registered Name']:
        if needed not in header:
            raise RuntimeError(
                f'Column {needed!r} missing from the download - the open '
                f'data layout has changed')
    out = folder / f'coops_opendata_{tag}.csv'
    out.write_bytes(data)
    n_rows = data.count(b'\n') - 1
    print(f'  saved {len(data):,} bytes (~{n_rows:,} rows) -> {out}')
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Download the Co-operatives UK organisations '
                    'open-data CSV')
    parser.add_argument('--outdir', default=None,
                        help=f'raw-data root (default {DEFAULT_RAW_ROOT})')
    args = parser.parse_args()
    download_open_data(outdir=args.outdir)
