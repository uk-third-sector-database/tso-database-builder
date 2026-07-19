import csv
import os

import pytest

from spine.bootstrap_lost_registers import write_lost_register_files

SPINE_HEADER = ['uid', 'organisationname', 'normalisedname', 'fulladdress',
                'city', 'postcode', 'registerdate', 'removeddate',
                'source_register', 'is_cic', 'cso_type', 'cso_subtype']
SUPP_HEADER = ['uid', 'organisationname', 'normalisedname', 'fulladdress',
               'city', 'postcode', 'registerdate', 'removeddate',
               'source_register']
MATCH_HEADER = ['uid', 'orgA_id_in_source', 'orgA_source', 'orgA_uid',
                'orgB_id_in_source', 'orgB_source', 'orgB_uid', 'match_type']


def write_csv(path, header, rows, encoding='utf-8'):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', newline='', encoding=encoding) as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    return str(path)


def spine_row(uid, name, register, address='', city='', postcode='',
              regdate='', remdate=''):
    return [uid, name, name.upper(), address, city, postcode,
            regdate, remdate, register, '', '', '']


def supp_row(uid, register, name='', address='', city='', postcode='',
             regdate='', remdate=''):
    return [uid, name, name.upper(), address, city, postcode,
            regdate, remdate, register]


def match_row(surviving_uid, a_id, a_source, a_uid, b_id, b_source, b_uid,
              match_type):
    return [surviving_uid, a_id, a_source, a_uid, b_id, b_source, b_uid,
            match_type]


@pytest.fixture
def setup(tmp_path):
    """A small published release + fresh downloads covering every scenario."""
    raw = tmp_path / 'raw_data'

    spine = write_csv(tmp_path / 'spine.csv', SPINE_HEADER, [
        # vanished co-op: own spine row, unmatched, dissolved
        spine_row('GB-COOP-R100', 'Vanished Coop', 'Co-operatives',
                  '1 HIGH ST', 'LEEDS', 'LS1 1AA',
                  '01/02/1990', '03/04/2010'),
        # current co-op: still in the fresh download -> must NOT be written
        spine_row('GB-COOP-R200', 'Current Coop', 'Co-operatives',
                  '2 LOW ST', 'YORK', 'YO1 1AA', '05/06/2000', ''),
        # matched co-op: spine regdate is the partner's (earlier); own
        # supp regdate must win; spine removal blank, own removal recovered
        spine_row('GB-COOP-R300', 'Matched Coop', 'Co-operatives',
                  '3 MID ST', 'HULL', 'HU1 1AA', '01/01/1900', ''),
        # co-op whose ONLY number evidence is a companyid-companyid link
        # to a charity: number recovered transitively via the charity's
        # own Companies House link
        spine_row('GB-COOP-R500', 'Transitive Coop', 'Co-operatives',
                  '5 FAR ST', 'DERBY', 'DE1 1AA', '02/03/1988', ''),
        spine_row('GB-CHC-900', 'Partner Charity',
                  'Charity Commission for England and Wales',
                  '6 CHY RD', 'DERBY', 'DE1 2BB', '01/01/1990', ''),
        # the mutual that absorbed a co-op record (absorber lookup)
        spine_row('GB-MPR-500W', 'Absorbing Mutual', 'Mutuals Public Register',
                  '9 MUT ST', 'BATH', 'BA1 1AA', '01/01/1980', '02/02/2015'),
        # vanished housing providers
        spine_row('GB-SHPE-H1', 'Gone Housing England', 'Social Housing England',
                  '', '', '', '10/10/2005', ''),
        spine_row('GB-SHR-77', 'Gone Housing Scotland',
                  'Scottish Housing Regulator'),
        # charity partner of the lost care service (not a target register)
        spine_row('GB-SC-SC001', 'Care Charity', 'Scottish Charity Register',
                  '4 CARE ST', 'OBAN', 'PA34 4AA', '01/01/1995', ''),
    ])

    supp = write_csv(tmp_path / 'supp.csv', SUPP_HEADER, [
        # absorbed co-op: name blanked as identical to absorber; own dates
        supp_row('GB-COOP-R400', 'Co-operatives',
                 regdate='07/08/1975', remdate='09/10/2012'),
        # matched co-op's own register dates
        supp_row('GB-COOP-R300', 'Co-operatives',
                 regdate='11/12/1965', remdate='13/01/2011'),
        # lost care service: name + address survive in supplementary
        supp_row('GB-CIS-CS900', 'Care Inspectorate Scotland',
                 name='Oban Care Home', address='5 SHORE RD', city='OBAN',
                 postcode='PA34 5BB', regdate='14/02/2003'),
        # care record whose name was blanked as identical to its absorbing
        # charity -> recovered from the absorber's spine row
        supp_row('GB-CIS-CS901', 'Care Inspectorate Scotland',
                 address='6 EMPTY LN'),
        # nameless care record absorbed into an organisation with no spine
        # row: no name recoverable anywhere -> skipped
        supp_row('GB-CIS-CS902', 'Care Inspectorate Scotland',
                 address='7 BLANK WAY'),
    ])

    matches = write_csv(tmp_path / 'matches.csv', MATCH_HEADER, [
        # absorbed co-op R400 <- mutual 500W; partner id = society number
        match_row('GB-MPR-500W', '500W', 'mutuals', 'GB-MPR-500W',
                  'R400', 'CoOps', 'GB-COOP-R400', 'companyid - coop mutual'),
        # matched co-op R300 also linked to the mutual (any match marks it)
        match_row('GB-MPR-500W', '500W', 'mutuals', 'GB-MPR-500W',
                  'R300', 'CoOps', 'GB-COOP-R300', 'companyid - coop mutual'),
        # transitive chain: coop R500 <-> charity CHC-900 share a company
        # number; the charity's own CH link exposes the number 00012345
        match_row('', 'R500', 'CoOps', 'GB-COOP-R500',
                  '900', 'ccew', 'GB-CHC-900', 'companyid - companyid'),
        match_row('GB-CHC-900', '900', 'ccew', 'GB-CHC-900',
                  '00012345', 'CH', 'GB-COH-00012345',
                  'companyid - id_in_source'),
        # lost care service attached to the Scottish charity
        match_row('GB-SC-SC001', 'SC001', 'OSCR', 'GB-SC-SC001',
                  'CS900', 'careinspectoratescot', 'GB-CIS-CS900',
                  'name - care'),
        match_row('GB-SC-SC001', 'SC001', 'OSCR', 'GB-SC-SC001',
                  'CS901', 'careinspectoratescot', 'GB-CIS-CS901',
                  'name - care'),
        # CS902's absorber has no spine row of its own
        match_row('GB-COH-999', '999', 'CH', 'GB-COH-999',
                  'CS902', 'careinspectoratescot', 'GB-CIS-CS902',
                  'name - care'),
    ])

    # fresh downloads: R200 still registered; a care service present but no
    # longer 'Voluntary or Not for Profit' does NOT count as present; a
    # housing provider re-designated away from 'Non-profit' likewise
    write_csv(raw / 'co_ops' / 'coops_opendata_2026_07.csv',
              ['CUK Organisation ID', 'Registered Name'],
              [['R200', 'Current Coop']])
    write_csv(raw / 'SocialHousingEngland' / 'registered_providers_20260701.csv',
              ['Organisation name', 'Registration number', 'Designation'],
              [['Gone Housing England', 'H1', 'Profit']])
    write_csv(raw / 'ScotHousingReg' / 'all-social-landlords-2026.csv',
              ['Reg No', 'Social Landlord'], [])
    write_csv(raw / 'CareInspectScot' / 'MDSF_data_2026.csv',
              ['CSNumber', 'ServiceType', 'ServiceProvider'],
              [['CS900', 'Private', 'Oban Care Home']], encoding='latin-1')

    return {'spine': spine, 'supp': supp, 'matches': matches,
            'raw': str(raw)}


def read_output(raw, relpath, encoding='utf-8'):
    with open(os.path.join(raw, relpath), newline='',
              encoding=encoding) as f:
        return {r[next(iter(r))]: r for r in csv.DictReader(f)}, relpath


def test_full_reconstruction(setup):
    stats = write_lost_register_files(setup['spine'], setup['supp'],
                                      setup['matches'], setup['raw'])

    coops, _ = read_output(setup['raw'],
                           'co_ops/coops_bootstrap_2026_01.csv')
    # keyed by first column = CUK Organisation ID
    assert set(coops) == {'R100', 'R300', 'R400', 'R500'}  # R200 is current

    # transitive recovery: number comes from the charity partner's CH link
    assert coops['R500']['Registered Number'] == '00012345'
    assert stats['coops']['companyid_recovered_via_partner'] == 1

    # vanished co-op: spine details pass through, no society number known
    r100 = coops['R100']
    assert r100['Registered Name'] == 'Vanished Coop'
    assert r100['Registered Street'] == '1 HIGH ST'
    assert r100['Registered City'] == 'LEEDS'
    assert r100['Registered Postcode'] == 'LS1 1AA'
    assert r100['Incorporation Date'] == '01/02/1990'
    assert r100['Dissolved Date'] == '03/04/2010'
    assert r100['Registered Number'] == ''

    # matched co-op: own register dates beat the (foreign) spine regdate,
    # and the removal the published spine blanked is recovered
    r300 = coops['R300']
    assert r300['Incorporation Date'] == '11/12/1965'
    assert r300['Dissolved Date'] == '13/01/2011'
    assert r300['Registered Number'] == '500W'

    # absorbed co-op: name filled from the absorbing mutual's spine row,
    # own supplementary dates kept, society number recovered from the match
    r400 = coops['R400']
    assert r400['Registered Name'] == 'Absorbing Mutual'
    assert r400['Incorporation Date'] == '07/08/1975'
    assert r400['Dissolved Date'] == '09/10/2012'
    assert r400['Registered Number'] == '500W'

    shpe, _ = read_output(
        setup['raw'],
        'SocialHousingEngland/registered_providers_bootstrap_Jan2026.csv')
    # re-designated provider counts as absent and is restored as Non-profit
    assert set(shpe) == {'Gone Housing England'}
    row = shpe['Gone Housing England']
    assert row['Registration number'] == 'H1'
    assert row['Registration date'] == '10/10/2005'
    assert row['Designation'] == 'Non-profit'

    shr, _ = read_output(
        setup['raw'],
        'ScotHousingReg/social_landlords_bootstrap.to_Jan2026.csv',
        encoding='latin-1')
    assert [ (r['Reg No'], r['Social Landlord']) for r in shr.values() ] == \
        [('77', 'Gone Housing Scotland')]

    cis, _ = read_output(
        setup['raw'], 'CareInspectScot/MDSF_data_bootstrap.Jan2026.csv',
        encoding='latin-1')
    # CS900 restored (present in fresh file but no longer in scope there);
    # CS901 restored with its name recovered from the absorbing charity;
    # CS902 skipped (no name recoverable anywhere)
    assert set(cis) == {'CS900', 'CS901'}
    assert cis['CS901']['ServiceProvider'] == 'Care Charity'
    assert cis['CS901']['Address_line_1'] == '6 EMPTY LN'
    row = cis['CS900']
    assert row['ServiceProvider'] == 'Oban Care Home'
    assert row['ServiceName'] == 'Oban Care Home'
    assert row['ServiceType'] == 'Voluntary or Not for Profit'
    assert row['Address_line_1'] == '5 SHORE RD'
    assert row['Service_town'] == 'OBAN'
    assert row['Service_Postcode'] == 'PA34 5BB'
    assert row['DateReg'] == '14/02/2003'

    assert stats['coops']['lost_records'] == 4
    assert stats['coops']['companyid_recovered'] == 3
    assert stats['coops']['regdate_own_preferred_over_spine'] == 1
    assert stats['coops']['removal_recovered_from_supplementary'] == 1
    assert stats['coops']['name_filled_from_absorber'] == 1
    assert stats['care_inspectorate_scot']['skipped_nameless'] == 1


def test_refuses_second_run(setup):
    write_lost_register_files(setup['spine'], setup['supp'],
                              setup['matches'], setup['raw'])
    with pytest.raises(RuntimeError, match='already exists'):
        write_lost_register_files(setup['spine'], setup['supp'],
                                  setup['matches'], setup['raw'])


def test_filenames_carry_the_release_currency(setup):
    """preprocess.py derives each row's iteration from the file name, so the
    names must parse to the release currency (01/2026) under the exact
    patterns preprocess.py uses for each folder."""
    write_lost_register_files(setup['spine'], setup['supp'],
                              setup['matches'], setup['raw'])
    from datetime import datetime

    base = os.path.basename  # noqa: E731

    # co_ops: <anything>_YYYY_MM.csv
    f = 'coops_bootstrap_2026_01.csv'
    year, month = f.removesuffix('.csv').split('_')[-2:]
    assert f'{month}/{year}' == '01/2026'
    assert os.path.exists(os.path.join(setup['raw'], 'co_ops', f))

    # SocialHousingEngland: <anything>_MonYYYY.csv
    f = 'registered_providers_bootstrap_Jan2026.csv'
    d = datetime.strptime(f.split('_')[-1].removesuffix('.csv'), '%b%Y')
    assert d.strftime('%m/%Y') == '01/2026'
    assert os.path.exists(os.path.join(setup['raw'],
                                       'SocialHousingEngland', f))

    # ScotHousingReg: <name>.to_MonYYYY.csv (and no hyphen-date false parse)
    f = 'social_landlords_bootstrap.to_Jan2026.csv'
    assert not f.split('-')[-1].removesuffix('.csv').isdigit()
    d = datetime.strptime(f.split('.')[-2].replace('to_', ''), '%b%Y')
    assert d.strftime('%m/%Y') == '01/2026'
    assert os.path.exists(os.path.join(setup['raw'], 'ScotHousingReg', f))

    # CareInspectScot: MDSF_data*.csv glob + <name>.MonYYYY.csv date parse
    f = 'MDSF_data_bootstrap.Jan2026.csv'
    assert f.startswith('MDSF_data')
    with pytest.raises(ValueError):
        int(base(f).split('MDSF_data_')[-1].removesuffix('.csv'))
    d = datetime.strptime(f.split('.')[-2], '%b%Y')
    assert d.strftime('%m/%Y') == '01/2026'
    assert os.path.exists(os.path.join(setup['raw'], 'CareInspectScot', f))
