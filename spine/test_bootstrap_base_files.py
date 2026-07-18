# Tests for spine/bootstrap_base_files.py - reconstruction of the three
# lost charity-regulator base files from a published Spine release.
# All fixtures are tiny synthetic CSVs written to tmp_path; no real data
# files are read. The full-scale validation against the published v1.0
# release is documented in RUNBOOK.md section 3.1.

import csv
import os

import pytest

from handler.ccew import CCEWDataHandler
from handler.oscr import OSCRDataHandler
from handler.preprocess_charity_regulators import (
    ccew_fields, ccni_fields, oscr_fields,
    process_ccew, process_ccni, process_oscr,
)
from spine.bootstrap_base_files import (
    AS_OF_ITERATION,
    build_ccew_rows,
    build_ccni_rows,
    build_oscr_rows,
    choose_primary_dates,
    load_matches,
    load_spine,
    load_supplementary,
    spine_date_to_base,
    write_base_files,
)

from collections import defaultdict


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _write_csv(path, fieldnames, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, restval='')
        w.writeheader()
        w.writerows(rows)


SPINE_FIELDS = ['uid', 'organisationname', 'normalisedname', 'fulladdress',
                'city', 'postcode', 'registerdate', 'removeddate',
                'source_register', 'is_cic', 'cso_type', 'cso_subtype']
SUPP_FIELDS = ['uid', 'organisationname', 'normalisedname', 'fulladdress',
               'city', 'postcode', 'registerdate', 'removeddate',
               'source_register', 'id_in_source']
MATCH_FIELDS = ['uid', 'orgA_id_in_source', 'orgA_source', 'orgA_uid',
                'orgB_id_in_source', 'orgB_source', 'orgB_uid', 'match_type']

CCEW_REG = 'Charity Commission for England and Wales'
OSCR_REG = 'Scottish Charity Register'
CCNI_REG = 'Charity Commission for Northern Ireland'


def make_published_release(tmp_path, bulk_oscr_orgs=0):
    """A miniature published release: spine + supplementary + matches.

    bulk_oscr_orgs adds N extra Scottish charities, each with two 2012
    company links. process_oscr's linkage deduplication re-reads the linkage
    file while its write handle is still open and buffered, which only works
    once a few hundred rows have been flushed - real base files are far past
    that point, tiny fixtures are not."""
    spine_rows = [
        # unmatched CCEW org with a name variant and a regdate variant
        dict(uid='GB-CHC-200001', organisationname='ALPHA TRUST',
             fulladdress='1 HIGH STREET', city='LONDON', postcode='E1 6AN',
             registerdate='17/03/1961', removeddate='', source_register=CCEW_REG),
        # CCEW org matched to a company; spine regdate may be the company's
        dict(uid='GB-CHC-200002', organisationname='BETA FOUNDATION',
             fulladdress='2 LOW ROAD', city='LEEDS', postcode='LS1 1AA',
             registerdate='05/05/1990', removeddate='', source_register=CCEW_REG),
        # CCEW org whose removal was suppressed in the spine (matched company
        # lived on) but survives in the supplementary file
        dict(uid='GB-CHC-200003', organisationname='DELTA SOCIETY',
             fulladdress='3 MID LANE', city='YORK', postcode='YO1 7HH',
             registerdate='01/06/1975', removeddate='', source_register=CCEW_REG),
        # CCEW org that absorbed another during linkage
        dict(uid='GB-CHC-200005', organisationname='EPSILON UNITED',
             fulladdress='5 TOP WAY', city='BATH', postcode='BA1 1AA',
             registerdate='01/01/1980', removeddate='', source_register=CCEW_REG),
        # OSCR org, cross-border, with 2012 linkage
        dict(uid='GB-SC-SC000001', organisationname='SCOT AID',
             fulladdress='9 ROYAL MILE', city='EDINBURGH', postcode='EH1 1AA',
             registerdate='26/06/1986', removeddate='', source_register=OSCR_REG),
        # CCNI live org and CCNI removed org
        dict(uid='GB-NIC-100001', organisationname='ULSTER HELP',
             fulladdress='UNIT 5, SOME ROAD', city='BELFAST', postcode='BT1 1AA',
             registerdate='02/02/2015', removeddate='', source_register=CCNI_REG),
        dict(uid='GB-NIC-100002', organisationname='GONE CHARITY',
             fulladdress='6 OLD STREET', city='DERRY', postcode='BT48 6AA',
             registerdate='03/03/2016', removeddate='03/04/2019', source_register=CCNI_REG),
        # a Companies House row: must be ignored by the reconstruction
        dict(uid='GB-COH-00000100', organisationname='BETA FOUNDATION LTD',
             fulladdress='2 LOW ROAD', city='LEEDS', postcode='LS1 1AA',
             registerdate='05/05/1990', removeddate='', source_register='Companies House'),
    ]
    supp_rows = [
        # name + regdate variants for the unmatched CCEW org
        dict(uid='GB-CHC-200001', organisationname='ALPHA CHARITY', source_register=CCEW_REG),
        dict(uid='GB-CHC-200001', registerdate='01/01/1970', source_register=CCEW_REG),
        # a row for the same org attributed to another register: must be ignored
        dict(uid='GB-CHC-200001', registerdate='09/09/1999', source_register='Companies House'),
        # own (displaced) CCEW registration date of the matched org
        dict(uid='GB-CHC-200002', registerdate='10/10/1990', source_register=CCEW_REG),
        # own removal of the org whose spine removal was blanked
        dict(uid='GB-CHC-200003', removeddate='01/02/2000', source_register=CCEW_REG),
        # the absorbed org exists only here (and in matches)
        dict(uid='GB-CHC-200006', organisationname='GAMMA AID', source_register=CCEW_REG),
        # CCNI live org: name variant (kept); removed org: name variant
        # (dropped) and regdate variant (kept as a date-only row)
        dict(uid='GB-NIC-100001', organisationname='ULSTER HELP (OLD NAME)', source_register=CCNI_REG),
        dict(uid='GB-NIC-100002', organisationname='GONE CHARITY OLD', source_register=CCNI_REG),
        dict(uid='GB-NIC-100002', registerdate='01/01/2010', source_register=CCNI_REG),
    ]
    match_rows = [
        dict(uid='GB-CHC-200002', orgA_id_in_source='200002-0', orgA_source='ccew',
             orgA_uid='GB-CHC-200002', orgB_id_in_source='00000100', orgB_source='CH',
             orgB_uid='GB-COH-00000100', match_type='companyid - id_in_source'),
        # merger: 200006 absorbed into 200005
        dict(uid='GB-CHC-200005', orgA_id_in_source='200005-0', orgA_source='ccew',
             orgA_uid='GB-CHC-200005', orgB_id_in_source='200006-0', orgB_source='ccew',
             orgB_uid='GB-CHC-200006', match_type='ftc'),
        # OSCR 2012 linkage + cross-border link
        dict(uid='GB-SC-SC000001', orgA_id_in_source='SC000001', orgA_source='oscr',
             orgA_uid='GB-SC-SC000001', orgB_id_in_source='00000300', orgB_source='CH',
             orgB_uid='GB-COH-00000300', match_type='oscr'),
        dict(uid='GB-SC-SC000001', orgA_id_in_source='SC000001', orgA_source='oscr',
             orgA_uid='GB-SC-SC000001', orgB_id_in_source='SC009999', orgB_source='oscr',
             orgB_uid='GB-SC-SC009999', match_type='oscr'),
        dict(uid='GB-CHC-200005', orgA_id_in_source='200005-0', orgA_source='ccew',
             orgA_uid='GB-CHC-200005', orgB_id_in_source='SC000001', orgB_source='oscr',
             orgB_uid='GB-SC-SC000001', match_type='name - crossborder'),
    ]
    for i in range(bulk_oscr_orgs):
        sc = 'SC%06d' % (900000 + i)
        spine_rows.append(dict(uid='GB-SC-' + sc, organisationname='BULK %d' % i,
                               fulladdress='%d BULK STREET' % i, city='GLASGOW',
                               postcode='G1 1AA', registerdate='01/01/2000',
                               removeddate='', source_register=OSCR_REG))
        for j in (1, 2):
            coh = 'SC%06d' % (700000 + 2 * i + j)
            match_rows.append(dict(uid='GB-SC-' + sc, orgA_id_in_source=sc,
                                   orgA_source='oscr', orgA_uid='GB-SC-' + sc,
                                   orgB_id_in_source=coh, orgB_source='CH',
                                   orgB_uid='GB-COH-' + coh, match_type='oscr'))
    spine_csv = str(tmp_path / 'TSCS_spine.spine.csv')
    supp_csv = str(tmp_path / 'TSCS_spine.supplementary.csv')
    matches_csv = str(tmp_path / 'TSCS_spine.matches.csv')
    _write_csv(spine_csv, SPINE_FIELDS, spine_rows)
    _write_csv(supp_csv, SUPP_FIELDS, supp_rows)
    _write_csv(matches_csv, MATCH_FIELDS, match_rows)
    return spine_csv, supp_csv, matches_csv


def read_base(path):
    with open(path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


# ---------------------------------------------------------------------------
# date conversion
# ---------------------------------------------------------------------------

class TestSpineDateToBase:

    def test_round_trip_through_ccew_handler(self):
        # published dd/mm/yyyy -> base ddMonYYYY -> handler back to dd/mm/yyyy
        base = spine_date_to_base('17/03/1961')
        assert base == '17Mar1961'
        assert CCEWDataHandler().map_date(base) == '17/03/1961'

    def test_blank_is_blank(self):
        assert spine_date_to_base('') == ''

    def test_unparseable_returns_none(self):
        assert spine_date_to_base('not-a-date') is None


# ---------------------------------------------------------------------------
# loading the published files
# ---------------------------------------------------------------------------

class TestLoaders:

    def test_load_spine_partitions_by_register_and_prefix(self, tmp_path):
        spine_csv, _, _ = make_published_release(tmp_path)
        by_reg = load_spine(spine_csv)
        assert set(by_reg['ccew']) == {'GB-CHC-200001', 'GB-CHC-200002',
                                       'GB-CHC-200003', 'GB-CHC-200005'}
        assert set(by_reg['oscr']) == {'GB-SC-SC000001'}
        assert set(by_reg['ccni']) == {'GB-NIC-100001', 'GB-NIC-100002'}

    def test_load_supplementary_keeps_only_own_register_rows(self, tmp_path):
        _, supp_csv, _ = make_published_release(tmp_path)
        supp = load_supplementary(supp_csv)
        # the Companies House-attributed row for 200001 must not be loaded
        dates = [r['registerdate'] for r in supp['ccew']['GB-CHC-200001']]
        assert '09/09/1999' not in dates
        assert '01/01/1970' in dates

    def test_load_matches(self, tmp_path):
        _, _, matches_csv = make_published_release(tmp_path)
        links = load_matches(matches_csv)
        # explicit company-number match rows win
        assert links['companyid']['GB-CHC-200002'] == '00000100'
        # merger direction: orgB absorbed into orgA
        assert links['absorbed_into']['GB-CHC-200006'] == 'GB-CHC-200005'
        # OSCR 2012 linkage recovered from 'oscr' match rows
        assert links['sc_2012']['GB-SC-SC000001'] == {'sc': ['SC009999'],
                                                      'coh': ['00000300']}
        # cross-border: Scottish charity linked to a GB-CHC organisation
        assert 'GB-SC-SC000001' in links['crossborder_sc']
        assert 'GB-CHC-200002' in links['matched_uids']

    def test_ftc_companyid_fallback_only_when_unambiguous(self, tmp_path):
        rows = [
            dict(uid='GB-CHC-7', orgA_uid='GB-CHC-7', orgA_id_in_source='7-0',
                 orgB_uid='GB-COH-1', orgB_id_in_source='001', match_type='ftc'),
            dict(uid='GB-CHC-8', orgA_uid='GB-CHC-8', orgA_id_in_source='8-0',
                 orgB_uid='GB-COH-2', orgB_id_in_source='002', match_type='ftc'),
            dict(uid='GB-CHC-8', orgA_uid='GB-CHC-8', orgA_id_in_source='8-0',
                 orgB_uid='GB-COH-3', orgB_id_in_source='003', match_type='ftc'),
        ]
        path = str(tmp_path / 'm.csv')
        _write_csv(path, MATCH_FIELDS, rows)
        links = load_matches(path)
        assert links['companyid'].get('GB-CHC-7') == '001'     # unique -> used
        assert 'GB-CHC-8' not in links['companyid']            # ambiguous -> not


# ---------------------------------------------------------------------------
# per-organisation date rules
# ---------------------------------------------------------------------------

class TestChoosePrimaryDates:

    def spine_row(self, reg='17/03/1961', rem=''):
        return dict(organisationname='X', fulladdress='', city='', postcode='',
                    registerdate=reg, removeddate=rem)

    def test_unmatched_org_keeps_spine_dates(self):
        stats = defaultdict(int)
        reg, rem = choose_primary_dates(self.spine_row(), [], False, None, stats)
        assert (reg, rem) == ('17/03/1961', '')

    def test_matched_with_own_regdate_sets_spine_date_aside(self):
        # the spine date may belong to the matched company, so only the
        # regulator's own (supplementary) dates are written - on variant rows
        stats = defaultdict(int)
        supp = [dict(organisationname='', fulladdress='', city='', postcode='',
                     registerdate='10/10/1990', removeddate='')]
        reg, rem = choose_primary_dates(self.spine_row(reg='05/05/1990'),
                                        supp, True, None, stats)
        assert reg == ''
        assert stats['regdate_spine_date_set_aside'] == 1

    def test_removal_recovered_when_spine_blanked_it(self):
        stats = defaultdict(int)
        supp = [dict(organisationname='', fulladdress='', city='', postcode='',
                     registerdate='', removeddate='01/02/2000')]
        reg, rem = choose_primary_dates(self.spine_row(), supp, False, None, stats)
        assert rem == ''   # the own removal lives on the variant row
        assert stats['removal_recovered_from_supplementary'] == 1

    def test_absorbed_org_fills_dates_from_absorber(self):
        stats = defaultdict(int)
        absorber = self.spine_row(reg='01/01/1980', rem='')
        reg, rem = choose_primary_dates(None, [], True, absorber, stats)
        assert reg == '01/01/1980'
        assert rem == ''   # absorber is live, so no removal is invented
        assert stats['regdate_filled_from_absorber'] == 1


# ---------------------------------------------------------------------------
# row builders
# ---------------------------------------------------------------------------

class TestBuildCcewRows:

    def test_primary_row_conventions(self):
        stats = defaultdict(int)
        spine = dict(organisationname='ALPHA TRUST', fulladdress='1 HIGH STREET',
                     city='LONDON', postcode='E1 6AN',
                     registerdate='17/03/1961', removeddate='')
        rows = build_ccew_rows('GB-CHC-200001', spine, [], False, '00000100',
                               None, stats)
        assert len(rows) == 1
        p = rows[0]
        assert set(p) == set(ccew_fields)
        assert p['charitynumber'] == '200001'      # plain number, no -0 suffix
        assert p['primary_name'] == '1' and p['primary_address'] == '1'
        assert p['iteration'] == AS_OF_ITERATION
        assert p['cqc_reg'] == '0'                 # permanent loss -> neutral 0
        assert p['companyid'] == '00000100'
        assert p['registerdate'] == '17Mar1961'

    def test_variant_rows_have_blank_flags_and_iteration(self):
        stats = defaultdict(int)
        spine = dict(organisationname='ALPHA TRUST', fulladdress='1 HIGH STREET',
                     city='LONDON', postcode='E1 6AN',
                     registerdate='17/03/1961', removeddate='')
        supp = [dict(organisationname='ALPHA CHARITY', fulladdress='', city='',
                     postcode='', registerdate='', removeddate=''),
                dict(organisationname='', fulladdress='', city='', postcode='',
                     registerdate='', removeddate='')]   # empty -> skipped
        rows = build_ccew_rows('GB-CHC-200001', spine, supp, False, '', None, stats)
        assert len(rows) == 2
        v = rows[1]
        assert v['organisationname'] == 'ALPHA CHARITY'
        assert v['primary_name'] == '' and v['iteration'] == ''

    def test_primary_details_beat_variants_but_lose_to_fresh_download(self):
        # the downstream CCEW handler must pick the tagged primary over
        # untagged variants, and a fresher download over the primary
        handler = CCEWDataHandler()
        primary, extras = handler.find_primary_info({
            ('ALPHA TRUST', 'ALPHA TRUST', '1', AS_OF_ITERATION),
            ('ALPHA CHARITY', 'ALPHA CHARITY', '', ''),
        })
        assert primary == ('ALPHA TRUST', 'ALPHA TRUST')
        primary, extras = handler.find_primary_info({
            ('ALPHA TRUST', 'ALPHA TRUST', '1', AS_OF_ITERATION),
            ('ALPHA RENAMED', 'ALPHA RENAMED', '1', '03/2026'),
        })
        assert primary == ('ALPHA RENAMED', 'ALPHA RENAMED')


class TestBuildOscrRows:

    def test_primary_row_conventions(self):
        stats = defaultdict(int)
        spine = dict(organisationname='SCOT AID', fulladdress='9 ROYAL MILE',
                     city='EDINBURGH', postcode='EH1 1AA',
                     registerdate='26/06/1986', removeddate='')
        rows = build_oscr_rows('GB-SC-SC000001', spine, [], False,
                               {'sc': ['SC009999'], 'coh': ['00000300']},
                               True, None, stats)
        p = rows[0]
        assert set(p) == set(oscr_fields)
        assert p['charitynumber'] == 'SC000001'
        assert p['name_origin'] == '%s Name' % AS_OF_ITERATION
        assert p['iteration'] == AS_OF_ITERATION
        assert p['crossborder'] == '1'
        assert p['charitynumber_2012'] == 'SC009999'
        assert p['companyid1_2012'] == '00000300'
        assert p['companyid2_2012'] == ''

    def test_tagged_name_beats_untagged_variants_downstream(self):
        handler = OSCRDataHandler()
        primary, extras = handler.find_primary_name([
            ('SCOT AID', 'SCOT AID', '%s Name' % AS_OF_ITERATION),
            ('OLD SCOT AID', 'OLD SCOT AID', ''),
        ])
        assert primary == ('SCOT AID', 'SCOT AID')


class TestBuildCcniRows:

    def spine_row(self, rem=''):
        return dict(organisationname='ULSTER HELP', fulladdress='UNIT 5, SOME ROAD',
                    city='BELFAST', postcode='BT1 1AA',
                    registerdate='02/02/2015', removeddate=rem)

    def test_postcode_appended_to_address(self):
        # process_ccni re-extracts the postcode from the last comma-separated
        # component, so the base row must carry it inside the address string
        stats = defaultdict(int)
        rows = build_ccni_rows('GB-NIC-100001', self.spine_row(), [], False, '',
                               None, stats)
        p = rows[0]
        assert set(p) == set(ccni_fields)
        assert p['address'] == 'UNIT 5, SOME ROAD, BT1 1AA'

    def test_live_org_keeps_name_variants(self):
        stats = defaultdict(int)
        supp = [dict(organisationname='ULSTER HELP (OLD NAME)', fulladdress='',
                     city='', postcode='', registerdate='', removeddate='')]
        rows = build_ccni_rows('GB-NIC-100001', self.spine_row(), supp, False,
                               '', None, stats)
        assert len(rows) == 2
        assert rows[1]['organisationname'] == 'ULSTER HELP (OLD NAME)'

    def test_removed_org_drops_name_variants_but_keeps_dates(self):
        # process_ccni stamps one shared iteration on all base rows, so a
        # variant name could arbitrarily become primary for a removed org
        # that never reappears in a download - names/addresses are dropped,
        # dates are kept on date-only rows
        stats = defaultdict(int)
        supp = [dict(organisationname='GONE CHARITY OLD', fulladdress='',
                     city='', postcode='', registerdate='', removeddate=''),
                dict(organisationname='', fulladdress='', city='', postcode='',
                     registerdate='01/01/2010', removeddate='')]
        rows = build_ccni_rows('GB-NIC-100002', self.spine_row(rem='03/04/2019'),
                               supp, False, '', None, stats)
        names = [r['organisationname'] for r in rows[1:]]
        assert 'GONE CHARITY OLD' not in names
        date_rows = [r for r in rows[1:] if r['registerdate'] == '01Jan2010']
        assert len(date_rows) == 1
        assert date_rows[0]['organisationname'] == ''
        # only the row carrying name/address details was dropped
        assert stats['ccni_removed_variant_rows_dropped'] == 1


# ---------------------------------------------------------------------------
# end-to-end: reconstruct, then feed through the real pipeline steps
# ---------------------------------------------------------------------------

class TestWriteBaseFiles:

    def test_files_layout_and_universe(self, tmp_path):
        spine_csv, supp_csv, matches_csv = make_published_release(tmp_path)
        raw = str(tmp_path / 'raw_data')
        stats = write_base_files(spine_csv, supp_csv, matches_csv, raw)

        fields, rows = read_base(os.path.join(raw, 'ccew', 'ccew_spine_public.csv'))
        assert fields == ccew_fields
        uids = {r['uid'] for r in rows}
        # four spine orgs plus the absorbed org recovered from the matches
        assert uids == {'GB-CHC-200001', 'GB-CHC-200002', 'GB-CHC-200003',
                        'GB-CHC-200005', 'GB-CHC-200006'}
        assert stats['ccew']['orgs_absorbed_recovered'] == 1
        by_uid = {}
        for r in rows:
            by_uid.setdefault(r['uid'], []).append(r)
        # matched org: spine regdate set aside; own date on the variant row
        assert by_uid['GB-CHC-200002'][0]['registerdate'] == ''
        assert by_uid['GB-CHC-200002'][1]['registerdate'] == '10Oct1990'
        # suppressed removal recovered onto a variant row
        assert by_uid['GB-CHC-200003'][0]['removeddate'] == ''
        assert any(r['removeddate'] == '01Feb2000' for r in by_uid['GB-CHC-200003'][1:])
        # absorbed org: name from supplementary, regdate from the absorber
        assert by_uid['GB-CHC-200006'][0]['organisationname'] == 'GAMMA AID'
        assert by_uid['GB-CHC-200006'][0]['registerdate'] == '01Jan1980'

        fields, rows = read_base(os.path.join(raw, 'oscr', 'oscr_spine_public.csv'))
        assert fields == oscr_fields
        # SC009999 (the 2012-register predecessor) was merged into SC000001
        # during linkage; it is recovered as an organisation of its own so
        # that the next build re-merges it the same way
        assert {r['uid'] for r in rows} == {'GB-SC-SC000001', 'GB-SC-SC009999'}
        assert stats['oscr']['orgs_absorbed_recovered'] == 1

        fields, rows = read_base(os.path.join(raw, 'ccni', 'ccni_spine.csv'))
        assert fields == ccni_fields
        assert {r['uid'] for r in rows} == {'GB-NIC-100001', 'GB-NIC-100002'}

    def test_as_of_override(self, tmp_path):
        spine_csv, supp_csv, matches_csv = make_published_release(tmp_path)
        raw = str(tmp_path / 'raw_data')
        write_base_files(spine_csv, supp_csv, matches_csv, raw, as_of='03/2026')
        _, rows = read_base(os.path.join(raw, 'ccew', 'ccew_spine_public.csv'))
        assert rows[0]['iteration'] == '03/2026'


class TestPipelineAcceptsReconstructedBases:
    """The reconstructed bases must run through the real
    process-charity-source step (with no fresh downloads present)."""

    @pytest.fixture()
    def pipeline_cwd(self, tmp_path, monkeypatch):
        spine_csv, supp_csv, matches_csv = make_published_release(tmp_path)
        raw = tmp_path / 'raw_data'
        write_base_files(spine_csv, supp_csv, matches_csv, str(raw))
        workdir = tmp_path / 'repo'
        workdir.mkdir()
        # process_* read/write via ../raw_data relative to the cwd
        monkeypatch.chdir(workdir)
        return raw

    def test_process_ccew(self, pipeline_cwd):
        process_ccew()
        fields, rows = read_base(str(pipeline_cwd / '..' / 'raw_data' / 'ccew.all.csv'))
        assert fields == ccew_fields
        by_uid = {}
        for r in rows:
            by_uid.setdefault(r['uid'], []).append(r)
        assert len(by_uid) == 5
        p = by_uid['GB-CHC-200001'][0]
        assert p['primary_name'] == '1'
        assert p['registerdate'] == '17Mar1961'   # copied verbatim

    def test_process_oscr_regenerates_linkage(self, tmp_path, monkeypatch):
        # needs the bulk fixture: see make_published_release's docstring
        spine_csv, supp_csv, matches_csv = make_published_release(
            tmp_path, bulk_oscr_orgs=600)
        raw = tmp_path / 'raw_data'
        write_base_files(spine_csv, supp_csv, matches_csv, str(raw))
        workdir = tmp_path / 'repo'
        workdir.mkdir()
        monkeypatch.chdir(workdir)
        process_oscr()
        _, rows = read_base(str(raw / 'oscr.all.csv'))
        first = next(r for r in rows if r['uid'] == 'GB-SC-SC000001')
        assert first['name_origin'] == '%s Name' % AS_OF_ITERATION
        assert first['iteration'] == AS_OF_ITERATION
        assert first['crossborder'] == '1'
        # SC000001 sorts first, so its linkage rows are always in the
        # (reliably flushed) head of the regenerated linkage file
        links_text = (raw / 'oscr.linkage.csv').read_text(encoding='utf-8')
        assert 'GB-SC-SC000001,GB-COH-00000300' in links_text
        assert 'GB-SC-SC000001,GB-SC-SC009999' in links_text

    def test_process_ccni_re_extracts_postcode(self, pipeline_cwd):
        process_ccni()
        _, rows = read_base(str(pipeline_cwd / '..' / 'raw_data' / 'ccni.all.csv'))
        by_uid = {}
        for r in rows:
            by_uid.setdefault(r['uid'], r)   # first row per org is the primary
        p = by_uid['GB-NIC-100001']
        assert p['postcode'] == 'BT1 1AA'
        assert p['address'] == 'UNIT 5, SOME ROAD'
        assert p['iteration'] == '01/2024'
