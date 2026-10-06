"""Companies House: free monthly bulk data product (live companies).

Source page : https://download.companieshouse.gov.uk/en_output.html
Product     : "BasicCompanyDataAsOneFile-YYYY-MM-DD.zip" (one ~500 MB zip
              containing one multi-GB CSV; published monthly, live
              companies only)
Output      : <raw_root>/CompaniesHouse/BasicCompanyDataAsOneFile-YYYY-MM-DD.csv

The module parses the download page for the current month's one-file
link, streams the zip, and unzips the CSV under the dated name the
preprocess step parses (the CSV member inside the zip carries the same
name; it is renamed to match the zip's date if it ever differs). The
zip is deleted after extraction unless --keep-zip is given.

`--verify-only` resolves the link and checks it is downloadable
(HTTP status and size via a ranged request) without pulling ~500 MB.
"""

import argparse
import re
import zipfile

import requests

from .common import (DEFAULT_RAW_ROOT, USER_AGENT, download_file, http_get,
                     resolve_outdir)

DOWNLOAD_PAGE = 'https://download.companieshouse.gov.uk/en_output.html'
BASE = 'https://download.companieshouse.gov.uk/'


def find_latest_url():
    """Parse the bulk-products page for this month's one-file zip link.
    Returns (absolute_url, YYYY-MM-DD date string)."""
    resp = http_get(DOWNLOAD_PAGE, timeout=60)
    m = re.search(
        r'href="((?:[^"]*/)?BasicCompanyDataAsOneFile-'
        r'(\d{4}-\d{2}-\d{2})\.zip)"', resp.text)
    if not m:
        raise RuntimeError(
            'Could not find a BasicCompanyDataAsOneFile link on '
            + DOWNLOAD_PAGE)
    href, datestr = m.groups()
    url = href if href.startswith('http') else BASE + href.lstrip('/')
    return url, datestr


def verify_link(url=None):
    """Check the one-file zip link resolves, without downloading it.
    Returns (url, size_in_bytes)."""
    if url is None:
        url, datestr = find_latest_url()
        print(f'Latest bulk file: {url} (snapshot {datestr})')
    head = requests.head(url, headers={'User-Agent': USER_AGENT},
                         timeout=60, allow_redirects=True)
    size = int(head.headers.get('Content-Length', 0))
    print(f'  HEAD {head.status_code}, {size:,} bytes, '
          f'{head.headers.get("Content-Type")}')
    # ranged request for the first bytes proves the file is servable and
    # is a zip (PK magic number)
    r = requests.get(url, headers={'User-Agent': USER_AGENT,
                                   'Range': 'bytes=0-3'}, timeout=60)
    ok = r.content.startswith(b'PK')
    print(f'  first bytes: {r.content[:4]!r} (zip: {ok})')
    if head.status_code != 200 or not ok:
        raise RuntimeError('Link did not verify as a downloadable zip')
    return url, size


def download_bulk_file(outdir=None, url=None, keep_zip=False):
    """Download and unzip the monthly one-file bulk product.
    Returns the path of the extracted CSV. NOTE: ~500 MB download,
    ~2.5 GB unzipped."""
    folder = resolve_outdir(outdir, 'CompaniesHouse')
    if url is None:
        url, datestr = find_latest_url()
    else:
        m = re.search(r'(\d{4}-\d{2}-\d{2})\.zip$', url)
        if not m:
            raise ValueError(
                'URL must end BasicCompanyDataAsOneFile-YYYY-MM-DD.zip')
        datestr = m.group(1)

    zip_path = folder / f'BasicCompanyDataAsOneFile-{datestr}.zip'
    csv_path = folder / f'BasicCompanyDataAsOneFile-{datestr}.csv'
    print(f'Downloading {url} (~500 MB; this takes a while)')
    download_file(url, zip_path)

    print(f'Extracting {zip_path}')
    with zipfile.ZipFile(zip_path) as z:
        members = [n for n in z.namelist() if n.lower().endswith('.csv')]
        if len(members) != 1:
            raise RuntimeError(f'Expected one CSV in the zip, found '
                               f'{z.namelist()}')
        # extract under the exact dated name the pipeline expects,
        # whatever the member is called
        with z.open(members[0]) as src, open(csv_path, 'wb') as dst:
            while True:
                chunk = src.read(1024 * 1024)
                if not chunk:
                    break
                dst.write(chunk)
    print(f'  wrote {csv_path} ({csv_path.stat().st_size:,} bytes)')
    if not keep_zip:
        zip_path.unlink()
        print(f'  removed {zip_path}')
    return csv_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Download the monthly Companies House bulk file '
                    '(BasicCompanyDataAsOneFile)')
    parser.add_argument('--outdir', default=None,
                        help=f'raw-data root (default {DEFAULT_RAW_ROOT})')
    parser.add_argument('--url', default=None,
                        help='download a specific month\'s zip instead of '
                             'the latest')
    parser.add_argument('--keep-zip', action='store_true',
                        help='keep the downloaded zip after extraction')
    parser.add_argument('--verify-only', action='store_true',
                        help='resolve and check the link without '
                             'downloading the ~500 MB file')
    args = parser.parse_args()

    if args.verify_only:
        verify_link(url=args.url)
    else:
        download_bulk_file(outdir=args.outdir, url=args.url,
                           keep_zip=args.keep_zip)
