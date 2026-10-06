"""CCEW: Charity Commission for England and Wales - full register download.

Source page : https://register-of-charities.charitycommission.gov.uk/en/register/full-register-download
Product     : "charity" table of the public extract (zip of one JSON file)
Output      : <raw_root>/ccew/ccew-publicextract.<monyyyy>.csv
              e.g. ccew-publicextract.jul2026.csv

The Commission publishes the extract as a zip of JSON (or tab-delimited
txt). The pipeline needs a CSV; the original converter notebook
(reformat_ccew.ipynb) was lost, but its 8-line recipe survives in a
comment at the bottom of handler/preprocess_charity_regulators.py:
read the JSON, build a pandas DataFrame, write to_csv. This module
recreates exactly that, and names the CSV from the extract's own
`date_of_extract` field (falling back to today's date).
"""

import argparse
import io
import json
import re
import zipfile
from datetime import datetime, date

import pandas as pd

from .common import (DEFAULT_RAW_ROOT, http_get, resolve_outdir)

DOWNLOAD_PAGE = ('https://register-of-charities.charitycommission.gov.uk'
                 '/en/register/full-register-download')
# fallback if the page layout changes; this is the link the page carried
# when this module was written (July 2026)
FALLBACK_JSON_ZIP = ('https://ccewuksprdoneregsadata1.blob.core.windows.net'
                     '/data/json/publicextract.charity.zip')


def find_charity_zip_url():
    """Scrape the full-register-download page for the current link to the
    JSON zip of the "charity" table. Falls back to the last known URL."""
    try:
        resp = http_get(DOWNLOAD_PAGE, timeout=60)
        links = re.findall(
            r'https?://[^"\']+/data/json/publicextract\.charity\.zip',
            resp.text)
        if links:
            return links[0]
        print('WARNING: could not find the charity JSON zip link on the '
              'download page; using the last known URL')
    except Exception as e:
        print(f'WARNING: could not read the download page ({e}); '
              f'using the last known URL')
    return FALLBACK_JSON_ZIP


def download_register(outdir=None):
    """Download the CCEW charity table and convert it to the CSV the
    pipeline expects. Returns the path written."""
    folder = resolve_outdir(outdir, 'ccew')
    url = find_charity_zip_url()
    print(f'Downloading CCEW public extract (charity table) from {url}')
    resp = http_get(url)
    print(f'  got {len(resp.content):,} bytes')

    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        json_members = [n for n in z.namelist() if n.endswith('.json')]
        if not json_members:
            raise RuntimeError(
                f'No .json member in the downloaded zip: {z.namelist()}')
        with z.open(json_members[0]) as f:
            raw = f.read()

    # the extract is UTF-8 with a BOM: same as the lost converter, which
    # read it with encoding='utf-8-sig'
    data = json.loads(raw.decode('utf-8-sig'))
    df = pd.DataFrame(data)
    print(f'  parsed {len(df):,} charity rows, {len(df.columns)} columns')

    # name the file from the snapshot month recorded inside the extract
    tag = _month_tag(df)
    out = folder / f'ccew-publicextract.{tag}.csv'
    df.to_csv(out, index=False)
    print(f'  wrote {out}')
    return out


def _month_tag(df):
    """monyyyy tag (e.g. 'jul2026') from date_of_extract, else today."""
    try:
        extract_date = str(df['date_of_extract'].iloc[0])[:10]
        d = datetime.strptime(extract_date, '%Y-%m-%d')
    except Exception:
        d = datetime.combine(date.today(), datetime.min.time())
    return d.strftime('%b%Y').lower()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Download the CCEW full register (charity table) and '
                    'convert it to ccew-publicextract.<monyyyy>.csv')
    parser.add_argument('--outdir', default=None,
                        help=f'raw-data root (default {DEFAULT_RAW_ROOT})')
    args = parser.parse_args()
    download_register(outdir=args.outdir)
