"""Companies House API: organisation-details fetcher for known companies.

Source API  : https://api.company-information.service.gov.uk/company/{number}
              (company profile endpoint; needs a free API key)
Input       : a list of company numbers (command line or a text file,
              one number per line)
Output      : <raw_root>/CompaniesHouse/ch_api_company_profiles_YYYY-MM-DD.csv

The output uses the SAME column layout as the historical
ch_adv_scrape*.csv files (see handler/companies_house_API_scrape.py):
etag, hits, company_name, company_number, company_status,
company_subtype, company_type, date_of_cessation, date_of_creation,
sic_codes, kind, address_line_1, address_line_2, country, locality,
postal_code, region - with sic_codes as a Python-list-style string.
The default output name deliberately does NOT match the pipeline's
ch_adv_scrape* glob: rename the file to ch_adv_scrape_<something>.csv
only if you intend the pipeline to consume it (note the handler stamps
those files with a hard-coded 2022 iteration).

API keys: comma-separated in the COH_API_KEYS environment variable, or
in a .env file passed with --env-file (e.g. the cso-spine project's
.env). Keys are NEVER hard-coded here. Fetching runs one worker thread
per key, each pacing itself to stay inside the API's 600 requests per
5 minutes PER-KEY allowance (2/second), so 12 keys sustain roughly 20
requests/second overall; a 429 response backs that key off without
stalling the others.

Scope note: this replaces the external ch_adv_scraper dependency's
"organisation details" role only. Rebuilding the 2022-style advanced
-search sweep of companies dissolved before the bulk product began
still needs the ch_adv_scraper repository (advanced-search endpoint).
The routine "which spine companies have dissolved?" refresh is driven
by acquire.ch_dissolution_check, which derives the candidate list and
writes a pipeline-consumable ch_adv_scrape_api_refresh_YYYY-MM-DD.csv.
"""

import argparse
import csv
import os
import queue
import threading
import time
from datetime import date
from pathlib import Path

import requests

from .common import DEFAULT_RAW_ROOT, USER_AGENT, resolve_outdir

API_URL = 'https://api.company-information.service.gov.uk/company/{}'
FIELDNAMES = ['etag', 'hits', 'company_name', 'company_number',
              'company_status', 'company_subtype', 'company_type',
              'date_of_cessation', 'date_of_creation', 'sic_codes',
              'kind', 'address_line_1', 'address_line_2', 'country',
              'locality', 'postal_code', 'region']
RATE_LIMIT_SLEEP = 60          # initial back-off after a 429 on a key
PER_KEY_DELAY = 0.55           # seconds between one key's requests
                               # (~1.8/s, inside the 2/s per-key limit)
MAX_403_RETRIES = 2            # 403 can be an IP/anti-abuse block, not just a
                               # bad key: back off and retry before skipping
                               # (observed 18 Jul 2026: sustained ~20 req/s
                               # got every key 403-blocked mid-run)
ABORT_AFTER_CONSECUTIVE = 30   # a run of consecutive failures across all
                               # keys means the source is blocking us: stop
                               # the whole fetch (it is resumable) instead of
                               # burning the rest of the candidate list


def load_api_keys(env_file=None, env_var='COH_API_KEYS'):
    """API keys as a list, from the environment or a .env file.

    Looks in os.environ[env_var] first; if absent and `env_file` is
    given, parses that file for a `COH_API_KEYS=key1,key2` line."""
    raw = os.environ.get(env_var, '')
    if not raw and env_file:
        for line in Path(env_file).read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line.startswith(env_var + '='):
                raw = line.split('=', 1)[1].strip().strip('"').strip("'")
                break
    keys = [k.strip() for k in raw.split(',') if k.strip()]
    if not keys:
        raise RuntimeError(
            f'No Companies House API keys found: set {env_var} '
            f'(comma-separated) in the environment or pass --env-file '
            f'pointing at a .env file that defines it')
    return keys


def _profile_to_row(profile):
    """Company-profile JSON -> flat row in the ch_adv_scrape layout."""
    addr = profile.get('registered_office_address') or {}
    sic = profile.get('sic_codes') or []
    return {
        'etag': profile.get('etag', ''),
        'hits': '',                       # advanced-search-only field
        'company_name': profile.get('company_name', ''),
        'company_number': profile.get('company_number', ''),
        'company_status': profile.get('company_status', ''),
        'company_subtype': profile.get('subtype', ''),
        'company_type': profile.get('type', ''),
        'date_of_cessation': profile.get('date_of_cessation', ''),
        'date_of_creation': profile.get('date_of_creation', ''),
        'sic_codes': str(sic),            # "['12345', ...]" like the scrape
        'kind': 'companyprofile',
        'address_line_1': addr.get('address_line_1', ''),
        'address_line_2': addr.get('address_line_2', ''),
        'country': addr.get('country', ''),
        'locality': addr.get('locality', ''),
        'postal_code': addr.get('postal_code', ''),
        'region': addr.get('region', ''),
    }


def fetch_company(number, key, timeout=60):
    """Fetch one company profile. Returns (status_code, row_or_None).
    The API key is the HTTP basic-auth username, password empty."""
    resp = requests.get(API_URL.format(number.strip()),
                        auth=(key, ''), timeout=timeout,
                        headers={'User-Agent': USER_AGENT})
    if resp.status_code == 200:
        return 200, _profile_to_row(resp.json())
    return resp.status_code, None


def fetch_companies(numbers, keys=None, outdir=None, outfile=None,
                    env_file=None, delay=PER_KEY_DELAY):
    """Fetch profiles for a list of company numbers, one worker thread
    per API key. Each worker paces itself with `delay` seconds between
    its own requests, keeping every key inside the per-key rate limit;
    a 429 backs that one key off exponentially.

    Appends to `outfile` if it exists, skipping numbers already fetched
    (so an interrupted run can simply be re-run). Returns the path."""
    if keys is None:
        keys = load_api_keys(env_file=env_file)
    print(f'{len(keys)} API key(s) loaded; {len(numbers)} companies '
          f'requested')

    if outfile is None:
        folder = resolve_outdir(outdir, 'CompaniesHouse')
        outfile = folder / (f'ch_api_company_profiles_'
                            f'{date.today():%Y-%m-%d}.csv')
    outfile = Path(outfile)

    done = set()
    if outfile.exists():
        with open(outfile, newline='', encoding='utf-8') as f:
            done = {r['company_number'] for r in csv.DictReader(f)}
        print(f'  resuming: {len(done)} companies already in {outfile}')
    todo = [n for n in numbers if n.strip() and n.strip() not in done]

    todo_q = queue.Queue()
    for n in todo:
        todo_q.put(n.strip())
    write_lock = threading.Lock()   # one writer: csv + counters + prints
    counts = {'done': 0, 'ok': 0, 'missing': 0, 'consecutive_failures': 0}
    aborted = threading.Event()

    mode = 'a' if outfile.exists() else 'w'
    with open(outfile, mode, newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if mode == 'w':
            writer.writeheader()

        def worker(key):
            while not aborted.is_set():
                try:
                    number = todo_q.get_nowait()
                except queue.Empty:
                    return
                backoff = RATE_LIMIT_SLEEP
                retries_403 = 0
                while True:
                    try:
                        status, row = fetch_company(number, key)
                    except (requests.ConnectionError, requests.Timeout) as e:
                        print(f'  {number}: network error ({e}); retrying')
                        time.sleep(5)
                        continue
                    if status == 429:   # this key is limited: back off
                        time.sleep(backoff)
                        backoff = min(backoff * 2, 300)
                        continue
                    if status == 403 and retries_403 < MAX_403_RETRIES:
                        # possibly a transient IP/anti-abuse block, not a
                        # bad key: back off like a 429, a bounded number
                        # of times
                        retries_403 += 1
                        time.sleep(backoff)
                        backoff = min(backoff * 2, 300)
                        continue
                    break
                with write_lock:
                    counts['done'] += 1
                    if status == 200 and row is not None:
                        writer.writerow(row)
                        f.flush()
                        counts['ok'] += 1
                        counts['consecutive_failures'] = 0
                    elif status == 404:
                        # a real answer (the number no longer resolves),
                        # not a sign we are being blocked
                        print(f'  {number}: not found (404)')
                        counts['missing'] += 1
                        counts['consecutive_failures'] = 0
                    else:
                        print(f'  {number}: HTTP {status} - skipped')
                        counts['missing'] += 1
                        counts['consecutive_failures'] += 1
                        if counts['consecutive_failures'] >= ABORT_AFTER_CONSECUTIVE:
                            print(f'ABORTING: {ABORT_AFTER_CONSECUTIVE} '
                                  f'consecutive failures across all keys - '
                                  f'the API is refusing this machine (rate/'
                                  f'anti-abuse block). The fetch is '
                                  f'resumable: re-run later and it will '
                                  f'skip what is already in {outfile.name}.')
                            aborted.set()
                    if counts['done'] % 100 == 0:
                        print(f"  {counts['done']}/{len(todo)} done "
                              f"({counts['ok']} ok)")
                time.sleep(delay)

        threads = [threading.Thread(target=worker, args=(k,))
                   for k in keys]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    outcome = 'ABORTED on sustained failures; partial fetch' if aborted.is_set() \
        else 'Fetched'
    print(f"{outcome} {counts['ok']} profiles ({counts['missing']} not "
          f"returned) -> {outfile}")
    return outfile


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Fetch Companies House company profiles for a list '
                    'of company numbers (needs API key(s) in '
                    'COH_API_KEYS)')
    parser.add_argument('--numbers', default=None,
                        help='comma-separated company numbers')
    parser.add_argument('--input-file', default=None,
                        help='text file with one company number per line')
    parser.add_argument('--outdir', default=None,
                        help=f'raw-data root (default {DEFAULT_RAW_ROOT})')
    parser.add_argument('--outfile', default=None,
                        help='explicit output CSV path (overrides '
                             '--outdir naming)')
    parser.add_argument('--env-file', default=None,
                        help='.env file containing COH_API_KEYS=key1,key2')
    parser.add_argument('--delay', type=float, default=PER_KEY_DELAY,
                        help='seconds between one key\'s requests '
                             '(each key has its own worker thread)')
    args = parser.parse_args()

    if not args.numbers and not args.input_file:
        parser.error('give --numbers or --input-file')
    numbers = []
    if args.numbers:
        numbers += [n.strip() for n in args.numbers.split(',')]
    if args.input_file:
        numbers += [line.strip() for line
                    in Path(args.input_file).read_text().splitlines()
                    if line.strip()]
    fetch_companies(numbers, outdir=args.outdir, outfile=args.outfile,
                    env_file=args.env_file, delay=args.delay)
