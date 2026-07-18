"""CCNI: Charity Commission for Northern Ireland - register + removal dates.

Source site : https://www.charitycommissionni.org.uk/charity-search/
Products    : 1) full register CSV export (includes removed charities)
              2) per-charity removal dates, scraped from each removed
                 charity's details page (CCNI's own export omits them)
Output      : <raw_root>/ccni/register_charitydetails_YYYY_MM_DD.csv
              <raw_root>/ccni/ni-removals-YYYY-MM-DD.csv

This modernises archive/ccni-scrape-2025-05-20.py. Two things changed
on CCNI's site since that script was written (verified July 2026):

* the export endpoint moved from
  /umbraco/api/charityApi/ExportSearchResultsToCsv/ (now 404) to
  /api/charity-search/exportSearchResultsToCsv/, and it now requires
  the same query parameters the search front-end sends - including a
  `homePageId` GUID which this module reads from the search page itself
  (with the July 2026 value as a fallback);
* charity details pages moved to
  /charity-search/charity-details-page/?regId=N&subId=0.

The old script also disabled SSL certificate verification
(verify=False). That hack is no longer needed - the site's certificate
chain verifies cleanly - so verification is left ON here.

The removals scrape is INCREMENTAL: removal dates never change once
recorded, so dates already present in earlier ni-removals-*.csv files
in the output folder are re-used and only newly-removed charities (or
ones whose date failed to parse last time) get a page visit. The first
ever run visits every removed charity (~1,300 as of July 2026; roughly
45 minutes at the politeness delay); routine re-runs take seconds to a
few minutes. Pass --full to ignore the cache and re-scrape everything.
Rows are written incrementally, so a partial file survives an
interruption. Output columns are regid, removed, removed_date (ISO
YYYY-MM-DD), as the preprocess step expects; each output file is a
complete snapshot (cached + freshly scraped rows).
"""

import argparse
import csv
import html as html_module
import re
import time
from datetime import datetime, date
from pathlib import Path

from bs4 import BeautifulSoup

from .common import DEFAULT_RAW_ROOT, http_get, resolve_outdir

BASE = 'https://www.charitycommissionni.org.uk'
SEARCH_PAGE = BASE + '/charity-search/'
EXPORT_URL = BASE + '/api/charity-search/exportSearchResultsToCsv/'
DETAILS_URL = BASE + '/charity-search/charity-details-page/'
# fallback if the search page cannot be read (value seen July 2026)
FALLBACK_HOME_PAGE_ID = 'c0884e5e-b621-4563-a378-2b313e15c74a'

POLITE_DELAY_SECONDS = 1.5     # between details-page requests


def find_home_page_id():
    """Read the homePageId GUID out of the charity-search page's embedded
    configuration (the export API requires it)."""
    try:
        text = http_get(SEARCH_PAGE, timeout=60).text
        # the data-config attribute is HTML-escaped twice
        # (&amp;quot; -> &quot; -> ")
        cfg = html_module.unescape(html_module.unescape(text))
        m = re.search(r'"homePageId"\s*:\s*"([0-9a-f\-]{36})"', cfg)
        if m:
            return m.group(1)
        print('WARNING: homePageId not found on the search page; '
              'using the last known value')
    except Exception as e:
        print(f'WARNING: could not read the search page ({e}); '
              f'using the last known homePageId')
    return FALLBACK_HOME_PAGE_ID


def download_register(outdir=None):
    """Download the full CCNI register (including removed charities).
    Returns the path written."""
    folder = resolve_outdir(outdir, 'ccni')
    params = {
        'homePageId': find_home_page_id(),
        'pageNumber': '1',
        'sortOption': 'Rank;asc',
        'searchText': '',
        'include': 'Removed',
    }
    print(f'Downloading CCNI register export from {EXPORT_URL}')
    resp = http_get(EXPORT_URL, params=params)
    ctype = resp.headers.get('Content-Type', '')
    if 'csv' not in ctype:
        raise RuntimeError(
            f'CCNI export did not return CSV (Content-Type {ctype!r}); '
            f'the export API may have changed again')
    out = folder / f'register_charitydetails_{date.today():%Y_%m_%d}.csv'
    out.write_bytes(resp.content)
    n_rows = resp.content.count(b'\n')
    print(f'  saved {len(resp.content):,} bytes (~{n_rows:,} rows) -> {out}')
    return out


def _parse_removal_date(page_html):
    """Extract the removal date from a charity details page.
    Returns ISO date string or ''. The date appears in a highlighted
    banner: 'This charity was removed from the register on 22 Mar 2021'."""
    soup = BeautifulSoup(page_html, 'html.parser')
    div = soup.find('div', class_=lambda c: bool(c and 'purpose--removed' in c))
    if div is None:
        return ''
    text = div.get_text(' ', strip=True)
    m = re.search(r'(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{4})', text)
    if not m:
        return ''
    for fmt in ('%d %b %Y', '%d %B %Y'):
        try:
            return datetime.strptime(' '.join(m.groups()), fmt).date().isoformat()
        except ValueError:
            continue
    return ''


def load_known_removal_dates(folder):
    """regid -> removal date, from every earlier ni-removals-*.csv in
    `folder`. Only non-blank dates are cached (a blank means the parse
    failed, so that charity is worth another visit); newest file wins."""
    known = {}
    for path in sorted(Path(folder).glob('ni-removals-*.csv')):
        with open(path, newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                d = (row.get('removed_date') or '').strip()
                if d:
                    known[row['regid']] = d
    return known


def scrape_removals(register_csv=None, outdir=None,
                    delay=POLITE_DELAY_SECONDS, limit=None,
                    refetch_all=False):
    """Scrape removal dates for every charity marked Removed in the
    register export, re-using dates from earlier ni-removals files and
    visiting only charities not yet dated (see module docstring).

    register_csv : path to a register_charitydetails_*.csv download
                   (default: the newest one in <raw_root>/ccni/)
    delay        : politeness delay between page requests, seconds
    limit        : stop after this many charities (for testing)
    refetch_all  : ignore earlier files and re-scrape every charity

    Writes <raw_root>/ccni/ni-removals-YYYY-MM-DD.csv incrementally and
    returns its path."""
    folder = resolve_outdir(outdir, 'ccni')
    if register_csv is None:
        candidates = sorted(folder.glob('*charitydetails_*.csv'))
        if not candidates:
            raise FileNotFoundError(
                f'No register download found in {folder}; run '
                f'download_register() first or pass register_csv=')
        register_csv = candidates[-1]
    register_csv = Path(register_csv)
    print(f'Reading removed charities from {register_csv}')

    with open(register_csv, newline='', encoding='Latin-1') as f:
        rows = list(csv.DictReader(f))
    removed_ids = [r['Reg charity number'] for r in rows
                   if r.get('Status', '') == 'Removed']
    print(f'  {len(removed_ids)} removed charities to look up')
    if limit is not None:
        removed_ids = removed_ids[:limit]
        print(f'  limiting to first {len(removed_ids)} (test run)')

    # dates already scraped in earlier runs: read BEFORE opening today's
    # output for writing (today's file may itself be in the glob)
    known = {} if refetch_all else load_known_removal_dates(folder)
    to_fetch = sum(1 for r in removed_ids if r not in known)
    if known:
        print(f'  {len(known)} dates cached from earlier files; '
              f'{to_fetch} pages to visit')

    out = folder / f'ni-removals-{date.today():%Y-%m-%d}.csv'
    n_dates = n_cached = n_fetched = 0
    with open(out, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['regid', 'removed', 'removed_date'])
        for regid in removed_ids:
            cached = known.get(regid, '')
            if cached:
                writer.writerow([regid, 1, cached])
                n_dates += 1
                n_cached += 1
                continue                     # no page visit, no delay
            try:
                resp = http_get(DETAILS_URL,
                                params={'regId': regid, 'subId': '0'},
                                timeout=60)
                removed_date = _parse_removal_date(resp.text)
            except Exception as e:
                print(f'  {regid}: page fetch failed ({e}) - recorded '
                      f'with no date')
                removed_date = ''
            if removed_date:
                n_dates += 1
            n_fetched += 1
            writer.writerow([regid, 1, removed_date])
            f.flush()
            if n_fetched % 50 == 0:
                print(f'  {n_fetched}/{to_fetch} pages done '
                      f'({n_dates} dates found so far)')
            time.sleep(delay)
    print(f'  wrote {len(removed_ids)} rows ({n_dates} with a removal '
          f'date; {n_cached} from cache, {n_fetched} freshly scraped) '
          f'-> {out}')
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Download the CCNI register and scrape removal dates '
                    'for removed charities')
    parser.add_argument('--outdir', default=None,
                        help=f'raw-data root (default {DEFAULT_RAW_ROOT})')
    parser.add_argument('--skip-removals', action='store_true',
                        help='download the register only')
    parser.add_argument('--register-csv', default=None,
                        help='existing register download to use for the '
                             'removals scrape (default: newest in outdir)')
    parser.add_argument('--delay', type=float, default=POLITE_DELAY_SECONDS,
                        help='seconds between details-page requests')
    parser.add_argument('--limit', type=int, default=None,
                        help='scrape only the first N removed charities '
                             '(testing)')
    parser.add_argument('--full', action='store_true',
                        help='ignore dates cached in earlier ni-removals '
                             'files and re-scrape every removed charity')
    args = parser.parse_args()

    if args.register_csv is None:
        register = download_register(outdir=args.outdir)
    else:
        register = args.register_csv
    if not args.skip_removals:
        scrape_removals(register_csv=register, outdir=args.outdir,
                        delay=args.delay, limit=args.limit,
                        refetch_all=args.full)
