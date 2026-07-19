"""Reconstruct the three lost charity-regulator "base" files from the
published Spine v1.0 release.

Why this module exists
----------------------
The pipeline step ``cli.py process-charity-source {ccew,oscr,ccni}``
(handler/preprocess_charity_regulators.py) requires three historical files
that carried each regulator's consolidated 2001-2023 history:

    ../raw_data/ccew/ccew_spine_public.csv
    ../raw_data/oscr/oscr_spine_public.csv
    ../raw_data/ccni/ccni_spine.csv

Those files are lost and cannot be rebuilt from public sources (see
RUNBOOK.md section 3.1).  The published Spine v1.0 release, however, was
built FROM them, and its three files together retain almost all of their
content:

    TSCS_spine.spine.csv          - one row per organisation: current/primary
                                    name, address, registration and removal
                                    dates, with source_register attribution.
    TSCS_spine.supplementary.csv  - the historical name/address/date variants
                                    per organisation, each row attributed to
                                    the register it came from and keyed by the
                                    organisation's own uid (this includes
                                    organisations that were merged into
                                    another organisation during linkage).
    TSCS_spine.matches.csv        - the cross-register links, which retain the
                                    company numbers of charity-company pairs
                                    and the historical OSCR 2012 linkage.

This module reads those three published files and writes replacement base
files with EXACTLY the column layout and value conventions that
``process_ccew`` / ``process_oscr`` / ``process_ccni`` expect (the field
lists are imported from handler.preprocess_charity_regulators so the schema
can never drift).  Future Spine versions are then built from these
reconstructed bases plus fresh register downloads.

Value conventions reproduced
----------------------------
* Register numbers are recovered from the uid (GB-CHC-x, GB-SC-x, GB-NIC-x).
* Dates are written as ddMonYYYY (e.g. ``17Mar1961``), the format the
  original Stata-exported bases used and the only format CCEWDataHandler
  accepts.
* Each organisation gets one "primary" row carrying its spine (current)
  details, plus one row per supplementary record carrying historical
  variants.  Primary rows are tagged so the downstream handlers select them
  until a fresher register download supersedes them:
    - CCEW: primary_name = primary_address = '1' and iteration = AS_OF;
      variant rows have blank flags and blank iteration (treated as oldest).
    - OSCR: name_origin = '<AS_OF> Name' and iteration = AS_OF on the
      primary row; blanks on variant rows.
    - CCNI: process_ccni force-stamps every base row iteration '01/2024',
      so primary selection between base rows cannot be controlled.  For
      still-registered organisations that is harmless in a real build (the
      next register download always wins the recency contest), but until a
      fresh CCNI download is present, which of an organisation's recorded
      names/addresses becomes primary is arbitrary (v1.0 validation: ~19%
      of CCNI organisations surface a different - but always genuine,
      recorded - name than the published spine).  For REMOVED organisations
      nothing would ever supersede an arbitrary pick, so we write a single
      consolidated row plus date-only variant rows, and deliberately drop
      name/address variants (see "losses").
* CCEW linked-charity ids: base rows use the plain register number (no
  -0/-1 suffix), exactly as the original base did.  The '-0' umbrella
  convention appears only in fresh downloads; the handler then treats these
  plain-number rows as the umbrella's historical record (check_for_old_data).
* AS_OF (default '01/2026') is the currency of the published v1.0 details -
  the January 2026 build.  Pass a different value if reconstructing from a
  different release.

Registration / removal date logic (cross-register caution)
----------------------------------------------------------
At spine build time an organisation's registerdate becomes the EARLIEST
date across all matched sources and its removeddate the LATEST (or is
blanked when a matched company is still live), with the displaced own date
pushed into the supplementary file under the organisation's own uid and
register.  A spine row's dates may therefore belong to a matched Companies
House / other-register record rather than to this regulator.  Empirically
(v1.0 CCEW): organisations WITH cross-source matches whose supplementary
carries own-register dates show a median spine-vs-supplementary gap of ~8
months (the classic incorporate-then-register-as-charity lag => the spine
date is usually the company's), while unmatched organisations show
multi-decade gaps (genuine historical variants).  Rules applied per
organisation:

* registerdate: if the organisation has any match AND own-register
  supplementary registration dates exist, the spine date is treated as
  possibly foreign and ONLY the supplementary dates are written (the
  handler then picks the earliest of them).  Otherwise the spine date is
  written on the primary row and supplementary dates become variant rows.
* removeddate: if the spine removal is blank but the supplementary carries
  an own-register removal (an organisation removed from this register while
  a matched company lived on), the supplementary removal is written - this
  RECOVERS removals the published spine suppressed.  If both exist and the
  organisation is matched, the supplementary (own) removal is preferred.
  Unmatched organisations keep the spine removal plus variants.
* Organisations absorbed into another organisation during linkage (present
  only in supplementary/matches, not in the spine): primary details come
  from their first supplementary row; a missing name/registration date is
  filled from the absorbing organisation's spine row (the build blanked
  fields that were identical to the absorber's, so the absorber's value is
  the best - usually exact - estimate).  A missing removal is filled from
  the absorber only when the absorber itself is removed.

What is recovered from the matches file
---------------------------------------
* CCEW/CCNI companyid: from 'companyid - id_in_source' match rows, else a
  unique ftc-linked GB-COH partner.
* OSCR charitynumber_2012 / companyid1..3_2012: from 'oscr' match rows
  (these regenerate ../raw_data/oscr.linkage.csv on the next
  process-charity-source run).
* OSCR crossborder flag: set to 1 for Scottish charities linked to a
  GB-CHC organisation (ftc / oscr / name-crossborder match).

Permanent losses (cannot be recovered from the published release)
-----------------------------------------------------------------
Each is filled with the neutral value the downstream handler treats as
"no special handling":

* CCEW cqc_reg ('should also be CQC-registered') -> '0' everywhere.  The
  v1.0 matches contain no CQC match rows to recover it from.  Consequence:
  the 'name - cqc' match rule will not fire for base-only organisations
  (the broader 'name - care' CQC->CCEW rule is unaffected).
* CCEW per-snapshot origin years (name_origin/address_origin/regdate_origin/
  remdate_origin = which of the 2001-2023 snapshots a variant came from):
  unknown for variants -> blank (the handlers never used them).  Variant
  rows also lose their snapshot iteration tag -> blank = "oldest".
* CCEW linked-charity substructure (which -1/-2 sub-charity a name belonged
  to): flattened to name variants of the parent number, as the original
  base itself did for pre-2011 snapshots.
* OSCR name_origin provenance text ('Known As', 'Former Name', '2012 Alt
  Name'...) for historical names -> blank (still never primary, exactly as
  before; only the human-readable provenance is lost).
* OSCR 2012 linkage rows whose counterpart never entered the spine (they
  produced no match row) - unrecoverable.
* OSCR localauthority / addressline2-8 split: the published fulladdress is
  a single consolidated string -> written to addressline1; localauthority
  blank.  The handler re-consolidates to the same fulladdress.
* CCNI name/address variants of REMOVED organisations (472 organisations in
  v1.0): dropped so that the forced shared iteration cannot make an old
  variant the primary name (variants remain available to researchers in the
  published v1.0 supplementary file).  Removal DATES are kept.
* CCNI companyid where no ftc link exists -> blank.
* Any date the spine blanked on both sides (identical values are blanked in
  the supplementary during the build, so a value visible nowhere was equal
  to the surviving one - no information is actually lost in that case).

Validation against the published v1.0 release (July 2026)
---------------------------------------------------------
The three reconstructed bases were run through ``process-charity-source``
and ``process-source`` with no fresh downloads present, and the resulting
sub-spine files compared to the published v1.0 subsets:

* Coverage: 100.0000% of published organisations on all three registers
  (CCEW 350,640/350,640; OSCR 53,342/53,342; CCNI 8,243/8,243; 0 missing).
  Additionally 5,364 CCEW and 1,421 OSCR organisations that were merged
  into another organisation during the original linkage are recovered as
  organisations of their own, so the next build re-merges them identically.
* Names: 100% identical for CCEW and OSCR.  CCNI 81.1% identical; every
  mismatch is a recorded name variant of the same organisation (the shared
  base iteration makes the pick arbitrary until a fresh download arrives).
* Dates: every difference falls into the designed categories above -
  regulator-own registration date preferred over a matched source's
  (CCEW 39,306; OSCR 2,461; CCNI 632), suppressed removals recovered
  (CCEW 1,216; OSCR 551; CCNI 18), regulator-own removal preferred
  (CCEW 902; OSCR 65; CCNI 11).  Zero unexplained date differences.
* Addresses/postcodes: 99.9%+ identical for CCEW, 99.8% for OSCR (the
  remainder are historical-variant picks for organisations with no current
  address, plus comma-spacing normalisation noise); CCNI ~91% with the
  remainder again recorded variants of the same organisation.

Usage
-----
Standard invocation, from the repo root (same pattern as the other pipeline
steps; see RUNBOOK.md section 3.1):

    python cli.py bootstrap-base-files SPINE.csv SUPPLEMENTARY.csv MATCHES.csv \
        -o ../raw_data [--as-of mm/yyyy]

then run ``python cli.py process-charity-source {ccni,oscr,ccew}`` as normal.
Also callable as a module (``python -m spine.bootstrap_base_files SPINE SUPP
MATCHES OUT_RAW_DATA_DIR``) or from Python:

    from spine.bootstrap_base_files import write_base_files
    stats = write_base_files(spine_csv, supplementary_csv, matches_csv,
                             raw_data_root='../raw_data')
"""

import csv
import os
from collections import defaultdict
from datetime import datetime

from handler.preprocess_charity_regulators import ccew_fields, oscr_fields, ccni_fields

# currency of the published v1.0 details (January 2026 build) in the
# 'mm/yyyy' iteration format used throughout the pipeline
AS_OF_ITERATION = '01/2026'

CCEW_REGISTER = 'Charity Commission for England and Wales'
OSCR_REGISTER = 'Scottish Charity Register'
CCNI_REGISTER = 'Charity Commission for Northern Ireland'

REGULATORS = {
    'ccew': {'prefix': 'GB-CHC-', 'register': CCEW_REGISTER, 'source': 'CCEW',
             'fields': ccew_fields, 'relpath': os.path.join('ccew', 'ccew_spine_public.csv')},
    'oscr': {'prefix': 'GB-SC-', 'register': OSCR_REGISTER, 'source': 'OSCR',
             'fields': oscr_fields, 'relpath': os.path.join('oscr', 'oscr_spine_public.csv')},
    'ccni': {'prefix': 'GB-NIC-', 'register': CCNI_REGISTER, 'source': 'CCNI',
             'fields': ccni_fields, 'relpath': os.path.join('ccni', 'ccni_spine.csv')},
}


def spine_date_to_base(datestr):
    """Convert a published-spine date (dd/mm/yyyy) to the base-file format
    ddMonYYYY (e.g. '17/03/1961' -> '17Mar1961').  Returns '' for blank or
    unparseable input (the caller counts the latter)."""
    if not datestr:
        return ''
    try:
        return datetime.strptime(datestr.strip(), '%d/%m/%Y').strftime('%d%b%Y')
    except ValueError:
        return None  # caller records and skips


def _prefix_of(uid):
    parts = uid.split('-')
    return '-'.join(parts[:2]) + '-' if len(parts) > 2 else ''


# ---------------------------------------------------------------------------
# loading the three published files
# ---------------------------------------------------------------------------

def load_matches(matches_csv):
    """One pass over the published matches file.

    Returns a dict with:
      matched_uids   : endpoints of real consolidation rows (uid non-blank).
                       Association-only rows (uid blank) do not merge source
                       data, so their endpoints' spine dates remain their own
                       regulator dates.
      absorbed_into  : orgB_uid -> orgA_uid for real (uid non-blank) matches;
                       organisations absent from the spine main file live here
      companyid      : charity uid -> company number ('companyid -
                       id_in_source' rows first, else a unique ftc GB-COH
                       partner)
      sc_2012        : GB-SC uid -> {'sc': [...], 'coh': [...]} from 'oscr'
                       match rows (regenerates the OSCR 2012 linkage)
      crossborder_sc : GB-SC uids linked to a GB-CHC organisation
    """
    matched_uids = set()
    absorbed_into = {}
    companyid = {}
    ftc_coh_partners = defaultdict(set)
    sc_2012 = defaultdict(lambda: {'sc': [], 'coh': []})
    crossborder_sc = set()

    with open(matches_csv, 'r', newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            a, b = row['orgA_uid'], row['orgB_uid']
            mt = row['match_type']
            if row['uid'] and a and b and a != b:
                matched_uids.update((a, b))
                absorbed_into.setdefault(b, a)

            pa, pb = _prefix_of(a), _prefix_of(b)

            if mt == 'companyid - id_in_source' and pa in ('GB-CHC-', 'GB-NIC-') and pb == 'GB-COH-':
                companyid.setdefault(a, row['orgB_id_in_source'])

            if mt == 'ftc':
                if pa in ('GB-CHC-', 'GB-NIC-') and pb == 'GB-COH-':
                    ftc_coh_partners[a].add(row['orgB_id_in_source'])
                elif pb in ('GB-CHC-', 'GB-NIC-') and pa == 'GB-COH-':
                    ftc_coh_partners[b].add(row['orgA_id_in_source'])

            if mt == 'oscr':
                if pa == 'GB-SC-' and pb == 'GB-COH-':
                    sc_2012[a]['coh'].append(row['orgB_id_in_source'])
                elif pa == 'GB-SC-' and pb == 'GB-SC-':
                    sc_2012[a]['sc'].append(row['orgB_id_in_source'])
                elif pb == 'GB-SC-' and pa == 'GB-COH-':
                    sc_2012[b]['coh'].append(row['orgA_id_in_source'])

            if mt in ('ftc', 'oscr', 'name - crossborder') and {pa, pb} == {'GB-CHC-', 'GB-SC-'}:
                crossborder_sc.add(a if pa == 'GB-SC-' else b)

    # ftc fallback for company numbers: only when unambiguous
    for uid, partners in ftc_coh_partners.items():
        if uid not in companyid and len(partners) == 1:
            companyid[uid] = next(iter(partners))

    return {'matched_uids': matched_uids, 'absorbed_into': absorbed_into,
            'companyid': companyid, 'sc_2012': dict(sc_2012),
            'crossborder_sc': crossborder_sc}


def load_spine(spine_csv):
    """One pass over the published spine.  Returns {regulator: {uid: row}}
    with only the fields the reconstruction needs."""
    by_reg = {k: {} for k in REGULATORS}
    wanted = {v['register']: k for k, v in REGULATORS.items()}
    with open(spine_csv, 'r', newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            reg = wanted.get(row['source_register'])
            if reg is None:
                continue
            if not row['uid'].startswith(REGULATORS[reg]['prefix']):
                continue
            by_reg[reg][row['uid']] = {
                'organisationname': row['organisationname'],
                'fulladdress': row['fulladdress'],
                'city': row['city'],
                'postcode': row['postcode'],
                'registerdate': row['registerdate'],
                'removeddate': row['removeddate'],
            }
    return by_reg


def load_supplementary(supplementary_csv):
    """One pass over the published supplementary file.  Returns
    {regulator: {uid: [rows in file order]}} keeping only rows attributed to
    the regulator's own register (rows for the same uid attributed to other
    registers belong to those registers' reconstructions)."""
    by_reg = {k: defaultdict(list) for k in REGULATORS}
    wanted = {v['register']: k for k, v in REGULATORS.items()}
    with open(supplementary_csv, 'r', newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            reg = wanted.get(row['source_register'])
            if reg is None:
                continue
            if not row['uid'].startswith(REGULATORS[reg]['prefix']):
                continue
            by_reg[reg][row['uid']].append({
                'organisationname': row['organisationname'],
                'fulladdress': row['fulladdress'],
                'city': row['city'],
                'postcode': row['postcode'],
                'registerdate': row['registerdate'],
                'removeddate': row['removeddate'],
            })
    return {k: dict(v) for k, v in by_reg.items()}


# ---------------------------------------------------------------------------
# per-organisation date selection (shared by all three regulators)
# ---------------------------------------------------------------------------

def choose_primary_dates(spine_row, supp_rows, is_matched, absorber_row, stats):
    """Return (registerdate, removeddate) for the primary base row, both in
    dd/mm/yyyy (conversion to ddMonYYYY happens at write time).  Blank means
    'no date on the primary row' - the organisation's supplementary variant
    rows still carry the regulator's own dates and the downstream handler
    consolidates dates across ALL rows of an organisation, so a blank here
    never loses a date that appears on a variant row.
    """
    own_reg = [r['registerdate'] for r in supp_rows if r['registerdate']]
    own_rem = [r['removeddate'] for r in supp_rows if r['removeddate']]

    # ---- registration ----
    if spine_row is None:
        # absorbed organisation: no spine row of its own
        if own_reg:
            regdate = ''  # variants carry the own dates
        else:
            regdate = absorber_row['registerdate'] if absorber_row else ''
            if regdate:
                stats['regdate_filled_from_absorber'] += 1
    elif is_matched and own_reg:
        # spine date may be a matched source's (e.g. company incorporation):
        # prefer the regulator's own dates, which live on the variant rows
        regdate = ''
        stats['regdate_spine_date_set_aside'] += 1
    else:
        regdate = spine_row['registerdate']

    # ---- removal ----
    if spine_row is None:
        if own_rem:
            remdate = ''
        else:
            remdate = absorber_row['removeddate'] if absorber_row else ''
            if remdate:
                stats['remdate_filled_from_absorber'] += 1
    else:
        spine_rem = spine_row['removeddate']
        if not spine_rem:
            remdate = ''  # any own removal is on the variant rows (recovery)
            if own_rem:
                stats['removal_recovered_from_supplementary'] += 1
        elif is_matched and own_rem:
            remdate = ''  # prefer the regulator's own removal (variant rows)
            stats['remdate_spine_date_set_aside'] += 1
        else:
            remdate = spine_rem

    return regdate, remdate


def _pick_primary_details(supp_rows, absorber_row, stats):
    """Primary name/address for an absorbed organisation: the first
    supplementary row is the organisation's own primary record (the build
    wrote it first); fall back to the first row carrying each field group,
    then to the absorbing organisation's spine row."""
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
        # identical values were blanked at build time, so the absorber's
        # postcode is the best estimate for the primary address
        postcode = postcode or absorber_row['postcode']
        stats['postcode_filled_from_absorber'] += 1
    return name, address, city, postcode


# ---------------------------------------------------------------------------
# regulator-specific row builders
# ---------------------------------------------------------------------------

def _convert(datestr, stats):
    if not datestr:
        return ''
    out = spine_date_to_base(datestr)
    if out is None:
        stats['unparseable_dates'] += 1
        return ''
    return out


def _preserve_displaced_spine_dates(rows, blank_row, spine_row,
                                    selected_regdate, selected_remdate, stats):
    """Keep published main-file dates that date selection moved off primary.

    A published spine date may have been consolidated from another source,
    which is why ``choose_primary_dates`` can prefer regulator-attributed
    supplementary dates for a matched organisation.  Discarding the main
    value entirely is nevertheless irreversible and caused old registration
    periods to disappear on a rebuild.  Write each displaced value as its own
    untagged historical row; a fresh ``-0`` regulator row can then remain the
    current primary while the prior value survives as a supplementary variant.
    """
    if spine_row is None:
        return

    for field, selected in (
        ('registerdate', selected_regdate),
        ('removeddate', selected_remdate),
    ):
        value = spine_row[field]
        if not value or value == selected:
            continue
        converted = _convert(value, stats)
        if not converted or any(row[field] == converted for row in rows):
            continue
        variant = blank_row()
        variant[field] = converted
        rows.append(variant)
        stats[f'{field}_spine_date_preserved_as_variant'] += 1


def build_ccew_rows(uid, spine_row, supp_rows, matched, companyid, absorber_row,
                    stats, as_of=AS_OF_ITERATION):
    number = uid[len('GB-CHC-'):]
    regdate, remdate = choose_primary_dates(spine_row, supp_rows, matched, absorber_row, stats)

    def blank():
        row = {f: '' for f in ccew_fields}
        row.update(uid=uid, charitynumber=number, source='CCEW', cqc_reg='0')
        return row

    primary = blank()
    if spine_row is not None:
        name, addr, city, pc = (spine_row['organisationname'], spine_row['fulladdress'],
                                spine_row['city'], spine_row['postcode'])
    else:
        name, addr, city, pc = _pick_primary_details(supp_rows, absorber_row, stats)
    primary.update(organisationname=name, addressline1=addr, city=city, postcode=pc,
                   registerdate=_convert(regdate, stats), removeddate=_convert(remdate, stats),
                   companyid=companyid, primary_name='1', primary_address='1',
                   iteration=as_of, name_origin=as_of, address_origin=as_of,
                   regdate_origin=as_of, remdate_origin=as_of)
    rows = [primary]

    for r in supp_rows:
        v = blank()
        v.update(organisationname=r['organisationname'], addressline1=r['fulladdress'],
                 city=r['city'], postcode=r['postcode'],
                 registerdate=_convert(r['registerdate'], stats),
                 removeddate=_convert(r['removeddate'], stats))
        if any(v[f] for f in ('organisationname', 'addressline1', 'city', 'postcode',
                              'registerdate', 'removeddate')):
            rows.append(v)
    _preserve_displaced_spine_dates(
        rows, blank, spine_row, regdate, remdate, stats
    )
    return rows


def build_oscr_rows(uid, spine_row, supp_rows, matched, links_2012, crossborder,
                    absorber_row, stats, as_of=AS_OF_ITERATION):
    number = uid[len('GB-SC-'):]
    regdate, remdate = choose_primary_dates(spine_row, supp_rows, matched, absorber_row, stats)

    def blank():
        row = {f: '' for f in oscr_fields}
        row.update(uid=uid, charitynumber=number, source='OSCR', crossborder='0')
        return row

    primary = blank()
    if spine_row is not None:
        name, addr, city, pc = (spine_row['organisationname'], spine_row['fulladdress'],
                                spine_row['city'], spine_row['postcode'])
    else:
        name, addr, city, pc = _pick_primary_details(supp_rows, absorber_row, stats)
    primary.update(organisationname=name, addressline1=addr, city=city, postcode=pc,
                   registerdate=_convert(regdate, stats), removeddate=_convert(remdate, stats),
                   name_origin='%s Name' % as_of, iteration=as_of,
                   crossborder='1' if crossborder else '0')
    if links_2012:
        sc = links_2012.get('sc') or []
        coh = links_2012.get('coh') or []
        if sc:
            primary['charitynumber_2012'] = sc[0]
        for i, c in enumerate(coh[:3]):
            primary['companyid%d_2012' % (i + 1)] = c
    rows = [primary]

    for r in supp_rows:
        v = blank()
        v.update(organisationname=r['organisationname'], addressline1=r['fulladdress'],
                 city=r['city'], postcode=r['postcode'],
                 registerdate=_convert(r['registerdate'], stats),
                 removeddate=_convert(r['removeddate'], stats))
        if any(v[f] for f in ('organisationname', 'addressline1', 'city', 'postcode',
                              'registerdate', 'removeddate')):
            rows.append(v)
    _preserve_displaced_spine_dates(
        rows, blank, spine_row, regdate, remdate, stats
    )
    return rows


def _ccni_address(fulladdress, postcode):
    """process_ccni re-extracts the postcode from the LAST comma-separated
    component of the address string, so the postcode must be appended."""
    if fulladdress and postcode:
        return '%s, %s' % (fulladdress, postcode)
    return fulladdress or postcode


def build_ccni_rows(uid, spine_row, supp_rows, matched, companyid, absorber_row, stats):
    number = uid[len('GB-NIC-'):]
    regdate, remdate = choose_primary_dates(spine_row, supp_rows, matched, absorber_row, stats)

    own_rem = any(r['removeddate'] for r in supp_rows)
    removed = bool(remdate) or (spine_row is not None and spine_row['removeddate']) or own_rem

    def blank():
        row = {f: '' for f in ccni_fields}
        row.update(uid=uid, charitynumber=number, source='CCNI')
        return row

    primary = blank()
    if spine_row is not None:
        name, addr, city, pc = (spine_row['organisationname'], spine_row['fulladdress'],
                                spine_row['city'], spine_row['postcode'])
    else:
        name, addr, city, pc = _pick_primary_details(supp_rows, absorber_row, stats)
    primary.update(organisationname=name, address=_ccni_address(addr, pc), city=city,
                   postcode=pc, companyid=companyid,
                   registerdate=_convert(regdate, stats), removeddate=_convert(remdate, stats))
    rows = [primary]

    for r in supp_rows:
        has_details = r['organisationname'] or r['fulladdress'] or r['postcode']
        has_dates = r['registerdate'] or r['removeddate']
        if removed and has_details:
            # process_ccni stamps all base rows with the same iteration, so a
            # variant name/address could arbitrarily beat the primary for an
            # organisation that never reappears in a download.  Keep only the
            # dates for removed organisations (variants stay available in the
            # published v1.0 supplementary file).
            stats['ccni_removed_variant_rows_dropped'] += 1
            if not has_dates:
                continue
            v = blank()
            v.update(registerdate=_convert(r['registerdate'], stats),
                     removeddate=_convert(r['removeddate'], stats))
        else:
            v = blank()
            v.update(organisationname=r['organisationname'],
                     address=_ccni_address(r['fulladdress'], r['postcode']),
                     city=r['city'], postcode=r['postcode'],
                     registerdate=_convert(r['registerdate'], stats),
                     removeddate=_convert(r['removeddate'], stats))
        if any(v[f] for f in ('organisationname', 'address', 'city', 'postcode',
                              'registerdate', 'removeddate')):
            rows.append(v)
    _preserve_displaced_spine_dates(
        rows, blank, spine_row, regdate, remdate, stats
    )
    return rows


# ---------------------------------------------------------------------------
# assembly
# ---------------------------------------------------------------------------

def reconstruct_regulator(regulator, spine_by_reg, supp_by_reg, links,
                          as_of=AS_OF_ITERATION):
    """Build the full list of base-file rows for one regulator.
    Returns (rows, stats)."""
    cfg = REGULATORS[regulator]
    prefix = cfg['prefix']
    spine = spine_by_reg[regulator]
    supp = supp_by_reg.get(regulator, {})
    matched_uids = links['matched_uids']
    absorbed_into = links['absorbed_into']
    all_spine = {}
    for rows in spine_by_reg.values():
        all_spine.update(rows)

    stats = defaultdict(int)

    # the universe: organisations in the spine main file, plus organisations
    # absorbed into another organisation (present in supplementary/matches)
    uids = set(spine)
    absorbed = {u for u in absorbed_into if u.startswith(prefix) and u not in uids}
    extra_from_supp = {u for u in supp if u not in uids and u not in absorbed}
    stats['orgs_from_spine'] = len(uids)
    stats['orgs_absorbed_recovered'] = len(absorbed)
    stats['orgs_supp_only'] = len(extra_from_supp)  # expected 0

    rows_out = []
    for uid in sorted(uids | absorbed | extra_from_supp):
        spine_row = spine.get(uid)
        supp_rows = supp.get(uid, [])
        matched = uid in matched_uids
        absorber_row = None
        if spine_row is None:
            absorber_uid = absorbed_into.get(uid)
            absorber_row = all_spine.get(absorber_uid) if absorber_uid else None

        if regulator == 'ccew':
            rows = build_ccew_rows(uid, spine_row, supp_rows, matched,
                                   links['companyid'].get(uid, ''), absorber_row,
                                   stats, as_of)
        elif regulator == 'oscr':
            rows = build_oscr_rows(uid, spine_row, supp_rows, matched,
                                   links['sc_2012'].get(uid), uid in links['crossborder_sc'],
                                   absorber_row, stats, as_of)
        else:
            rows = build_ccni_rows(uid, spine_row, supp_rows, matched,
                                   links['companyid'].get(uid, ''), absorber_row, stats)
        rows_out.extend(rows)

    stats['rows_written'] = len(rows_out)
    return rows_out, dict(stats)


def write_base_file(rows, path, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)


def write_base_files(spine_csv, supplementary_csv, matches_csv, raw_data_root,
                     as_of=AS_OF_ITERATION):
    """Reconstruct and write all three base files under raw_data_root
    (typically '../raw_data').  Returns {regulator: stats}."""
    links = load_matches(matches_csv)
    spine_by_reg = load_spine(spine_csv)
    supp_by_reg = load_supplementary(supplementary_csv)

    all_stats = {}
    for regulator, cfg in REGULATORS.items():
        rows, stats = reconstruct_regulator(regulator, spine_by_reg, supp_by_reg,
                                            links, as_of)
        path = os.path.join(raw_data_root, cfg['relpath'])
        write_base_file(rows, path, cfg['fields'])
        stats['output'] = path
        all_stats[regulator] = stats
        print('%s: %d organisations (%d from spine, %d recovered from merges), '
              '%d rows -> %s' % (regulator, stats['orgs_from_spine'] +
                                 stats['orgs_absorbed_recovered'] + stats['orgs_supp_only'],
                                 stats['orgs_from_spine'], stats['orgs_absorbed_recovered'],
                                 stats['rows_written'], path))
        for k in sorted(stats):
            if k not in ('output', 'rows_written', 'orgs_from_spine',
                         'orgs_absorbed_recovered', 'orgs_supp_only'):
                print('    %s: %s' % (k, stats[k]))
    return all_stats


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description='Reconstruct the charity-regulator '
                                'base files from a published Spine release.')
    p.add_argument('spine_csv')
    p.add_argument('supplementary_csv')
    p.add_argument('matches_csv')
    p.add_argument('raw_data_root', help="destination, typically ../raw_data")
    p.add_argument('--as-of', default=AS_OF_ITERATION,
                   help="currency of the published release, mm/yyyy (default %s)" % AS_OF_ITERATION)
    args = p.parse_args()
    write_base_files(args.spine_csv, args.supplementary_csv, args.matches_csv,
                     args.raw_data_root, as_of=args.as_of)
