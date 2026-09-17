# Tests for the 2026-07 correctness fixes in the handler/ package.
# All fixtures are tiny synthetic rows - no real data files are read.

import csv
from copy import deepcopy
from datetime import datetime

import pandas as pd
import pytest

from handler.base import (
    DataHandler,
    compress_org_details,
    dict_indexed_by_field,
    fix_dates_set,
    parse_iteration_date,
)
from handler.ccew import CCEWDataHandler
from handler.oscr import OSCRDataHandler
from handler.companies_house import CompaniesHouseDataHandler
from handler.preprocess import drop_duplicates, parse_iteration_tag
from handler.preprocess_charity_regulators import (
    CCNI_KNOWN_BAD_COMPANY_NUMBERS,
    format_date_strings,
    find_postcode,
    normalise_ccni_company_number,
    process_ccni,
)
from handler.ccni import CCNIDataHandler


def test_utf8_intermediate_csv_is_read_without_platform_default(tmp_path):
    path = tmp_path / "unicode.csv"
    path.write_text("uid,name\nGB-COH-1,ČARITY\n", encoding="utf-8")

    result = dict_indexed_by_field(path, "uid")

    assert result["GB-COH-1"][0]["name"] == "ČARITY"


# ---------------------------------------------------------------------------
# Item 2: OSCR name_origin date formatting must preserve trailing text
# ---------------------------------------------------------------------------

class TestFormatDateStrings:

    def test_date_with_text_keeps_text(self):
        assert format_date_strings('09/2021 Name') == '09/2021 Name'

    def test_named_month_with_text_keeps_text(self):
        assert format_date_strings('Sept 2021 Name') == '09/2021 Name'

    def test_bare_year_with_text_keeps_text(self):
        assert format_date_strings('2012 Name') == '01/2012 Name'

    def test_pure_year(self):
        assert format_date_strings('2012') == '01/2012'

    def test_pure_month_year(self):
        assert format_date_strings('09/2021') == '09/2021'

    def test_pure_named_month_year(self):
        assert format_date_strings('Sept 2021') == '09/2021'

    def test_no_date_returned_unchanged(self):
        assert format_date_strings('Name') == 'Name'

    def test_empty_string(self):
        assert format_date_strings('') == ''


# ---------------------------------------------------------------------------
# Item 3: OSCR primary-name selection must tolerate undated name_origin
# ---------------------------------------------------------------------------

class TestOSCRFindPrimaryName:

    def test_undated_name_does_not_crash_and_is_honoured(self):
        handler = OSCRDataHandler()
        primary, extras = handler.find_primary_name([('Org A', 'ORG A', 'Name')])
        assert primary == ('Org A', 'ORG A')

    def test_dated_name_beats_undated(self):
        handler = OSCRDataHandler()
        names = [('Old Org', 'OLD ORG', 'Name'),
                 ('New Org', 'NEW ORG', '10/2022 Name')]
        primary, extras = handler.find_primary_name(names)
        assert primary == ('New Org', 'NEW ORG')
        assert ('Old Org', 'OLD ORG') in extras

    def test_most_recent_dated_name_wins(self):
        handler = OSCRDataHandler()
        names = [('Older', 'OLDER', '09/2021 Name'),
                 ('Newer', 'NEWER', '10/2022 Name')]
        primary, extras = handler.find_primary_name(names)
        assert primary == ('Newer', 'NEWER')


# ---------------------------------------------------------------------------
# Item 4: CCEW find_primary_info must tolerate blank/invalid iteration tags
# ---------------------------------------------------------------------------

class TestCCEWFindPrimaryInfo:

    def test_blank_iteration_treated_as_oldest(self):
        handler = CCEWDataHandler()
        details = [('Name A', 'NAME A', '', ''),          # blank iteration
                   ('Name B', 'NAME B', '', '03/2022')]   # dated iteration
        primary, extras = handler.find_primary_info(details)
        assert primary == ('Name B', 'NAME B')
        assert ('Name A', 'NAME A') in extras

    def test_invalid_iteration_does_not_return_none(self):
        handler = CCEWDataHandler()
        details = [('Name A', 'NAME A', '', 'garbage')]
        primary, extras = handler.find_primary_info(details)
        assert primary == ('Name A', 'NAME A')
        assert extras == []


# ---------------------------------------------------------------------------
# Item 5: chronological (not text) date sorting in fix_dates_set
# ---------------------------------------------------------------------------

class TestFixDatesSet:

    def test_earliest_is_chronological(self):
        primary, extras = fix_dates_set({'01/02/2020', '30/11/2019'}, 0)
        assert primary == '30/11/2019'
        assert extras == ['01/02/2020']

    def test_latest_is_chronological(self):
        primary, extras = fix_dates_set({'01/02/2020', '30/11/2019'}, -1)
        assert primary == '01/02/2020'
        assert extras == ['30/11/2019']

    def test_empty_set(self):
        assert fix_dates_set(set(), 0) == ('', '')
        assert fix_dates_set({''}, 0) == ('', '')

    def test_unparseable_dates_become_extras(self):
        primary, extras = fix_dates_set({'01/02/2020', 'garbage'}, -1)
        assert primary == '01/02/2020'
        assert extras == ['garbage']

    def test_only_unparseable_falls_back_to_text_sort(self):
        primary, extras = fix_dates_set({'bbb', 'aaa'}, 0)
        assert primary == 'aaa'
        assert extras == ['bbb']

    def test_datetime_objects_accepted(self):
        # ccew's check_for_old_data passes datetime keys, not strings
        early, late = datetime(2019, 11, 30), datetime(2020, 2, 1)
        primary, _ = fix_dates_set({early, late}, -1)
        assert primary == late

    def test_same_function_used_by_all_three_modules(self):
        import handler.base as b
        import handler.ccew as c
        import handler.oscr as o
        assert c.fix_dates_set is b.fix_dates_set
        assert o.fix_dates_set is b.fix_dates_set


# ---------------------------------------------------------------------------
# Deterministic generic primary/extras selection
# ---------------------------------------------------------------------------

class TestGenericConsolidationDeterminism:

    @staticmethod
    def make_row(**overrides):
        row = {
            'uid': 'GB-COH-1',
            'id_in_source': '1',
            'organisationname': 'Example Org',
            'normalisedname': 'EXAMPLE ORG',
            'companyid': '',
            'fulladdress': '1 EXAMPLE STREET',
            'city': 'LONDON',
            'postcode': 'AA1 1AA',
            'registerdate': '01/01/2020',
            'removeddate': '',
            'source': 'CH',
            'source_register': 'Companies House',
            'is_cic': '',
            'iteration': '07/2026',
        }
        row.update(overrides)
        return row

    def test_equal_iteration_variants_ignore_input_order(self):
        rows = [
            {
                'uid': 'GB-COH-1',
                'id_in_source': '1',
                'organisationname': 'Zulu Org',
                'normalisedname': 'ZULU ORG',
                'companyid': '',
                'fulladdress': '9 ZULU STREET',
                'city': 'LONDON',
                'postcode': 'ZZ1 1ZZ',
                'registerdate': '01/01/2020',
                'removeddate': '',
                'source': 'CH',
                'source_register': 'Companies House',
                'is_cic': '',
                'iteration': '07/2026',
            },
            {
                'uid': 'GB-COH-1',
                'id_in_source': '1',
                'organisationname': 'Alpha Org',
                'normalisedname': 'ALPHA ORG',
                'companyid': '',
                'fulladdress': '1 ALPHA STREET',
                'city': 'LONDON',
                'postcode': 'AA1 1AA',
                'registerdate': '01/01/2020',
                'removeddate': '',
                'source': 'CH',
                'source_register': 'Companies House',
                'is_cic': '',
                'iteration': '07/2026',
            },
        ]
        handler = DataHandler()
        handler.tmp_fields = []

        forward = handler.combine_org_details_per_source(deepcopy(rows))
        reverse = handler.combine_org_details_per_source(
            list(reversed(deepcopy(rows)))
        )

        assert forward == reverse
        assert forward[0]['organisationname'] == 'Alpha Org'
        assert forward[0]['fulladdress'] == '1 ALPHA STREET'

    def test_latest_active_snapshot_keeps_historical_removal_as_extra(self):
        rows = [
            self.make_row(iteration='2022', removeddate='07/03/2023'),
            self.make_row(iteration='07/2026', removeddate=''),
        ]
        handler = DataHandler()
        handler.tmp_fields = []

        sub_spine, extras = handler.combine_org_details_per_source(rows)

        assert sub_spine['removeddate'] == ''
        assert [row['removeddate'] for row in extras if row['removeddate']] == [
            '07/03/2023'
        ]

    def test_daily_refresh_beats_monthly_bulk_status(self):
        rows = [
            self.make_row(iteration='07/2026', removeddate=''),
            self.make_row(
                iteration='18/07/2026',
                removeddate='17/07/2026',
                organisationname='Daily Refresh Org',
                normalisedname='DAILY REFRESH ORG',
                fulladdress='18 REFRESH STREET',
            ),
        ]
        handler = DataHandler()
        handler.tmp_fields = []

        sub_spine, extras = handler.combine_org_details_per_source(rows)

        assert sub_spine['removeddate'] == '17/07/2026'
        assert sub_spine['organisationname'] == 'Daily Refresh Org'
        assert sub_spine['fulladdress'] == '18 REFRESH STREET'
        assert not [row for row in extras if row['removeddate']]

    def test_daily_active_refresh_can_supersede_monthly_removed_status(self):
        rows = [
            self.make_row(
                iteration='07/2026',
                removeddate='07/03/2023',
            ),
            self.make_row(iteration='18/07/2026', removeddate=''),
        ]
        handler = DataHandler()
        handler.tmp_fields = []

        sub_spine, extras = handler.combine_org_details_per_source(rows)

        assert sub_spine['removeddate'] == ''
        assert any(row['removeddate'] == '07/03/2023' for row in extras)

    def test_iteration_precision_order(self):
        assert parse_iteration_date('2022') == datetime(2022, 1, 1)
        assert parse_iteration_date('07/2026') == datetime(2026, 7, 1)
        assert parse_iteration_date('18/07/2026') == datetime(2026, 7, 18)


# ---------------------------------------------------------------------------
# CCEW consolidation fixtures (items 6, 7, 12)
# ---------------------------------------------------------------------------

def make_ccew_row(**overrides):
    row = {
        'uid': 'GB-CHC-123456',
        'id_in_source': '123456-0',
        'organisationname': 'Main Charity',
        'normalisedname': 'MAIN CHARITY',
        'companyid': '',
        'fulladdress': '1 MAIN STREET',
        'city': 'TOWNSVILLE',
        'postcode': 'AB1 2CD',
        'registerdate': '01/01/2000',
        'removeddate': '',
        'source': 'ccew',
        'source_register': 'Charity Commission for England and Wales',
        'is_cic': '',
        'primary_name': '1',
        'primary_address': '1',
        'cqc_reg': '',
        'iteration': '03/2022',
    }
    row.update(overrides)
    return row


class TestCCEWUmbrellaIdInSource:
    """Item 7: umbrella consolidation must take its identifiers from the
    umbrella ('-0') rows, not from whichever row the outer loop saw last."""

    def test_umbrella_id_used_even_when_linked_row_is_last(self):
        handler = CCEWDataHandler()
        umbrella = make_ccew_row(id_in_source='123456-0')
        linked = make_ccew_row(id_in_source='123456-3',
                               organisationname='Linked Branch',
                               normalisedname='LINKED BRANCH',
                               fulladdress='2 SIDE STREET',
                               primary_name='', primary_address='')
        # the linked charity row is deliberately LAST in the input
        sub_spine, extras = handler.combine_org_details_per_source([umbrella, linked])
        assert sub_spine['id_in_source'] == '123456-0'
        assert sub_spine['uid'] == 'GB-CHC-123456'


class TestCCEWCurrentUmbrellaStatus:

    def test_newest_active_registration_keeps_historical_dates_as_extras(self):
        handler = CCEWDataHandler()
        current = make_ccew_row(
            uid='GB-CHC-800882',
            id_in_source='800882-0',
            organisationname='RE-REGISTERED TRUST',
            normalisedname='RE REGISTERED TRUST',
            registerdate='28/02/2012',
            removeddate='',
            iteration='07/2026',
        )
        historical = make_ccew_row(
            uid='GB-CHC-800882',
            id_in_source='800882',
            organisationname='OLD TRUST',
            normalisedname='OLD TRUST',
            registerdate='03/02/1989',
            removeddate='27/08/2009',
            primary_name='',
            primary_address='',
            iteration='',
        )

        sub_spine, extras = handler.combine_org_details_per_source(
            [historical, current]
        )

        assert sub_spine['registerdate'] == '28/02/2012'
        assert sub_spine['removeddate'] == ''
        assert '03/02/1989' in {row['registerdate'] for row in extras}
        assert '27/08/2009' in {row['removeddate'] for row in extras}

    def test_newest_removed_registration_remains_removed(self):
        handler = CCEWDataHandler()
        older = make_ccew_row(
            registerdate='01/01/2000', removeddate='',
            iteration='01/2020',
        )
        newest = make_ccew_row(
            registerdate='01/01/2000', removeddate='02/02/2025',
            iteration='07/2026',
        )

        sub_spine, _ = handler.combine_org_details_per_source(
            [older, newest]
        )

        assert sub_spine['removeddate'] == '02/02/2025'


class TestCCEWCqcRegCarriedThrough:
    """Item 12 (CCEW half): cqc_reg must survive consolidation in the
    non-umbrella branch too."""

    def test_cqc_reg_set_in_non_umbrella_branch(self):
        handler = CCEWDataHandler()
        r1 = make_ccew_row(id_in_source='654321', uid='GB-CHC-654321', cqc_reg='1')
        r2 = make_ccew_row(id_in_source='654321', uid='GB-CHC-654321', cqc_reg='',
                           organisationname='Older Name', normalisedname='OLDER NAME',
                           iteration='01/2020', primary_name='')
        sub_spine, extras = handler.combine_org_details_per_source([r1, r2])
        assert str(sub_spine['cqc_reg']) == '1'

    def test_cqc_reg_still_set_in_umbrella_branch(self):
        handler = CCEWDataHandler()
        umbrella = make_ccew_row(cqc_reg='1')
        linked = make_ccew_row(id_in_source='123456-1', cqc_reg='',
                               primary_name='', primary_address='')
        sub_spine, extras = handler.combine_org_details_per_source([umbrella, linked])
        assert str(sub_spine['cqc_reg']) == '1'


class TestCCEWConsolidationDeterminism:

    def test_equal_iteration_primary_variants_ignore_input_order(self):
        handler = CCEWDataHandler()
        rows = [
            make_ccew_row(
                organisationname='Zulu Charity',
                normalisedname='ZULU CHARITY',
                fulladdress='9 ZULU STREET',
            ),
            make_ccew_row(
                organisationname='Alpha Charity',
                normalisedname='ALPHA CHARITY',
                fulladdress='1 ALPHA STREET',
            ),
        ]

        forward = handler.combine_org_details_per_source(deepcopy(rows))
        reverse = handler.combine_org_details_per_source(
            list(reversed(deepcopy(rows)))
        )

        assert forward == reverse
        assert forward[0]['organisationname'] == 'Alpha Charity'
        assert forward[0]['fulladdress'] == '1 ALPHA STREET'


# ---------------------------------------------------------------------------
# OSCR consolidation fixtures (items 5 end-to-end and 12)
# ---------------------------------------------------------------------------

def make_oscr_row(**overrides):
    row = {
        'uid': 'GB-SC-SC012345',
        'id_in_source': 'SC012345',
        'organisationname': 'Scottish Charity',
        'normalisedname': 'SCOTTISH CHARITY',
        'companyid': '',
        'fulladdress': '5 HIGH STREET',
        'city': 'EDINBURGH',
        'postcode': 'EH1 1AA',
        'registerdate': '01/02/2020',
        'removeddate': '',
        'source': 'OSCR',
        'source_register': 'Scottish Charity Register',
        'is_cic': '',
        'name_origin': '09/2021 Name',
        'crossborder': '0',
        'iteration': '09/2021',
    }
    row.update(overrides)
    return row


class TestOSCRConsolidation:

    def test_crossborder_flag_carried_through(self):
        """Item 12 (OSCR half): any row in the group with crossborder set counts."""
        handler = OSCRDataHandler()
        r1 = make_oscr_row(crossborder='1')
        r2 = make_oscr_row(crossborder='0', organisationname='Older Name',
                           normalisedname='OLDER NAME', name_origin='01/2019 Name',
                           iteration='01/2019')
        sub_spine, extras = handler.combine_org_details_per_source([r1, r2])
        assert str(sub_spine['crossborder']) == '1'

    def test_crossborder_absent_when_never_set(self):
        handler = OSCRDataHandler()
        r1 = make_oscr_row(crossborder='0')
        r2 = make_oscr_row(crossborder='0', iteration='01/2019',
                           name_origin='01/2019 Name')
        sub_spine, extras = handler.combine_org_details_per_source([r1, r2])
        assert str(sub_spine.get('crossborder', '')) != '1'

    def test_registration_date_is_chronologically_earliest(self):
        """Item 5 end-to-end: {01/02/2020, 30/11/2019} must give 30/11/2019
        as the (earliest) registration date, not the text-sorted answer."""
        handler = OSCRDataHandler()
        r1 = make_oscr_row(registerdate='01/02/2020')
        r2 = make_oscr_row(registerdate='30/11/2019', iteration='01/2019',
                           name_origin='01/2019 Name')
        sub_spine, extras = handler.combine_org_details_per_source([r1, r2])
        assert sub_spine['registerdate'] == '30/11/2019'

    def test_undated_name_origin_does_not_crash_consolidation(self):
        """Item 3 end-to-end: plain 'Name' (no date) must not crash."""
        handler = OSCRDataHandler()
        r1 = make_oscr_row(name_origin='Name')
        r2 = make_oscr_row(organisationname='Second Name',
                           normalisedname='SECOND NAME',
                           name_origin='09/2021 Known As')
        sub_spine, extras = handler.combine_org_details_per_source([r1, r2])
        assert sub_spine['organisationname'] == 'Scottish Charity'

    def test_equal_iteration_variants_ignore_input_order(self):
        handler = OSCRDataHandler()
        rows = [
            make_oscr_row(
                organisationname='Zulu Scottish Charity',
                normalisedname='ZULU SCOTTISH CHARITY',
                fulladdress='9 ZULU STREET',
            ),
            make_oscr_row(
                organisationname='Alpha Scottish Charity',
                normalisedname='ALPHA SCOTTISH CHARITY',
                fulladdress='1 ALPHA STREET',
            ),
        ]

        forward = handler.combine_org_details_per_source(deepcopy(rows))
        reverse = handler.combine_org_details_per_source(
            list(reversed(deepcopy(rows)))
        )

        assert forward == reverse
        assert forward[0]['organisationname'] == 'Alpha Scottish Charity'
        assert forward[0]['fulladdress'] == '1 ALPHA STREET'


# ---------------------------------------------------------------------------
# Item 9: address must only lose a TRAILING city, never be split mid-address
# ---------------------------------------------------------------------------

class TestSortAddressFields:

    def make_row(self, fulladdress, city):
        return {
            'uid': 'GB-TEST-1',
            'organisationname': 'Test Org',
            'fulladdress': fulladdress,
            'city': city,
            'postcode': 'G1 1AA',
            'source': 'CCEW',
        }

    def test_city_inside_address_left_intact(self):
        row = self.make_row('12 Glasgow Road', 'Glasgow')
        DataHandler().sort_address_fields(row)
        assert row['fulladdress'] == '12 GLASGOW ROAD'

    def test_trailing_city_removed(self):
        row = self.make_row('12 High Street, Glasgow', 'Glasgow')
        DataHandler().sort_address_fields(row)
        assert row['fulladdress'] == '12 HIGH STREET'

    def test_city_mid_address_and_trailing(self):
        row = self.make_row('12 Glasgow Road, Glasgow', 'Glasgow')
        DataHandler().sort_address_fields(row)
        assert row['fulladdress'] == '12 GLASGOW ROAD'

    def test_city_as_word_suffix_not_removed(self):
        # 'YORK' at the end of 'NEWYORK' is not the city YORK
        row = self.make_row('12 Newyork', 'York')
        DataHandler().sort_address_fields(row)
        assert row['fulladdress'] == '12 NEWYORK'

    def test_empty_city_leaves_address_alone(self):
        row = self.make_row('12 High Street', '')
        DataHandler().sort_address_fields(row)
        assert row['fulladdress'] == '12 HIGH STREET'

    @pytest.mark.parametrize(
        "corrupt_prefix",
        ['\x84\n ', '\xc2\x84\n ', '\xc2\u201e\u2026 '],
    )
    def test_confirmed_legacy_care_of_prefix_is_normalised(self, corrupt_prefix):
        row = self.make_row(corrupt_prefix + '10 High Street', '')
        DataHandler().sort_address_fields(row)
        assert row['fulladdress'] == '℅ 10 HIGH STREET'


# ---------------------------------------------------------------------------
# Item 1: consolidation failures must not silently drop organisations
# ---------------------------------------------------------------------------

class FailingHandler(DataHandler):
    tmp_fields = []

    def combine_org_details_per_source(self, rows):
        raise ValueError('synthetic failure')


class TestCompressOrgDetailsFailure:

    def test_runtime_error_raised_when_org_fails(self, tmp_path):
        csv_in = tmp_path / 'input.csv'
        with open(csv_in, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['uid', 'organisationname', 'source'])
            writer.writeheader()
            writer.writerow({'uid': 'GB-X-1', 'organisationname': 'A', 'source': 'test'})
            writer.writerow({'uid': 'GB-X-1', 'organisationname': 'B', 'source': 'test'})
        spine_out = tmp_path / 'spine.csv'
        with pytest.raises(RuntimeError) as excinfo:
            compress_org_details(str(csv_in), str(spine_out), FailingHandler())
        assert 'GB-X-1' in str(excinfo.value)
        assert '1 organisation(s)' in str(excinfo.value)


# ---------------------------------------------------------------------------
# Item 8: recency-preserving deduplication of monthly files
# ---------------------------------------------------------------------------

class TestIterationDedup:

    def test_parse_iteration_tag_compares_year_first(self):
        assert parse_iteration_tag('02/2024') > parse_iteration_tag('03/2023')

    def test_bare_year_is_oldest_point_in_year(self):
        assert parse_iteration_tag('2022') == datetime(2022, 1, 1)
        assert parse_iteration_tag('2022') < parse_iteration_tag('02/2022')

    def test_daily_refresh_beats_monthly_snapshot(self):
        assert parse_iteration_tag('18/07/2026') > parse_iteration_tag(
            '07/2026'
        )

    def test_blank_and_garbage_treated_as_oldest(self):
        assert parse_iteration_tag('') == datetime(1900, 1, 1)
        assert parse_iteration_tag(None) == datetime(1900, 1, 1)
        assert parse_iteration_tag('notadate') == datetime(1900, 1, 1)

    def test_drop_duplicates_keeps_latest_iteration(self, tmp_path):
        f = tmp_path / 'data.csv'
        pd.DataFrame({
            'Name': ['Org1', 'Org1', 'Org2'],
            'Iteration': ['03/2023', '02/2024', '2022'],
        }).to_csv(f, index=False)
        drop_duplicates(str(f))
        result = pd.read_csv(f)
        assert len(result) == 2
        org1 = result[result['Name'] == 'Org1']
        # text sorting would keep 03/2023; chronological must keep 02/2024
        assert org1['Iteration'].iloc[0] == '02/2024'


# ---------------------------------------------------------------------------
# Item 11: unknown Companies House categories must fail loudly
# ---------------------------------------------------------------------------

class TestCompaniesHouseCategories:

    def test_known_include_category_passes(self):
        h = CompaniesHouseDataHandler()
        assert h.all_filters({'CompanyCategory': 'Community Interest Company'}) is True
        h.raise_for_unknown_categories()  # nothing unknown - must not raise

    def test_known_exclude_category_filtered(self):
        h = CompaniesHouseDataHandler()
        assert h.all_filters({'CompanyCategory': 'Private Limited Company'}) is False
        h.raise_for_unknown_categories()

    def test_unknown_category_collected_and_raises(self):
        h = CompaniesHouseDataHandler()
        assert h.all_filters({'CompanyCategory': 'Brand New Category'}) is False
        assert h.all_filters({'CompanyCategory': 'Brand New Category'}) is False
        with pytest.raises(RuntimeError) as excinfo:
            h.raise_for_unknown_categories()
        assert 'Brand New Category' in str(excinfo.value)
        assert '2 rows' in str(excinfo.value)


# ---------------------------------------------------------------------------
# Item 13: CCNI name-stripping only from the start of the address
# ---------------------------------------------------------------------------

class TestFindPostcode:

    def test_name_stripped_from_start(self):
        address, postcode = find_postcode(
            'Charity X, Bangor Road, Bangor, BT19 1AB', 'Charity X')
        assert postcode == 'BT19 1AB'
        assert address == 'Bangor Road, Bangor'

    def test_name_inside_address_left_intact(self):
        address, postcode = find_postcode(
            '10 Bangor Road, Bangor, BT19 1AB', 'Bangor')
        assert postcode == 'BT19 1AB'
        assert address == '10 Bangor Road, Bangor'


# ---------------------------------------------------------------------------
# Item 16: Companies House map_date must call strptime correctly
# ---------------------------------------------------------------------------

class TestCompaniesHouseMapDate:

    def test_map_date_roundtrip(self):
        assert CompaniesHouseDataHandler().map_date('01/02/2020') == '01/02/2020'

    def test_map_date_empty(self):
        assert CompaniesHouseDataHandler().map_date('') == ''


# ---------------------------------------------------------------------------
# CCNI company numbers: the download publishes a bare integer ('0' when the
# charity is not a company); the spine needs the Companies House NI form.
# ---------------------------------------------------------------------------

class TestNormaliseCCNICompanyNumber:

    def test_not_a_company_is_blank(self):
        assert normalise_ccni_company_number('0') == ''

    def test_blank_is_blank(self):
        assert normalise_ccni_company_number('') == ''

    def test_six_digits_kept_as_is(self):
        assert normalise_ccni_company_number('652013') == 'NI652013'

    def test_five_digits_zero_padded(self):
        assert normalise_ccni_company_number('43374') == 'NI043374'

    def test_three_digits_zero_padded(self):
        assert normalise_ccni_company_number('306') == 'NI000306'

    def test_more_than_six_digits_is_not_an_ni_number(self):
        assert normalise_ccni_company_number('1029207') == ''

    def test_non_numeric_is_blank(self):
        assert normalise_ccni_company_number('abc') == ''

    def test_repeated_digit_filler_is_blank(self):
        # keyboard junk, not a company number
        assert normalise_ccni_company_number('111111') == ''
        assert normalise_ccni_company_number('999999') == ''
        assert normalise_ccni_company_number('99999') == ''

    def test_surrounding_whitespace_stripped(self):
        assert normalise_ccni_company_number(' 652013 ') == 'NI652013'

    def test_all_zeros_is_blank(self):
        assert normalise_ccni_company_number('000000') == ''

    def test_none_is_blank(self):
        assert normalise_ccni_company_number(None) == ''


class TestCCNICompanyIdCarriedThrough:
    # The base consolidation helper takes identifiers from whichever row happens
    # to be last in the group; for CCNI that is usually a removals row or an older
    # snapshot with no company number. CCNI takes the FIRST nonblank company number
    # instead, so that the proven 2024 seed value beats a contradictory value in a
    # later CCNI download (see handler/ccni.py).

    def _row(self, **overrides):
        row = {
            'uid': 'GB-NIC-107323',
            'id_in_source': '107323',
            'organisationname': 'Oak Counselling Services Ltd',
            'normalisedname': 'OAK COUNSELLING SERVICES LTD',
            'companyid': '',
            'fulladdress': '51 Strand Road',
            'city': 'Londonderry',
            'postcode': 'BT48 7BN',
            'registerdate': '10/02/2020',
            'removeddate': '',
            'source': 'ccni',
            'source_register': 'Charity Commission for Northern Ireland',
            'is_cic': '',
            'iteration': '01/2024',
        }
        row.update(overrides)
        return row

    def test_first_nonblank_companyid_wins(self):
        # blank seed rows and a trailing removals row must not wipe the number
        rows = [
            self._row(iteration='01/2024', companyid=''),
            self._row(iteration='07/2026', companyid='NI652013'),
            self._row(iteration='07/2026', companyid='', removeddate='29/01/2024'),
        ]
        sub_spine_row, _ = CCNIDataHandler().combine_org_details_per_source(rows)
        assert sub_spine_row['companyid'] == 'NI652013'

    def test_seed_value_beats_a_contradictory_download_value(self):
        # real case: charity 107859, seed NI649994 against a truncated '64999'
        # in the July 2026 download
        rows = [
            self._row(iteration='01/2024', companyid='NI649994'),
            self._row(iteration='07/2026', companyid='NI064999'),
        ]
        sub_spine_row, _ = CCNIDataHandler().combine_org_details_per_source(rows)
        assert sub_spine_row['companyid'] == 'NI649994'

    def test_blank_stays_blank_when_no_row_has_one(self):
        rows = [self._row(iteration='01/2024'), self._row(iteration='07/2026')]
        sub_spine_row, _ = CCNIDataHandler().combine_org_details_per_source(rows)
        assert sub_spine_row['companyid'] == ''



# ---------------------------------------------------------------------------
# CCNI charities whose self-declared company number names a different company
# ---------------------------------------------------------------------------

class TestCCNIKnownBadCompanyNumbers:

    SEED_FIELDS = ['uid', 'charitynumber', 'organisationname', 'normalisedname',
                   'companyid', 'housenumber', 'address', 'city', 'localauthority',
                   'postcode', 'registerdate', 'removeddate', 'source', 'iteration']
    DOWNLOAD_FIELDS = ['Reg charity number', 'Charity name', 'Date registered',
                       'Status', 'Public address', 'Company number']

    def run_process_ccni(self, tmp_path, monkeypatch, download_rows):
        # process_ccni() reads '../raw_data/ccni/...' and writes
        # '../raw_data/ccni.all.csv' relative to the working directory, so give it a
        # throwaway working directory with its own sibling raw_data tree. The real
        # ../raw_data is never touched.
        raw = tmp_path / 'raw_data' / 'ccni'
        raw.mkdir(parents=True)
        work = tmp_path / 'work'
        work.mkdir()

        with open(raw / 'ccni_spine.csv', 'w', newline='', encoding='utf-8-sig') as fh:
            csv.DictWriter(fh, fieldnames=self.SEED_FIELDS).writeheader()
        with open(raw / 'register_charitydetails_2026_07_18.csv', 'w',
                  newline='', encoding='Latin-1') as fh:
            writer = csv.DictWriter(fh, fieldnames=self.DOWNLOAD_FIELDS)
            writer.writeheader()
            writer.writerows(download_rows)

        monkeypatch.chdir(work)
        process_ccni()

        with open(tmp_path / 'raw_data' / 'ccni.all.csv', newline='',
                  encoding='utf8') as fh:
            return {row['charitynumber']: row['companyid']
                    for row in csv.DictReader(fh)}

    def download_row(self, charity_number, company_number, name='A Charity'):
        return {'Reg charity number': charity_number,
                'Charity name': name,
                'Date registered': '10Feb2020',
                'Status': 'Registered',
                'Public address': '1 High Street, Belfast, BT1 1AA',
                'Company number': company_number}

    def test_mapping_documents_the_two_verified_cases(self):
        assert CCNI_KNOWN_BAD_COMPANY_NUMBERS == {'108557': 'NI653679',
                                                  '108948': 'NI056404'}

    def test_known_bad_value_is_suppressed(self, tmp_path, monkeypatch, capsys):
        rows = [self.download_row('108557', '653679',
                                  'Healthy Living Centres Alliance Ltd'),
                self.download_row('108948', '56404',
                                  'Pomeroy Development Projects Ltd')]

        result = self.run_process_ccni(tmp_path, monkeypatch, rows)

        assert result['108557'] == ''
        assert result['108948'] == ''
        # the suppression is visible in the build log
        printed = capsys.readouterr().out
        assert ('CCNI known-bad company number suppressed for charity 108557: '
                'NI653679') in printed
        assert ('CCNI known-bad company number suppressed for charity 108948: '
                'NI056404') in printed

    def test_a_corrected_value_for_the_same_charity_passes_through(
            self, tmp_path, monkeypatch, capsys):
        # NI653799 is the charity's real company; if CCNI corrects the field the
        # value must flow through with no code change
        rows = [self.download_row('108557', '653799',
                                  'Healthy Living Centres Alliance Ltd')]

        result = self.run_process_ccni(tmp_path, monkeypatch, rows)

        assert result['108557'] == 'NI653799'
        assert 'known-bad' not in capsys.readouterr().out

    def test_an_unlisted_charity_is_unaffected(self, tmp_path, monkeypatch):
        rows = [self.download_row('100001', '652013'),
                self.download_row('100002', '0')]

        result = self.run_process_ccni(tmp_path, monkeypatch, rows)

        assert result['100001'] == 'NI652013'
        assert result['100002'] == ''
