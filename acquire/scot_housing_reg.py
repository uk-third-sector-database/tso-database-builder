"""Scottish Housing Regulator: annual landlord dataset (AFS).

Source page : https://www.housingregulator.gov.scot/landlord-performance/statistical-information/
Product     : "afs_public.csv" - the annual financial statements dataset
              for all registered social landlords. Its leading columns
              (Financial Year, Reg No, Social Landlord, Constitution,
              Clients, Landlord type, Settlement, National Operator) are
              exactly the fields the pipeline keeps
              (handler/preprocess.py ScHR_fields).
Output      : <raw_root>/ScotHousingReg/all-social-landlords-YYYY.csv
              where YYYY is the latest financial-year end in the data
              (e.g. Financial Year 2024/25 -> 2025).

Encoding note: the regulator serves the CSV with a UTF-8 byte-order
mark but a Windows-1252 body (it contains raw 0xA3 pound signs -
verified July 2026). The BOM is stripped and the body saved unchanged,
which is exactly what the preprocess step's Latin-1 reader expects.
"""

import argparse
import csv
import io
import re
from datetime import date

from .common import (DEFAULT_RAW_ROOT, http_get, resolve_outdir,
                     strip_utf8_bom)

CSV_URL = 'https://shrpublicdata.blob.core.windows.net/csv/afs_public.csv'
SOURCE_PAGE = ('https://www.housingregulator.gov.scot/landlord-performance/'
               'statistical-information/')


def _latest_year(text):
    """Latest financial-year end year in the Financial Year column,
    e.g. '2024/2025' or '2024/25' -> 2025. Falls back to the current
    year (with a warning) if no year parses."""
    try:
        reader = csv.DictReader(io.StringIO(text))
        years = set()
        for row in reader:
            fy = (row.get('Financial Year') or '').strip()
            m = re.match(r'(\d{4})/(\d{2}|\d{4})$', fy)
            if m:
                start, end = m.groups()
                years.add(int(end) if len(end) == 4 else int(start) + 1)
        if years:
            return max(years)
    except Exception:
        pass
    print('WARNING: no Financial Year values parsed; naming the file '
          'with the current year')
    return date.today().year


def download_landlords(outdir=None, year=None):
    """Download the SHR all-social-landlords dataset. Returns the path
    written. `year` overrides the YYYY used in the filename."""
    folder = resolve_outdir(outdir, 'ScotHousingReg')
    print(f'Downloading {CSV_URL}')
    resp = http_get(CSV_URL)
    print(f'  got {len(resp.content):,} bytes')
    # BOM + Windows-1252 body (see module docstring): strip the BOM,
    # keep the body bytes unchanged for the preprocess Latin-1 reader
    data = strip_utf8_bom(resp.content)
    text = data.decode('cp1252', errors='replace')

    header = text.split('\n', 1)[0]
    for needed in ['Financial Year', 'Reg No', 'Social Landlord']:
        if needed not in header:
            raise RuntimeError(
                f'Column {needed!r} missing from the download - the '
                f'dataset layout has changed')

    if year is None:
        year = _latest_year(text)
    out = folder / f'all-social-landlords-{year}.csv'
    out.write_bytes(data)
    n_rows = text.count('\n') - 1
    print(f'  wrote ~{n_rows:,} rows -> {out}')
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Download the Scottish Housing Regulator annual '
                    'landlord dataset (afs_public.csv)')
    parser.add_argument('--outdir', default=None,
                        help=f'raw-data root (default {DEFAULT_RAW_ROOT})')
    parser.add_argument('--year', type=int, default=None,
                        help='override the YYYY in the output filename '
                             '(default: latest financial year in the data)')
    args = parser.parse_args()
    download_landlords(outdir=args.outdir, year=args.year)
