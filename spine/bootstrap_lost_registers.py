"""Reconstruct the lost co-op / housing / care register history from the
published Spine v1.0 release.

Why this module exists
----------------------
Four registers' historical snapshot files were lost and — unlike the three
charity regulators (spine/bootstrap_base_files.py) and the Companies House
2022 scrape (spine/bootstrap_ch_scrape.py) — no reconstruction was ever
written for them:

    Co-operatives               ../raw_data/co_ops/
    Social Housing England      ../raw_data/SocialHousingEngland/
    Scottish Housing Regulator  ../raw_data/ScotHousingReg/
    Care Inspectorate Scotland  ../raw_data/CareInspectScot/

Their fresh downloads list CURRENT members only, so every organisation that
left one of these registers since the lost snapshots simply never enters a
from-raw rebuild. On the July 2026 trial rebuild that cost:

* 281 organisations gone from the spine entirely (233 co-ops, 44 Social
  Housing England, 4 Scottish Housing Regulator);
* ~4,800 match pairs whose absorbed endpoint (a deregistered co-op record,
  a closed Scottish care service, a former housing-association listing)
  never entered the inputs, so the rule had nothing to fire on — even
  though the surviving endpoint is still on the spine in every case.

The published v1.0 release retains those records' content (spine row and/or
supplementary rows, plus the identifier evidence inside its matches file).
This module reads the three published files and writes ONE reconstructed
historical snapshot per register, in the exact raw-download column layout
that handler/preprocess.py + the register's DataHandler already consume.
The records then flow through preprocessing, sub-spine building and record
linkage exactly like any other register snapshot ("through the front
door"), so current and future matching rules re-derive the lost links from
ordinary input data rather than from copied output rows.

Scope: a delta, not a full snapshot
-----------------------------------
Only organisations present in v1.0 (spine, matches or supplementary) and
ABSENT from the fresh downloads currently on disk are written (the
handler's own inclusion filters are applied to the fresh files when
deciding absence, so an organisation the register has since reclassified —
e.g. a housing provider no longer designated "Non-profit" — is still
restored with its v1.0 details). Records the register still lists are NOT
duplicated into the bootstrap: the fresh download remains their sole
input source, which keeps this step a pure addition — it cannot alter any
organisation the rebuild already covers.

Run it ONCE, before handler/preprocess.py. The outputs are permanent
input artifacts (like ch_adv_scrape_bootstrap.csv): keep them in
../raw_data alongside future fresh downloads. The step refuses to
overwrite an existing output.

Value conventions reproduced
----------------------------
* Filenames carry the currency of the published release (January 2026
  build -> "Jan2026"/"2026_01"), so preprocess.py stamps every row with
  iteration 01/2026 and any fresher download wins the recency contest for
  an organisation's current details. (Deregistered organisations never
  reappear in a download, so nothing ever supersedes them — as intended.)
* Primary name/address: the v1.0 spine row where one exists; for absorbed
  organisations (present only in supplementary/matches) the first v1.0
  supplementary row attributed to this register, with a missing name or
  postcode filled from the absorbing organisation's spine row (the build
  blanked fields identical to the absorber's, so the absorber's value is
  the best — usually exact — estimate; same rule as
  bootstrap_base_files._pick_primary_details).
* Dates (dd/mm/yyyy throughout, the format every handler parses): a spine
  row's dates may belong to a matched source rather than this register
  (registerdate = earliest across matched sources, removeddate = latest),
  so for organisations with any v1.0 match the register's OWN dates from
  its supplementary rows are preferred: registration = earliest own date,
  removal = latest own date (this also RECOVERS removals the published
  spine blanked while a matched company lived on). Unmatched
  organisations keep their spine dates. Absorbed organisations use their
  own supplementary dates, falling back to the absorber's registration
  date (removal only if the absorber itself is removed).
* Co-operatives 'Registered Number' (the FCA society number, which the
  'companyid - coop mutual' rule compares against the mutual register):
  recovered from the organisation's own 'companyid - coop mutual' rows in
  the v1.0 matches file — the partner's id_in_source IS the shared
  society number the original rule fired on. This is regulator-published
  data that v1.0 preserved in its matches file, not an inference, so
  restoring it is not a bootstrap echo; and because v1.0 published these
  match rows itself, spine/suppress_echo_matches.py never touches the
  re-fired pairs. Organisations with no such row get a blank number (no
  false links possible).
* Care Inspectorate Scotland rows are written with
  ServiceType='Voluntary or Not for Profit' (the handler's inclusion
  filter — every v1.0 CIS record passed it by construction) and with
  ServiceName=ServiceProvider (the handler demotes ServiceName rows to a
  fixed old iteration; writing the same name in both keeps the primary
  deterministic without leaking a blank name variant).
* Social Housing England rows are written with Designation='Non-profit'
  (the handler's inclusion filter; every v1.0 SHPE record passed it).

Permanent losses (cannot be recovered by this reconstruction)
-------------------------------------------------------------
* Historical name/address variants are NOT written here (a raw snapshot
  row carries one name and one address). They are restored to the final
  release by the existing seed-supplementary step (RUNBOOK section 4 step
  9) once the organisation is back in the spine/matches universe, which
  is triggered by this bootstrap. Match rules only ever fire on primary
  names, so the variants' absence from the inputs does not cost links.
* Scottish Housing Regulator raw files carry no dates or addresses; the
  reconstruction cannot either. (v1.0 spine dates for these organisations
  came from matched sources and regenerate through re-matching.)
* Care Inspectorate Scotland raw files carry no removal date column.
* Lost pairs whose care-service endpoint is still in the fresh CIS
  download but under a different recorded provider name: the register
  itself revised the record, so no honest input reconstruction can make
  the name rule re-fire. These pairs survive only in the published v1.0
  archive.
* Register-specific classification columns never used by the handlers
  (Registrar, Legal Form, Corporate form, CareService...) -> blank.

Usage
-----
    python cli.py bootstrap-lost-registers SPINE.csv SUPPLEMENTARY.csv \
        MATCHES.csv -o ../raw_data [--as-of mm/yyyy]

then `python handler/preprocess.py` and the build as normal (RUNBOOK
section 4). Also callable as a module or from Python:

    from spine.bootstrap_lost_registers import write_lost_register_files
    stats = write_lost_register_files(spine_csv, supplementary_csv,
                                      matches_csv, raw_data_root='../raw_data')
"""

import csv
import glob
import os
import re
from collections import defaultdict
from datetime import datetime

# currency of the published v1.0 details (January 2026 build), mm/yyyy
AS_OF_ITERATION = '01/2026'

DATE_RE = re.compile(r'^\d{2}/\d{2}/\d{4}$')

COOP_FIELDS = ['CUK Organisation ID', 'Registered Number', 'Registrar',
               'Registered Name', 'Trading Name', 'Legal Form',
               'Registered Street', 'Registered City',
               'Registered State/Province', 'Registered Postcode',
               'UK Nation', 'FCA Reporting Classification',
               'Ownership Classification', 'Registered Status',
               'Incorporation Date', 'Dissolved Date']

SHPE_FIELDS = ['Organisation name', 'Registration number',
               'Registration date', 'Designation', 'Corporate form']

SHR_FIELDS = ['Financial Year', 'Reg No', 'Social Landlord', 'Constitution',
              'Clients', 'Landlord type', 'Settlement', 'National Operator']

CIS_FIELDS = ['CSNumber', 'ServiceName', 'ServiceType', 'CareService',
              'Subtype', 'ServiceProvider', 'Address_line_1',
              'Address_line_2', 'Address_line_3', 'Address_line_4',
              'Service_town', 'Service_Postcode', 'DateReg']

REGISTERS = {
    'coops': {
        'prefix': 'GB-COOP-',
        'register': 'Co-operatives',
        'folder': 'co_ops',
        # matches acquire pattern <anything>_YYYY_MM.csv -> iteration mm/yyyy
        'filename': 'coops_bootstrap_{yyyy}_{mm}.csv',
        'fields': COOP_FIELDS,
        'encoding': 'utf-8',
        'forms_spine_rows': True,
    },
    'social_housing_england': {
        'prefix': 'GB-SHPE-',
        'register': 'Social Housing England',
        'folder': 'SocialHousingEngland',
        # matches acquire pattern <anything>_MonYYYY.csv -> iteration mm/yyyy
        'filename': 'registered_providers_bootstrap_{monyyyy}.csv',
        'fields': SHPE_FIELDS,
        'encoding': 'utf-8',
        'forms_spine_rows': True,
    },
    'scot_housing_reg': {
        'prefix': 'GB-SHR-',
        'register': 'Scottish Housing Regulator',
        'folder': 'ScotHousingReg',
        # matches acquire pattern <name>.to_MonYYYY.csv -> iteration mm/yyyy
        # (no hyphens: a hyphen would win the filename date parse instead)
        'filename': 'social_landlords_bootstrap.to_{monyyyy}.csv',
        'fields': SHR_FIELDS,
        'encoding': 'latin-1',
        'forms_spine_rows': True,
    },
    'care_inspectorate_scot': {
        'prefix': 'GB-CIS-',
        'register': 'Care Inspectorate Scotland',
        'folder': 'CareInspectScot',
        # matches preprocess glob MDSF_data*.csv + date parse <name>.MonYYYY.csv
        'filename': 'MDSF_data_bootstrap.{monyyyy}.csv',
        'fields': CIS_FIELDS,
        'encoding': 'latin-1',
        'forms_spine_rows': False,  # CIS records appear in matches only
    },
}


# ---------------------------------------------------------------------------
# loading the three published files
# ---------------------------------------------------------------------------

def load_spine(spine_csv):
    """One pass over the published spine. Returns (by_reg, all_spine):
    by_reg = {register_key: {uid: row}} for the four target registers;
    all_spine = {uid: row} over EVERY register (absorber lookups)."""
    by_reg = {k: {} for k in REGISTERS}
    prefix_of = {v['prefix']: k for k, v in REGISTERS.items()}
    all_spine = {}
    with open(spine_csv, 'r', newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            slim = {
                'organisationname': row['organisationname'],
                'fulladdress': row['fulladdress'],
                'city': row['city'],
                'postcode': row['postcode'],
                'registerdate': row['registerdate'],
                'removeddate': row['removeddate'],
            }
            all_spine[row['uid']] = slim
            for prefix, key in prefix_of.items():
                if row['uid'].startswith(prefix):
                    by_reg[key][row['uid']] = slim
                    break
    return by_reg, all_spine


def load_supplementary(supplementary_csv):
    """One pass over the published supplementary file. Returns
    {register_key: {uid: [rows in file order]}} keeping only rows attributed
    to the register's own source_register (rows for the same uid attributed
    to other registers belong to those registers)."""
    by_reg = {k: defaultdict(list) for k in REGISTERS}
    wanted = {v['register']: k for k, v in REGISTERS.items()}
    with open(supplementary_csv, 'r', newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            key = wanted.get(row['source_register'])
            if key is None:
                continue
            if not row['uid'].startswith(REGISTERS[key]['prefix']):
                continue
            by_reg[key][row['uid']].append({
                'organisationname': row['organisationname'],
                'fulladdress': row['fulladdress'],
                'city': row['city'],
                'postcode': row['postcode'],
                'registerdate': row['registerdate'],
                'removeddate': row['removeddate'],
            })
    return {k: dict(v) for k, v in by_reg.items()}


def load_matches(matches_csv):
    """One pass over the published matches file. Returns a dict with:
      matched_uids  : every uid appearing in any match row
      absorbed_into : orgB_uid -> orgA_uid (organisations absent from the
                      spine main file were absorbed into their orgA)
      uids_in_matches : {register_key: set of uids} for the four registers
      coop_companyid : GB-COOP uid -> FCA society number, recovered from
                      'companyid - coop mutual' rows (the partner's
                      id_in_source is the shared number the rule fired on)
      coop_companyid_conflicts : count of co-ops whose rows disagreed
                      (first value kept)
    """
    matched_uids = set()
    absorbed_into = {}
    uids_in_matches = {k: set() for k in REGISTERS}
    prefix_of = {v['prefix']: k for k, v in REGISTERS.items()}
    coop_companyid = {}
    conflicts = 0

    with open(matches_csv, 'r', newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            a, b = row['orgA_uid'], row['orgB_uid']
            for u in (a, b):
                if u:
                    matched_uids.add(u)
                    for prefix, key in prefix_of.items():
                        if u.startswith(prefix):
                            uids_in_matches[key].add(u)
                            break
            if row['uid'] and a and b and a != b:
                absorbed_into.setdefault(b, a)

            if row['match_type'] == 'companyid - coop mutual':
                if a.startswith('GB-COOP-'):
                    coop, number = a, row['orgB_id_in_source']
                elif b.startswith('GB-COOP-'):
                    coop, number = b, row['orgA_id_in_source']
                else:
                    continue
                prev = coop_companyid.get(coop)
                if prev is not None and prev != number:
                    conflicts += 1
                    continue
                coop_companyid.setdefault(coop, number)

    return {'matched_uids': matched_uids, 'absorbed_into': absorbed_into,
            'uids_in_matches': uids_in_matches,
            'coop_companyid': coop_companyid,
            'coop_companyid_conflicts': conflicts}


# ---------------------------------------------------------------------------
# fresh-download id sets (deciding which v1.0 records are actually lost)
# ---------------------------------------------------------------------------

def _read_csv_rows(path, encoding):
    with open(path, 'r', newline='', encoding=encoding) as f:
        for row in csv.DictReader(f):
            yield row


def load_fresh_ids(raw_data_root):
    """Return {register_key: set of id_in_source} found in the fresh
    downloads on disk, applying the same inclusion filters the register's
    handler applies (so a record the register has reclassified out of scope
    counts as absent and is restored). Files this module itself wrote
    ('bootstrap' in the name) are ignored."""
    fresh = {k: set() for k in REGISTERS}

    def files(folder, patterns):
        out = []
        for p in patterns:
            out.extend(glob.glob(os.path.join(raw_data_root, folder, p)))
        return sorted(fp for fp in set(out)
                      if 'bootstrap' not in os.path.basename(fp).lower())

    for fp in files('co_ops', ['*.csv']):
        for row in _read_csv_rows(fp, 'utf-8-sig'):
            v = (row.get('CUK Organisation ID') or '').strip()
            if v:
                fresh['coops'].add(v)

    for fp in files('SocialHousingEngland', ['*.csv']):
        for row in _read_csv_rows(fp, 'utf-8-sig'):
            if (row.get('Designation') or '').strip() != 'Non-profit':
                continue
            v = (row.get('Registration number') or '').strip()
            if v:
                fresh['social_housing_england'].add(v)

    for fp in files('ScotHousingReg', ['*.csv']):
        for row in _read_csv_rows(fp, 'latin-1'):
            v = (row.get('Reg No') or '').strip()
            if v:
                fresh['scot_housing_reg'].add(v)

    for fp in files('CareInspectScot', ['MDSF_data*.csv', '*Datastore*.csv']):
        for row in _read_csv_rows(fp, 'latin-1'):
            servicetype = (row.get('ServiceType')
                           or row.get('Service Type') or '').strip()
            if servicetype != 'Voluntary or Not for Profit':
                continue
            # a UTF-8 byte-order mark read as latin-1 mangles the first
            # header, so accept any field name ENDING in CSNumber
            v = next((row[k] for k in row
                      if k and (k.endswith('CSNumber') or k == 'CaseNumber')
                      and row[k]), '').strip()
            if v:
                fresh['care_inspectorate_scot'].add(v)

    return fresh


# ---------------------------------------------------------------------------
# per-organisation detail and date selection
# ---------------------------------------------------------------------------

def _checked_date(datestr, stats):
    """Pass a dd/mm/yyyy date through unchanged; blank (and count) anything
    else so a malformed value can never poison a handler's date parse."""
    if not datestr:
        return ''
    if DATE_RE.match(datestr.strip()):
        return datestr.strip()
    stats['unparseable_dates'] += 1
    return ''


def choose_dates(spine_row, supp_rows, is_matched, absorber_row, stats):
    """(registerdate, removeddate) for the reconstructed record, dd/mm/yyyy.

    A spine row's dates may belong to a matched source (registerdate =
    earliest across sources, removeddate = latest), so for matched
    organisations the register's OWN supplementary dates are preferred:
    earliest own registration, latest own removal. See module docstring."""
    def _chronological(dates):
        parsed = []
        for d in dates:
            try:
                parsed.append((datetime.strptime(d, '%d/%m/%Y'), d))
            except (TypeError, ValueError):
                continue
        return [d for _, d in sorted(parsed)]

    own_reg = _chronological(r['registerdate'] for r in supp_rows)
    own_rem = _chronological(r['removeddate'] for r in supp_rows)

    if spine_row is None:
        regdate = own_reg[0] if own_reg else (
            absorber_row['registerdate'] if absorber_row else '')
        if not own_reg and regdate:
            stats['regdate_filled_from_absorber'] += 1
    elif is_matched and own_reg:
        regdate = own_reg[0]
        stats['regdate_own_preferred_over_spine'] += 1
    else:
        regdate = spine_row['registerdate']

    if spine_row is None:
        if own_rem:
            remdate = own_rem[-1]
        else:
            remdate = (absorber_row['removeddate'] if absorber_row else '')
            if remdate:
                stats['remdate_filled_from_absorber'] += 1
    elif own_rem and (is_matched or not spine_row['removeddate']):
        remdate = own_rem[-1]
        if not spine_row['removeddate']:
            stats['removal_recovered_from_supplementary'] += 1
        else:
            stats['remdate_own_preferred_over_spine'] += 1
    else:
        remdate = spine_row['removeddate']

    return _checked_date(regdate, stats), _checked_date(remdate, stats)


def pick_details(spine_row, supp_rows, absorber_row, stats):
    """Primary (name, fulladdress, city, postcode) for the record: the spine
    row where one exists; otherwise the first supplementary row carrying a
    name (the build wrote the organisation's own primary record first), with
    absorber fills for name/postcode blanked as identical at build time."""
    if spine_row is not None:
        return (spine_row['organisationname'], spine_row['fulladdress'],
                spine_row['city'], spine_row['postcode'])

    name = address = city = postcode = ''
    for r in supp_rows:
        if r['organisationname']:
            name = r['organisationname']
            if r['fulladdress'] or r['postcode']:
                address, city, postcode = (r['fulladdress'], r['city'],
                                           r['postcode'])
            break
    if not name and absorber_row:
        name = absorber_row['organisationname']
        stats['name_filled_from_absorber'] += 1
    if not address and not postcode:
        for r in supp_rows:
            if r['fulladdress'] or r['postcode']:
                address, city, postcode = (r['fulladdress'], r['city'],
                                           r['postcode'])
                break
    if not postcode and absorber_row and absorber_row['postcode']:
        postcode = absorber_row['postcode']
        stats['postcode_filled_from_absorber'] += 1
    return name, address, city, postcode


# ---------------------------------------------------------------------------
# register-specific row builders (one primary row per lost record)
# ---------------------------------------------------------------------------

def build_coop_row(uid, details, dates, companyid):
    name, address, city, postcode = details
    regdate, remdate = dates
    row = {f: '' for f in COOP_FIELDS}
    row.update({'CUK Organisation ID': uid[len('GB-COOP-'):],
                'Registered Number': companyid,
                'Registered Name': name,
                'Registered Street': address,
                'Registered City': city,
                'Registered Postcode': postcode,
                'Incorporation Date': regdate,
                'Dissolved Date': remdate})
    return row


def build_shpe_row(uid, details, dates):
    name, _, _, _ = details
    regdate, _ = dates
    row = {f: '' for f in SHPE_FIELDS}
    row.update({'Organisation name': name,
                'Registration number': uid[len('GB-SHPE-'):],
                'Registration date': regdate,
                'Designation': 'Non-profit'})
    return row


def build_shr_row(uid, details):
    name, _, _, _ = details
    row = {f: '' for f in SHR_FIELDS}
    row.update({'Reg No': uid[len('GB-SHR-'):],
                'Social Landlord': name})
    return row


def build_cis_row(uid, details, dates):
    name, address, city, postcode = details
    regdate, _ = dates
    row = {f: '' for f in CIS_FIELDS}
    row.update({'CSNumber': uid[len('GB-CIS-'):],
                'ServiceName': name,
                'ServiceType': 'Voluntary or Not for Profit',
                'ServiceProvider': name,
                'Address_line_1': address,
                'Service_town': city,
                'Service_Postcode': postcode,
                'DateReg': regdate})
    return row


# ---------------------------------------------------------------------------
# assembly
# ---------------------------------------------------------------------------

def reconstruct_register(key, spine_by_reg, all_spine, supp_by_reg, links,
                         fresh_ids):
    """Build the reconstructed rows for one register. Returns (rows, stats)."""
    cfg = REGISTERS[key]
    prefix = cfg['prefix']
    spine = spine_by_reg[key]
    supp = supp_by_reg.get(key, {})
    absorbed_into = links['absorbed_into']

    universe = (set(spine) | links['uids_in_matches'][key] | set(supp))
    fresh_uids = {prefix + i for i in fresh_ids[key]}
    delta = universe - fresh_uids

    stats = defaultdict(int)
    stats['universe_in_v1'] = len(universe)
    stats['in_fresh_downloads'] = len(universe & fresh_uids)
    stats['lost_records'] = len(delta)
    stats['lost_with_spine_row'] = len(delta & set(spine))

    rows = []
    for uid in sorted(delta):
        spine_row = spine.get(uid)
        supp_rows = supp.get(uid, [])
        matched = uid in links['matched_uids']
        absorber_row = None
        if spine_row is None:
            absorber_uid = absorbed_into.get(uid)
            absorber_row = all_spine.get(absorber_uid) if absorber_uid else None

        details = pick_details(spine_row, supp_rows, absorber_row, stats)
        dates = choose_dates(spine_row, supp_rows, matched, absorber_row, stats)

        if not details[0]:
            # a record no rule can ever fire on is not worth reconstructing
            # for a matches-only register; for spine-forming registers it
            # would only create a nameless organisation
            stats['skipped_nameless'] += 1
            continue

        if key == 'coops':
            companyid = links['coop_companyid'].get(uid, '')
            if companyid:
                stats['companyid_recovered'] += 1
            rows.append(build_coop_row(uid, details, dates, companyid))
        elif key == 'social_housing_england':
            rows.append(build_shpe_row(uid, details, dates))
        elif key == 'scot_housing_reg':
            rows.append(build_shr_row(uid, details))
        else:
            rows.append(build_cis_row(uid, details, dates))

    stats['rows_written'] = len(rows)
    return rows, dict(stats)


def _output_path(key, raw_data_root, as_of):
    cfg = REGISTERS[key]
    dt = datetime.strptime(as_of, '%m/%Y')
    filename = cfg['filename'].format(yyyy=dt.strftime('%Y'),
                                      mm=dt.strftime('%m'),
                                      monyyyy=dt.strftime('%b%Y'))
    return os.path.join(raw_data_root, cfg['folder'], filename)


def write_register_file(rows, path, fields, encoding, stats):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', newline='', encoding=encoding,
              errors='replace') as f:
        writer = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)
    # count values the target encoding could not represent (written as '?')
    for row in rows:
        for v in row.values():
            try:
                v.encode(encoding)
            except UnicodeEncodeError:
                stats['values_transliterated_for_encoding'] += 1


def write_lost_register_files(spine_csv, supplementary_csv, matches_csv,
                              raw_data_root, as_of=AS_OF_ITERATION):
    """Reconstruct and write the four lost-register snapshot files under
    raw_data_root. Returns {register_key: stats}. Refuses to overwrite an
    existing output (delete the file first to force regeneration)."""
    paths = {key: _output_path(key, raw_data_root, as_of) for key in REGISTERS}
    existing = [p for p in paths.values() if os.path.exists(p)]
    if existing:
        raise RuntimeError(
            'bootstrap-lost-registers: output already exists: %s. This step '
            'runs once; its outputs are permanent input artifacts. Delete '
            'the file(s) first to force regeneration.' % ', '.join(existing))

    links = load_matches(matches_csv)
    spine_by_reg, all_spine = load_spine(spine_csv)
    supp_by_reg = load_supplementary(supplementary_csv)
    fresh_ids = load_fresh_ids(raw_data_root)

    all_stats = {}
    for key, cfg in REGISTERS.items():
        rows, stats = reconstruct_register(key, spine_by_reg, all_spine,
                                           supp_by_reg, links, fresh_ids)
        write_register_file(rows, paths[key], cfg['fields'],
                            cfg['encoding'], stats)
        stats['output'] = paths[key]
        all_stats[key] = stats
        print('%s: %d of %d v1.0 organisations absent from fresh downloads; '
              '%d rows -> %s' % (cfg['register'], stats['lost_records'],
                                 stats['universe_in_v1'],
                                 stats['rows_written'], paths[key]))
        for k in sorted(stats):
            if k not in ('output', 'rows_written', 'lost_records',
                         'universe_in_v1'):
                print('    %s: %s' % (k, stats[k]))
    if links['coop_companyid_conflicts']:
        print('WARNING: %d co-ops had conflicting society numbers across '
              'their v1.0 match rows (first kept)'
              % links['coop_companyid_conflicts'])
    return all_stats


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(
        description='Reconstruct the lost co-op/housing/care register '
                    'snapshots from a published Spine release.')
    p.add_argument('spine_csv')
    p.add_argument('supplementary_csv')
    p.add_argument('matches_csv')
    p.add_argument('raw_data_root', help='destination, typically ../raw_data')
    p.add_argument('--as-of', default=AS_OF_ITERATION,
                   help='currency of the published release, mm/yyyy '
                        '(default %s)' % AS_OF_ITERATION)
    args = p.parse_args()
    write_lost_register_files(args.spine_csv, args.supplementary_csv,
                              args.matches_csv, args.raw_data_root,
                              as_of=args.as_of)
