"""Companies House dissolution check: which Spine companies have gone?

The free bulk product (BasicCompanyDataAsOneFile) lists LIVE companies
only -- a company that dissolves simply drops out of the next month's
file, and nothing records when or why. So dissolution status has to be
asked for company-by-company through the API, and the candidate set is
not known a priori. This module derives it:

    candidates = Spine organisations with a GB-COH- uid and a blank
                 removeddate (live as far as the register knows)
               MINUS
                 company numbers present in the latest bulk download
                 (still live, no API call needed)

i.e. exactly the companies we believed were alive that have vanished
from the bulk product -- dissolved, converted, or renumbered -- and then
fetches their current profile (company_status + date_of_cessation) via
acquire.companies_house_api with per-key rate-limited threads.

Output: <raw_root>/CompaniesHouse/ch_adv_scrape_api_refresh_YYYY-MM-DD.csv
This name DOES match the pipeline's ch_adv_scrape* glob on purpose: the
whole point is that the next build ingests the refreshed statuses. The
handler stamps iteration from the date in the filename (files without a
date keep the historical 2022 stamp -- see handler/all_companies_house.py).

Usage
-----
  python -m acquire.ch_dissolution_check --spine <TSCS_spine.spine.csv> \
      [--bulk <BasicCompanyDataAsOneFile-....csv>] [--env-file ../.env] \
      [--dry-run] [--list-out candidates.txt]

--bulk defaults to the newest bulk download in <raw_root>/CompaniesHouse.
--dry-run derives and reports the candidate list without calling the API.
New companies in the bulk download need no API work: the normal
preprocess-ch step ingests them with full details from the bulk file.
"""

import argparse
import csv
from datetime import date
from pathlib import Path

from .common import DEFAULT_RAW_ROOT, resolve_outdir
from .companies_house_api import PER_KEY_DELAY, fetch_companies

COH_PREFIX = 'GB-COH-'


def spine_live_coh_numbers(spine_csv):
    """Company numbers of spine rows with a GB-COH- uid and no removeddate."""
    numbers = set()
    with open(spine_csv, newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            uid = (row.get('uid') or '').strip()
            if (uid.startswith(COH_PREFIX)
                    and not (row.get('removeddate') or '').strip()):
                numbers.add(uid[len(COH_PREFIX):])
    return numbers


def bulk_company_numbers(bulk_csv):
    """All company numbers in a bulk download. Handles the header's
    leading-space variant (' CompanyNumber') seen in some vintages."""
    numbers = set()
    with open(bulk_csv, newline='', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = [h.strip() for h in next(reader)]
        idx = header.index('CompanyNumber')
        for row in reader:
            if len(row) > idx:
                numbers.add(row[idx].strip())
    return numbers


def newest_bulk_download(raw_root=None):
    folder = resolve_outdir(raw_root, 'CompaniesHouse')
    candidates = sorted(folder.glob('BasicCompanyDataAsOneFile*.csv'))
    if not candidates:
        raise FileNotFoundError(
            f'No BasicCompanyDataAsOneFile*.csv in {folder}; download one '
            f'with acquire.companies_house_bulk or pass --bulk')
    return candidates[-1]


def derive_candidates(spine_csv, bulk_csv):
    """Spine-live company numbers absent from the bulk download, sorted."""
    live = spine_live_coh_numbers(spine_csv)
    print(f'{len(live):,} spine companies with no removal date '
          f'({Path(spine_csv).name})')
    bulk = bulk_company_numbers(bulk_csv)
    print(f'{len(bulk):,} live companies in the bulk download '
          f'({Path(bulk_csv).name})')
    gone = sorted(live - bulk)
    print(f'{len(gone):,} candidates have disappeared from the bulk file '
          f'-> need an API status check')
    return gone


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Find spine companies missing from the latest bulk '
                    'download and fetch their dissolution status from '
                    'the Companies House API')
    parser.add_argument('--spine', required=True,
                        help='spine CSV (TSCS_spine.spine.csv or the '
                             'published register)')
    parser.add_argument('--bulk', default=None,
                        help='bulk download CSV (default: newest in '
                             '<raw_root>/CompaniesHouse)')
    parser.add_argument('--outdir', default=None,
                        help=f'raw-data root (default {DEFAULT_RAW_ROOT})')
    parser.add_argument('--env-file', default=None,
                        help='.env file containing COH_API_KEYS=key1,key2')
    parser.add_argument('--list-out', default=None,
                        help='also write the candidate numbers to this '
                             'text file (one per line)')
    parser.add_argument('--dry-run', action='store_true',
                        help='derive and report candidates only; no API '
                             'calls')
    parser.add_argument('--delay', type=float, default=PER_KEY_DELAY,
                        help='seconds between one key\'s requests (default '
                             f'{PER_KEY_DELAY}; raise it after a 403 '
                             'anti-abuse block - 12 keys at the default '
                             'sustain ~20 req/s, which got this machine '
                             'blocked on 18 Jul 2026)')
    args = parser.parse_args()

    bulk = args.bulk or newest_bulk_download(args.outdir)
    numbers = derive_candidates(args.spine, bulk)
    if args.list_out:
        Path(args.list_out).write_text('\n'.join(numbers) + '\n',
                                       encoding='utf-8')
        print(f'candidate list written to {args.list_out}')
    if args.dry_run:
        print('dry run: stopping before the API fetch')
    elif not numbers:
        print('nothing to fetch')
    else:
        folder = resolve_outdir(args.outdir, 'CompaniesHouse')
        outfile = folder / (f'ch_adv_scrape_api_refresh_'
                            f'{date.today():%Y-%m-%d}.csv')
        fetch_companies(numbers, outfile=outfile, env_file=args.env_file,
                        delay=args.delay)
