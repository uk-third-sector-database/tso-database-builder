"""Reconstruct the lost 2022 Companies House advanced-search scrape file
from the published Spine v1.0 release.

Why this module exists
----------------------
The register rebuild (``cli.py preprocess-CH``) reads every
``../raw_data/CompaniesHouse/ch_adv_scrape*.csv``.  The historical file in
that set was the one-off 2022 output of
github.com/uk-third-sector-database/ch_adv_scraper and is the pipeline's
ONLY source for companies dissolved before the monthly bulk downloads
began (the bulk file carries live companies only).  If the 2022 file is
absent, a from-raw rebuild silently drops those pre-2010s dissolved
companies.  The file is lost; its content, however, survives inside the
published v1.0 release.  This module derives a replacement,
``ch_adv_scrape_bootstrap.csv``, with EXACTLY the 2022 scraper's column
layout (imported from acquire.companies_house_api.FIELDNAMES so the schema
cannot drift) so the existing handler ingests it unchanged.

Same principle as spine/bootstrap_base_files.py for the charity
regulators; read that module's docstring for the shared background.

What is written
---------------
One row per company, for every GB-COH organisation in the published
release: organisations with their own spine row (source_register
'Companies House') plus organisations that were absorbed into another
organisation during linkage (present only in the supplementary and
matches files - typically the company half of a charity-company pair).

ONE row per company is deliberate (the charity bases write name/address
variant rows; this file must not).  All rows of a ch_adv_scrape* file
without a date in its name share the historical iteration '2022', and
handler.base.find_primary_info breaks equal-iteration ties arbitrarily -
variant rows could therefore surface an old name as primary for any
company that never reappears in a bulk download (exactly the CCNI
removed-organisation problem, see bootstrap_base_files).  Historical
variants remain available to researchers in the published v1.0
supplementary file.

Value conventions
-----------------
* company_number is recovered from the uid (GB-COH-x); string operations
  only, so leading zeros survive.
* Dates are converted dd/mm/yyyy -> YYYY-MM-DD (the API format the
  handler's map_date parses; anything else would crash it).  Unparseable
  dates are blanked and counted.
* A spine row's dates can belong to a matched partner rather than to the
  company (the build takes the earliest registration / latest removal
  across matched sources, displacing the company's own date into the
  supplementary file).  Rules, per company - the single-row resolution of
  bootstrap_base_files.choose_primary_dates:
    - date_of_creation: if the company is matched AND CH-attributed
      supplementary registration dates exist, the earliest of those (the
      displaced own date); else the spine date.
    - date_of_cessation: spine removal blank -> latest CH-attributed
      supplementary removal if any (recovers removals the spine
      suppressed while a matched partner lived on); spine removal set and
      company matched and supplementary removal exists -> the
      supplementary (own) removal; else the spine removal.
* Absorbed companies (no spine row of their own): name/address from their
  first CH-attributed supplementary row; a missing name is filled from
  the absorbing organisation's spine row (the build blanked fields that
  were identical to the absorber's, so the absorber's value is the best -
  usually exact - estimate).  Only the postcode of the address is filled
  from the absorber, mirroring bootstrap_base_files.  Dates: earliest /
  latest own supplementary date first, else the absorber's spine date
  (registration always; removal only if the absorber itself is removed).
* company_subtype: 'community-interest-company' when the spine flags
  is_cic, the exact value handler.all_companies_house.find_CIC_uids and
  the handler's is_cic logic match on.  Absorbed companies inherit the
  absorbing organisation's is_cic flag: the spine build propagates the
  flag from a matched CIC company onto the surviving organisation
  (build_public_spine.sort_matches), so this reverses that propagation.
  A charity absorber flagged CIC got the flag from its company partner -
  a charity cannot itself be a CIC.
* sic_codes: written in the scraper's Python-list format
  ("['82990', '88990']"), which the handler strips back to plain codes.
  Codes come from the published SIC_codes file under the company's own
  uid; for absorbed companies whose SIC was re-keyed to the absorbing
  organisation's uid (spine.add_cso_type/sic_codes_lookup did exactly
  that at build time) the absorber's codes are used, but ONLY when the
  absorber has a single GB-COH partner in the matches file - with two or
  more partners the codes cannot be attributed to one company.
* etag, hits, company_status, company_type, kind, country, region: blank.
  None of them is read by any consumer of ch_adv_scrape* files
  (handler.companies_house_API_scrape.format_row and find_CIC_uids are
  the only consumers; 'companytype' is written to the preprocess
  intermediate but dropped again at process-source and never used).
  company_type detail beyond the CIC flag is the one thing the published
  release does not retain.

Permanent losses (cannot be recovered from the published release)
-----------------------------------------------------------------
* company_type (private-limited-guarant-nsc, registered society, CIO...)
  beyond the CIC flag - blank; unused downstream (see above).
* Name/address history: one row per company (see above); the current
  (final, for dissolved companies) name only.
* SIC codes for absorbed companies whose absorber has several company
  partners - blanked, counted per run.
* company_status - blank; unused downstream.

The output filename carries NO date on purpose: preprocess-CH stamps
dateless ch_adv_scrape files with the historical iteration '2022'
(handler.all_companies_house.api_scrape_iteration), so fresher register
downloads win every recency contest against these rows.

Usage
-----
From the repo root (RUNBOOK section 3):

    python cli.py bootstrap-ch-scrape SPINE.csv SUPPLEMENTARY.csv \
        MATCHES.csv SIC_CODES.csv -o ../raw_data

then run ``python cli.py preprocess-CH`` as normal.  Also callable as a
module (``python -m spine.bootstrap_ch_scrape SPINE SUPP MATCHES SIC
OUT_RAW_DATA_DIR``) or from Python:

    from spine.bootstrap_ch_scrape import write_ch_scrape_bootstrap
    stats = write_ch_scrape_bootstrap(spine_csv, supplementary_csv,
                                      matches_csv, sic_csv,
                                      raw_data_root='../raw_data')
"""

import csv
import os
import re
from collections import defaultdict
from datetime import datetime

from acquire.companies_house_api import FIELDNAMES

CH_REGISTER = 'Companies House'
COH_PREFIX = 'GB-COH-'
CIC_SUBTYPE = 'community-interest-company'
OUTPUT_RELPATH = os.path.join('CompaniesHouse', 'ch_adv_scrape_bootstrap.csv')

# a SIC code is a 4- or 5-digit run; published values are either bare
# codes ('94120'), comma-joined codes ('82990, 88990') or bulk-download
# style 'code - description' text whose description may itself contain
# commas, so codes are extracted rather than split
_SIC_CODE_RE = re.compile(r'\b\d{4,5}\b')


def spine_date_to_scrape(datestr, stats):
    """Published-spine date (dd/mm/yyyy) -> scrape format (YYYY-MM-DD).
    Blank in, blank out; unparseable dates are blanked and counted (the
    handler's map_date would crash on them)."""
    if not datestr:
        return ''
    try:
        return datetime.strptime(datestr.strip(), '%d/%m/%Y').strftime('%Y-%m-%d')
    except ValueError:
        stats['unparseable_dates'] += 1
        return ''


# ---------------------------------------------------------------------------
# loading the published files
# ---------------------------------------------------------------------------

def load_spine(spine_csv):
    """One pass over the published spine.  Returns (coh, all_min):
    coh     : {uid: row-dict} for GB-COH organisations attributed to
              Companies House (the companies with their own spine row)
    all_min : {uid: row-dict} for EVERY spine row (any register) - used to
              look up absorbing organisations, which are usually charities."""
    coh = {}
    all_min = {}
    with open(spine_csv, 'r', newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            slim = {
                'organisationname': row['organisationname'],
                'fulladdress': row['fulladdress'],
                'city': row['city'],
                'postcode': row['postcode'],
                'registerdate': row['registerdate'],
                'removeddate': row['removeddate'],
                'is_cic': row['is_cic'],
            }
            all_min[row['uid']] = slim
            if row['uid'].startswith(COH_PREFIX) and row['source_register'] == CH_REGISTER:
                coh[row['uid']] = slim
    return coh, all_min


def load_matches(matches_csv):
    """One pass over the published matches file.  Returns a dict with:
    matched_uids : every uid appearing in any match row (their spine dates
                   may have been merged across sources)
    absorbed_into: orgB_uid -> orgA_uid for real (uid non-blank) merges;
                   GB-COH uids absent from the spine main file live here
    coh_partners : uid -> set of GB-COH partner uids (any match type), for
                   the SIC unambiguous-absorber rule"""
    matched_uids = set()
    absorbed_into = {}
    coh_partners = defaultdict(set)
    with open(matches_csv, 'r', newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            a, b = row['orgA_uid'], row['orgB_uid']
            if a:
                matched_uids.add(a)
            if b:
                matched_uids.add(b)
            if row['uid'] and a and b and a != b:
                absorbed_into.setdefault(b, a)
            for x, y in ((a, b), (b, a)):
                if x and y and y.startswith(COH_PREFIX):
                    coh_partners[x].add(y)
    return {'matched_uids': matched_uids, 'absorbed_into': absorbed_into,
            'coh_partners': dict(coh_partners)}


def load_supplementary(supplementary_csv):
    """One pass over the published supplementary file.  Returns
    {uid: [rows in file order]} for GB-COH rows attributed to Companies
    House (rows for the same uid attributed to other registers belong to
    those registers' own reconstructions)."""
    supp = defaultdict(list)
    with open(supplementary_csv, 'r', newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            if row['uid'].startswith(COH_PREFIX) and row['source_register'] == CH_REGISTER:
                supp[row['uid']].append({
                    'organisationname': row['organisationname'],
                    'fulladdress': row['fulladdress'],
                    'city': row['city'],
                    'postcode': row['postcode'],
                    'registerdate': row['registerdate'],
                    'removeddate': row['removeddate'],
                })
    return dict(supp)


def load_sic(sic_csv):
    """One pass over the published SIC_codes file.  Returns
    {uid: [codes in first-seen order, de-duplicated]}.  The file holds
    several rows per uid and mixed value formats; see _SIC_CODE_RE."""
    sic = defaultdict(list)
    with open(sic_csv, 'r', newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            for code in _SIC_CODE_RE.findall(row['SIC']):
                if code not in sic[row['uid']]:
                    sic[row['uid']].append(code)
    return dict(sic)


# ---------------------------------------------------------------------------
# per-company date and detail selection
# ---------------------------------------------------------------------------

def _earliest(dates):
    return min(dates, key=lambda d: datetime.strptime(d.strip(), '%d/%m/%Y'))


def _latest(dates):
    return max(dates, key=lambda d: datetime.strptime(d.strip(), '%d/%m/%Y'))


def _own_dates(supp_rows):
    """(registration dates, removal dates) present on the company's own
    CH-attributed supplementary rows, parseable ones only (unparseable
    values cannot win a min/max and are handled at write time)."""
    def parseable(d):
        try:
            datetime.strptime(d.strip(), '%d/%m/%Y')
            return True
        except ValueError:
            return False
    reg = [r['registerdate'] for r in supp_rows if r['registerdate'] and parseable(r['registerdate'])]
    rem = [r['removeddate'] for r in supp_rows if r['removeddate'] and parseable(r['removeddate'])]
    return reg, rem


def choose_dates(spine_row, supp_rows, is_matched, absorber_row, stats):
    """Return (registerdate, removeddate) in dd/mm/yyyy - the single-row
    resolution of bootstrap_base_files.choose_primary_dates (that module
    can defer to variant rows; a scrape row cannot)."""
    own_reg, own_rem = _own_dates(supp_rows)

    if spine_row is None:
        # absorbed organisation: no spine row of its own
        if own_reg:
            regdate = _earliest(own_reg)
        else:
            regdate = absorber_row['registerdate'] if absorber_row else ''
            if regdate:
                stats['regdate_filled_from_absorber'] += 1
        if own_rem:
            remdate = _latest(own_rem)
        else:
            remdate = absorber_row['removeddate'] if absorber_row else ''
            if remdate:
                stats['remdate_filled_from_absorber'] += 1
        return regdate, remdate

    # ---- registration ----
    if is_matched and own_reg:
        # the spine date may be a matched partner's; prefer the displaced own date
        regdate = _earliest(own_reg)
        stats['regdate_recovered_from_supplementary'] += 1
    else:
        regdate = spine_row['registerdate']

    # ---- removal ----
    spine_rem = spine_row['removeddate']
    if not spine_rem:
        remdate = _latest(own_rem) if own_rem else ''
        if remdate:
            stats['removal_recovered_from_supplementary'] += 1
    elif is_matched and own_rem:
        remdate = _latest(own_rem)
        stats['remdate_spine_date_set_aside'] += 1
    else:
        remdate = spine_rem

    return regdate, remdate


def _pick_details(supp_rows, absorber_row, stats):
    """Primary name/address for an absorbed company: its first
    CH-attributed supplementary row is its own primary record (the build
    wrote it first); a missing name is filled from the absorber, a missing
    address gets only the absorber's postcode (see module docstring)."""
    name = ''
    address = city = postcode = ''
    for r in supp_rows:
        if r['organisationname']:
            name = r['organisationname']
            if r['fulladdress'] or r['postcode']:
                address, city, postcode = r['fulladdress'], r['city'], r['postcode']
            break
    if not name and absorber_row:
        name = absorber_row['organisationname']
        stats['name_filled_from_absorber'] += 1
    if not address and not postcode:
        for r in supp_rows:
            if r['fulladdress'] or r['postcode']:
                address, city, postcode = r['fulladdress'], r['city'], r['postcode']
                break
    if not postcode and absorber_row and absorber_row['postcode']:
        postcode = absorber_row['postcode']
        stats['postcode_filled_from_absorber'] += 1
    return name, address, city, postcode


# ---------------------------------------------------------------------------
# row builder and assembly
# ---------------------------------------------------------------------------

def build_company_row(uid, spine_row, supp_rows, is_matched, absorber_row,
                      sic_codes, stats):
    """One ch_adv_scrape-layout row for one GB-COH organisation."""
    number = uid[len(COH_PREFIX):]
    regdate, remdate = choose_dates(spine_row, supp_rows, is_matched, absorber_row, stats)

    if spine_row is not None:
        name = spine_row['organisationname']
        address, city, postcode = (spine_row['fulladdress'], spine_row['city'],
                                   spine_row['postcode'])
        cic = spine_row['is_cic'] == 'True'
    else:
        name, address, city, postcode = _pick_details(supp_rows, absorber_row, stats)
        cic = bool(absorber_row) and absorber_row['is_cic'] == 'True'
        if cic:
            stats['cic_inherited_from_absorber'] += 1
        if not name:
            stats['companies_without_name'] += 1

    row = {f: '' for f in FIELDNAMES}
    row.update(
        company_name=name,
        company_number=number,
        company_subtype=CIC_SUBTYPE if cic else '',
        date_of_creation=spine_date_to_scrape(regdate, stats),
        date_of_cessation=spine_date_to_scrape(remdate, stats),
        sic_codes=str(sic_codes) if sic_codes else '',
        address_line_1=address,
        locality=city,
        postal_code=postcode,
    )
    return row


def sic_for(uid, absorbed_into, coh_partners, sic, stats):
    """SIC codes for a company: its own uid first; for absorbed companies,
    the absorber's codes when the absorber has exactly one GB-COH partner
    (the build re-keyed absorbed companies' SIC to the absorber's uid)."""
    if uid in sic:
        return sic[uid]
    absorber = absorbed_into.get(uid)
    if absorber and absorber in sic:
        if len(coh_partners.get(absorber, ())) == 1:
            stats['sic_via_absorber'] += 1
            return sic[absorber]
        stats['sic_ambiguous_absorber'] += 1
    return []


def reconstruct_companies(spine_coh, all_spine, supp, links, sic):
    """Build the full row list.  Returns (rows, stats)."""
    matched_uids = links['matched_uids']
    absorbed_into = links['absorbed_into']
    coh_partners = links['coh_partners']

    stats = defaultdict(int)
    uids = set(spine_coh)
    absorbed = {u for u in absorbed_into
                if u.startswith(COH_PREFIX) and u not in uids}
    extra_from_supp = {u for u in supp if u not in uids and u not in absorbed}
    stats['companies_from_spine'] = len(uids)
    stats['companies_absorbed_recovered'] = len(absorbed)
    stats['companies_supp_only'] = len(extra_from_supp)  # expected 0

    rows = []
    for uid in sorted(uids | absorbed | extra_from_supp):
        spine_row = spine_coh.get(uid)
        supp_rows = supp.get(uid, [])
        absorber_row = None
        if spine_row is None:
            absorber_uid = absorbed_into.get(uid)
            absorber_row = all_spine.get(absorber_uid) if absorber_uid else None
            if absorber_uid and absorber_row is None:
                stats['absorber_missing_from_spine'] += 1
        codes = sic_for(uid, absorbed_into, coh_partners, sic, stats)
        if not codes:
            stats['companies_without_sic'] += 1
        rows.append(build_company_row(uid, spine_row, supp_rows,
                                      uid in matched_uids, absorber_row,
                                      codes, stats))
        if rows[-1]['company_subtype'] == CIC_SUBTYPE:
            stats['cic_companies'] += 1
    stats['rows_written'] = len(rows)
    return rows, dict(stats)


def write_ch_scrape_bootstrap(spine_csv, supplementary_csv, matches_csv,
                              sic_csv, raw_data_root):
    """Reconstruct and write CompaniesHouse/ch_adv_scrape_bootstrap.csv
    under raw_data_root (typically '../raw_data').  Returns the stats dict."""
    links = load_matches(matches_csv)
    spine_coh, all_spine = load_spine(spine_csv)
    supp = load_supplementary(supplementary_csv)
    sic = load_sic(sic_csv)

    rows, counts = reconstruct_companies(spine_coh, all_spine, supp, links, sic)

    path = os.path.join(raw_data_root, OUTPUT_RELPATH)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', newline='', encoding='UTF8') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    stats = {**counts, 'output': path}

    print('%d companies (%d from spine, %d recovered from merges), %d rows -> %s'
          % (stats['companies_from_spine'] + stats['companies_absorbed_recovered']
             + stats['companies_supp_only'],
             stats['companies_from_spine'], stats['companies_absorbed_recovered'],
             stats['rows_written'], path))
    for k in sorted(stats):
        if k not in ('output', 'rows_written', 'companies_from_spine',
                     'companies_absorbed_recovered', 'companies_supp_only'):
            print('    %s: %s' % (k, stats[k]))
    return stats


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description='Reconstruct the 2022 Companies House '
                                'advanced-search scrape file from a published '
                                'Spine release.')
    p.add_argument('spine_csv')
    p.add_argument('supplementary_csv')
    p.add_argument('matches_csv')
    p.add_argument('sic_csv')
    p.add_argument('raw_data_root', help="destination, typically ../raw_data")
    args = p.parse_args()
    write_ch_scrape_bootstrap(args.spine_csv, args.supplementary_csv,
                              args.matches_csv, args.sic_csv, args.raw_data_root)
