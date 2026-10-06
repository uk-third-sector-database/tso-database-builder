# Tests for spine/bootstrap_ch_scrape.py - reconstruction of the lost 2022
# Companies House advanced-search scrape file from a published Spine release.
# All fixtures are tiny synthetic CSVs written to tmp_path; no real data
# files are read. The full-scale validation against the published v1.0
# release is documented in RUNBOOK.md section 3.

import csv
import os

import pytest

from acquire.companies_house_api import FIELDNAMES
from handler.all_companies_house import api_scrape_iteration, find_CIC_uids
from handler.base import iter_csv_rows
from handler.companies_house import CompaniesHouseDataHandler
from handler.companies_house_API_scrape import CH_APIScrape_DataHandler
from spine.bootstrap_ch_scrape import (
    OUTPUT_RELPATH,
    load_sic,
    spine_date_to_scrape,
    write_ch_scrape_bootstrap,
)

CH_REG = 'Companies House'
CCEW_REG = 'Charity Commission for England and Wales'

SPINE_FIELDS = ['uid', 'organisationname', 'normalisedname', 'fulladdress',
                'city', 'postcode', 'registerdate', 'removeddate',
                'source_register', 'is_cic', 'cso_type', 'cso_subtype']
SUPP_FIELDS = ['uid', 'organisationname', 'normalisedname', 'fulladdress',
               'city', 'postcode', 'registerdate', 'removeddate',
               'source_register', 'id_in_source']
MATCH_FIELDS = ['uid', 'orgA_id_in_source', 'orgA_source', 'orgA_uid',
                'orgB_id_in_source', 'orgB_source', 'orgB_uid', 'match_type']
SIC_FIELDS = ['uid', 'SIC']


def _write_csv(path, fieldnames, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, restval='')
        w.writeheader()
        w.writerows(rows)


def make_published_release(tmp_path):
    """A miniature published release exercising every reconstruction rule.

    Companies:
      00000100 unmatched, live, own spine dates, own SIC
      00000200 matched, spine dates displaced by the charity's -> recovered
               from CH-attributed supplementary rows
      00000300 CIC, dissolved, unmatched, multi-format SIC rows
      00000400 absorbed into removed charity 777777: name/address/regdate
               from own supplementary rows, removal from the absorber,
               SIC via the (unambiguous) absorber
      00000500 absorbed into live CIC-flagged charity 666666, no
               supplementary rows: everything from the absorber, but SIC
               ambiguous (the absorber has two company partners)
      00000600 the second company of 666666 (same ambiguity)
      00000900 GB-COH uid attributed to another register: excluded
    """
    spine_rows = [
        dict(uid='GB-COH-00000100', organisationname='PLAIN COMPANY LIMITED',
             fulladdress='1 HIGH STREET', city='LONDON', postcode='E1 6AN',
             registerdate='05/05/1990', removeddate='',
             source_register=CH_REG, is_cic='False'),
        dict(uid='GB-COH-00000200', organisationname='BETA TRADING LIMITED',
             fulladdress='2 LOW ROAD', city='LEEDS', postcode='LS1 1AA',
             registerdate='01/01/1989', removeddate='01/01/2020',
             source_register=CH_REG, is_cic='False'),
        dict(uid='GB-COH-00000300', organisationname='GAMMA CIC',
             fulladdress='3 MID LANE', city='YORK', postcode='YO1 7HH',
             registerdate='07/07/2005', removeddate='10/10/2010',
             source_register=CH_REG, is_cic='True'),
        dict(uid='GB-COH-00000900', organisationname='NOT A CH ROW',
             fulladdress='9 WRONG WAY', city='HULL', postcode='HU1 1AA',
             registerdate='01/01/2000', removeddate='',
             source_register=CCEW_REG, is_cic='False'),
        dict(uid='GB-CHC-888888', organisationname='BETA FOUNDATION',
             fulladdress='2 LOW ROAD', city='LEEDS', postcode='LS1 1AA',
             registerdate='01/01/1989', removeddate='01/01/2020',
             source_register=CCEW_REG, is_cic='False'),
        dict(uid='GB-CHC-777777', organisationname='EPSILON CHARITY',
             fulladdress='5 TOP WAY', city='BATH', postcode='BA1 1AA',
             registerdate='01/01/1980', removeddate='01/01/2018',
             source_register=CCEW_REG, is_cic='False'),
        dict(uid='GB-CHC-666666', organisationname='CIC PARENT',
             fulladdress='6 SIDE STREET', city='GLASGOW', postcode='G1 1AA',
             registerdate='03/03/2005', removeddate='',
             source_register=CCEW_REG, is_cic='True'),
    ]
    supp_rows = [
        # displaced own dates of the matched company
        dict(uid='GB-COH-00000200', registerdate='05/06/1990',
             removeddate='15/03/2015', source_register=CH_REG),
        # same uid attributed to another register: must be ignored
        dict(uid='GB-COH-00000200', registerdate='01/01/1900',
             source_register=CCEW_REG),
        # the absorbed company's own primary record + a regdate variant
        dict(uid='GB-COH-00000400', organisationname='TRADING ARM LIMITED',
             fulladdress='9 BACK LANE', city='BATH', postcode='BA2 2BB',
             source_register=CH_REG),
        dict(uid='GB-COH-00000400', registerdate='02/02/2001',
             source_register=CH_REG),
        # an older name variant: must NOT beat the first row's name
        dict(uid='GB-COH-00000400', organisationname='TRADING ARM OLD NAME',
             source_register=CH_REG),
    ]
    match_rows = [
        dict(uid='GB-CHC-888888', orgA_uid='GB-CHC-888888', orgA_source='ccew',
             orgB_uid='GB-COH-00000200', orgB_id_in_source='00000200',
             orgB_source='CH', match_type='companyid - id_in_source'),
        dict(uid='GB-CHC-777777', orgA_uid='GB-CHC-777777', orgA_source='ccew',
             orgB_uid='GB-COH-00000400', orgB_id_in_source='00000400',
             orgB_source='CH', match_type='ftc'),
        dict(uid='GB-CHC-666666', orgA_uid='GB-CHC-666666', orgA_source='ccew',
             orgB_uid='GB-COH-00000500', orgB_id_in_source='00000500',
             orgB_source='CH', match_type='ftc'),
        dict(uid='GB-CHC-666666', orgA_uid='GB-CHC-666666', orgA_source='ccew',
             orgB_uid='GB-COH-00000600', orgB_id_in_source='00000600',
             orgB_source='CH', match_type='ftc'),
    ]
    sic_rows = [
        dict(uid='GB-COH-00000100',
             SIC='62020 - Information technology consultancy activities'),
        # multiple rows and mixed formats for one uid, with a duplicate code
        dict(uid='GB-COH-00000300', SIC='82990, 88990'),
        dict(uid='GB-COH-00000300',
             SIC='82990 - Other business support service activities n.e.c.'),
        dict(uid='GB-CHC-777777',
             SIC='94120 - Activities of professional membership organizations'),
        dict(uid='GB-CHC-666666', SIC='85310 - General secondary education'),
    ]

    spine = os.path.join(tmp_path, 'spine.csv')
    supp = os.path.join(tmp_path, 'supp.csv')
    matches = os.path.join(tmp_path, 'matches.csv')
    sic = os.path.join(tmp_path, 'sic.csv')
    _write_csv(spine, SPINE_FIELDS, spine_rows)
    _write_csv(supp, SUPP_FIELDS, supp_rows)
    _write_csv(matches, MATCH_FIELDS, match_rows)
    _write_csv(sic, SIC_FIELDS, sic_rows)
    return spine, supp, matches, sic


@pytest.fixture()
def bootstrap(tmp_path):
    """Run the reconstruction once; return (rows-by-company-number, stats, path)."""
    spine, supp, matches, sic = make_published_release(tmp_path)
    out_root = os.path.join(tmp_path, 'raw_data')
    stats = write_ch_scrape_bootstrap(spine, supp, matches, sic, out_root)
    path = os.path.join(out_root, OUTPUT_RELPATH)
    with open(path, newline='', encoding='UTF8') as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        rows = {r['company_number']: r for r in reader}
    return rows, stats, path, header


# ---------------------------------------------------------------------------
# unit pieces
# ---------------------------------------------------------------------------

def test_spine_date_to_scrape():
    from collections import defaultdict
    stats = defaultdict(int)
    assert spine_date_to_scrape('17/03/1961', stats) == '1961-03-17'
    assert spine_date_to_scrape('', stats) == ''
    assert stats['unparseable_dates'] == 0
    # anything unparseable must be blanked: the handler's map_date crashes on it
    assert spine_date_to_scrape('17Mar1961', stats) == ''
    assert stats['unparseable_dates'] == 1


def test_load_sic_formats(tmp_path):
    path = os.path.join(tmp_path, 'sic.csv')
    _write_csv(path, SIC_FIELDS, [
        dict(uid='GB-COH-1', SIC='82990, 88990'),
        dict(uid='GB-COH-1', SIC='82990 - Duplicate code, with comma in text'),
        dict(uid='GB-COH-2', SIC='94120 - Activities of professional membership organizations'),
    ])
    sic = load_sic(path)
    assert sic['GB-COH-1'] == ['82990', '88990']
    assert sic['GB-COH-2'] == ['94120']


# ---------------------------------------------------------------------------
# the reconstructed file
# ---------------------------------------------------------------------------

def test_layout_and_universe(bootstrap):
    rows, stats, path, header = bootstrap
    # exact scraper column layout, and the dateless name that earns the
    # historical '2022' iteration stamp
    assert header == FIELDNAMES
    assert api_scrape_iteration(path) == '2022'
    # one row per company: three from the spine, three recovered from merges;
    # the non-CH-register GB-COH row is excluded
    assert sorted(rows) == ['00000100', '00000200', '00000300',
                            '00000400', '00000500', '00000600']
    assert stats['companies_from_spine'] == 3
    assert stats['companies_absorbed_recovered'] == 3
    assert stats['companies_supp_only'] == 0


def test_unmatched_company_passes_through(bootstrap):
    rows, _, _, _ = bootstrap
    r = rows['00000100']
    assert r['company_name'] == 'PLAIN COMPANY LIMITED'
    assert r['date_of_creation'] == '1990-05-05'
    assert r['date_of_cessation'] == ''
    assert r['company_subtype'] == ''
    assert r['sic_codes'] == "['62020']"
    assert (r['address_line_1'], r['locality'], r['postal_code']) == \
        ('1 HIGH STREET', 'LONDON', 'E1 6AN')
    # unused-by-consumer columns stay blank
    assert (r['etag'], r['hits'], r['company_status'], r['company_type'],
            r['kind'], r['country'], r['region']) == ('',) * 7


def test_matched_company_recovers_own_dates(bootstrap):
    rows, stats, _, _ = bootstrap
    r = rows['00000200']
    # spine carried the charity's dates; the company's own displaced dates
    # live on its CH-attributed supplementary rows
    assert r['date_of_creation'] == '1990-06-05'
    assert r['date_of_cessation'] == '2015-03-15'
    assert stats['regdate_recovered_from_supplementary'] == 1
    assert stats['remdate_spine_date_set_aside'] == 1


def test_cic_flag_and_multi_format_sic(bootstrap):
    rows, _, _, _ = bootstrap
    r = rows['00000300']
    assert r['company_subtype'] == 'community-interest-company'
    assert r['date_of_cessation'] == '2010-10-10'
    assert r['sic_codes'] == "['82990', '88990']"


def test_absorbed_company_from_supplementary_and_absorber(bootstrap):
    rows, stats, _, _ = bootstrap
    r = rows['00000400']
    # first supplementary row wins the name; the variant row must not
    assert r['company_name'] == 'TRADING ARM LIMITED'
    assert (r['address_line_1'], r['locality'], r['postal_code']) == \
        ('9 BACK LANE', 'BATH', 'BA2 2BB')
    assert r['date_of_creation'] == '2001-02-02'
    # no own removal: filled from the (removed) absorber
    assert r['date_of_cessation'] == '2018-01-01'
    assert stats['remdate_filled_from_absorber'] >= 1
    # SIC re-keyed to the absorber at build time; absorber unambiguous
    assert r['sic_codes'] == "['94120']"
    assert stats['sic_via_absorber'] == 1


def test_absorbed_company_with_nothing_fills_from_absorber(bootstrap):
    rows, stats, _, _ = bootstrap
    r = rows['00000500']
    assert r['company_name'] == 'CIC PARENT'
    assert r['date_of_creation'] == '2005-03-03'
    assert r['date_of_cessation'] == ''  # absorber is live
    # only the postcode of the address is taken from the absorber
    assert r['postal_code'] == 'G1 1AA'
    assert r['address_line_1'] == ''
    # the absorber's is_cic flag is inherited (a charity flagged CIC got the
    # flag from its company partner)
    assert r['company_subtype'] == 'community-interest-company'
    assert stats['cic_inherited_from_absorber'] >= 1
    # two company partners -> SIC cannot be attributed to one of them
    assert r['sic_codes'] == ''
    assert stats['sic_ambiguous_absorber'] == 2


# ---------------------------------------------------------------------------
# ingestion by the real pipeline handler
# ---------------------------------------------------------------------------

def test_handler_round_trip(bootstrap):
    rows, _, path, _ = bootstrap
    handler = CH_APIScrape_DataHandler()
    out = {}
    for raw in iter_csv_rows(path, handler):
        for r in handler.transform_row(raw):
            out[r['uid']] = r
    assert sorted(out) == ['GB-COH-00000100', 'GB-COH-00000200',
                           'GB-COH-00000300', 'GB-COH-00000400',
                           'GB-COH-00000500', 'GB-COH-00000600']
    r = out['GB-COH-00000100']
    # dates come back in the pipeline's dd/mm/yyyy, addresses re-consolidate
    # to the published fulladdress, SIC strips back to plain codes
    assert r['registerdate'] == '05/05/1990'
    assert r['removeddate'] == ''
    assert r['fulladdress'] == '1 HIGH STREET'
    assert r['postcode'] == 'E1 6AN'
    assert r['SIC'] == '62020'
    assert r['is_cic'] is False
    assert out['GB-COH-00000300']['is_cic'] is True
    assert out['GB-COH-00000300']['SIC'] == '82990, 88990'
    assert out['GB-COH-00000200']['removeddate'] == '15/03/2015'


def test_find_cic_uids_reads_the_file(bootstrap):
    path = bootstrap[2]
    # exactly the call preprocess-CH makes (Latin-1 and all)
    uids = find_CIC_uids(path, 'company_subtype', 'community-interest-company',
                         'Latin-1')
    assert sorted(uids) == ['GB-COH-00000300', 'GB-COH-00000500',
                            'GB-COH-00000600']


def test_bulk_download_wins_recency_contest(bootstrap):
    """A company present in both the bootstrap (iteration 2022) and a fresh
    bulk download (07/2026): the bulk name/address must become primary, the
    registration date stays the earliest and the removal the latest."""
    path = bootstrap[2]
    handler = CH_APIScrape_DataHandler()
    boot_row = None
    for raw in iter_csv_rows(path, handler):
        for r in handler.transform_row(raw):
            if r['uid'] == 'GB-COH-00000100':
                boot_row = r
    assert boot_row is not None
    boot_row.update(iteration='2022', companyid='', extraname='')

    bulk_row = dict(uid='GB-COH-00000100',
                    organisationname='PLAIN COMPANY (RENAMED) LIMITED',
                    normalisedname='PLAIN COMPANY RENAMED LIMITED',
                    fulladdress='99 NEW ADDRESS', city='LONDON',
                    postcode='E2 7AA', companyid='', id_in_source='00000100',
                    registerdate='06/05/1990', removeddate='01/02/2026',
                    source='CH', source_register=CH_REG, is_cic='False',
                    iteration='07/2026', extraname='0', SIC='62020')
    # simulate the CSV round trip of the preprocess intermediate: every
    # value the consolidation sees is a string
    boot_row = {k: str(v) for k, v in boot_row.items()}

    combined, _ = CompaniesHouseDataHandler().combine_org_details_per_source(
        [boot_row, bulk_row])
    assert combined['organisationname'] == 'PLAIN COMPANY (RENAMED) LIMITED'
    assert combined['fulladdress'] == '99 NEW ADDRESS'
    # earliest registration (the bootstrap's) and latest removal (the bulk's)
    assert combined['registerdate'] == '05/05/1990'
    assert combined['removeddate'] == '01/02/2026'
