# Tests for the CQC handler's support for CQC API files (acquire/cqc_api.py),
# which carry Companies House numbers, charity numbers and registration dates
# that the old care-directory downloads lack. All fixtures are tiny synthetic
# rows - no real data files are read.

import csv

import pytest

from handler.base import do_csv_processing
from handler.careQC import CQCDataHandler, normalise_company_number, PROVIDER_ID_FIELD


def make_api_row(**overrides):
    '''a row as read from a CQC API file written by acquire/cqc_api.py'''
    row = {
        PROVIDER_ID_FIELD: '1-101601999',
        'Provider name': 'Sunrise Care Ltd',
        'Also known as': '',
        'Brand ID': '',
        'Brand Name': '',
        'Ownership Type': 'Organisation',
        'Companies House Number': '4378206',
        'Charity Number': '1103190',
        'Address': '1 High Street',
        'City': 'Maidstone',
        'Postcode': 'ME16 9NT',
        'Local authority': 'Kent',
        'Region': 'South East',
        'Registration Status': 'Registered',
        'Registration Date': '2010-10-01',
        'Deregistration Date': '',
        'Iteration': '07/2026',
    }
    row.update(overrides)
    return row


def make_directory_row(**overrides):
    '''a row as read from the old care-directory CareQualityCommission.all.csv'''
    row = {
        'Name': 'Sunrise House',
        'Also known as': '',
        'Address': '1 High Street',
        'Postcode': 'ME16 9NT',
        'Provider name': 'Sunrise Care Ltd',
        'Local authority': 'Kent',
        PROVIDER_ID_FIELD: '1-101601999',
        'Iteration': '02/2025',
    }
    row.update(overrides)
    return row


class TestNormaliseCompanyNumber:

    def test_digit_only_zero_padded_to_8(self):
        assert normalise_company_number('4378206') == '04378206'

    def test_already_8_chars_unchanged(self):
        assert normalise_company_number('10723188') == '10723188'

    def test_excess_leading_zeros_trimmed_then_padded(self):
        # seen in the live API data: 10-digit values with extra leading zeros
        assert normalise_company_number('0000064296') == '00064296'

    def test_alpha_prefix_uppercased_kept(self):
        assert normalise_company_number('sc123456') == 'SC123456'

    def test_too_long_digit_value_dropped(self):
        assert normalise_company_number('123456789') == ''

    def test_blank(self):
        assert normalise_company_number('') == ''
        assert normalise_company_number(None) == ''


class TestFormatRowAPIFile:

    def test_companyid_and_charitynumber_populated(self):
        h = CQCDataHandler()
        new_row = h.format_row('Provider name', make_api_row())
        assert new_row['companyid'] == '04378206'
        assert new_row['charitynumber'] == '1103190'
        assert new_row['uid'] == 'GB-CQC-1-101601999'
        assert new_row['source'] == 'carequalitycommission'

    def test_iso_dates_converted(self):
        h = CQCDataHandler()
        new_row = h.format_row('Provider name', make_api_row(
            **{'Deregistration Date': '2016-09-06'}))
        assert new_row['registerdate'] == '01/10/2010'
        assert new_row['removeddate'] == '06/09/2016'

    def test_city_carried(self):
        h = CQCDataHandler()
        new_row = h.format_row('Provider name', make_api_row())
        assert new_row['city'] == 'MAIDSTONE'


class TestFormatRowDirectoryFileBackwardsCompatible:

    def test_old_columns_still_work_identifiers_blank(self):
        h = CQCDataHandler()
        new_row = h.format_row('Provider name', make_directory_row())
        assert new_row['companyid'] == ''
        assert new_row['charitynumber'] == ''
        assert new_row['registerdate'] == ''
        assert new_row['removeddate'] == ''
        assert new_row['uid'] == 'GB-CQC-1-101601999'
        assert new_row['organisationname'] == 'Sunrise Care Ltd'


class TestAllFilters:

    def test_repeated_header_row_dropped(self):
        # API files carry their header twice (line 1 for the handler, line 5 for
        # preprocess.fix_CQC_files); the echo reaches the handler as a data row
        h = CQCDataHandler()
        header_echo = {k: k for k in make_api_row()}
        assert h.all_filters(header_echo) is False

    def test_normal_row_kept(self):
        h = CQCDataHandler()
        assert h.all_filters(make_api_row()) is True


class TestEndToEndAPIFile:
    '''run the full do_csv_processing path on a small API-shape file, including
    the dual-header layout written by acquire/cqc_api.py, and check that
    companyid and charitynumber survive into the sub-spine CSV.'''

    def write_api_file(self, path, rows):
        fields = list(make_api_row().keys())
        with open(path, 'w', encoding='UTF8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()              # line 1: header (for the handler)
            f.write('\r\n' * 3)               # lines 2-4: truly blank (skipped by DictReader)
            writer.writerow({k: k for k in fields})   # line 5: header again (for preprocess)
            for row in rows:
                writer.writerow(row)

    def test_identifiers_reach_sub_spine_csv(self, tmp_path):
        infile = tmp_path / 'api_providers.csv'
        outfile = tmp_path / 'carequalitycommission.spine.csv'
        # two rows for the same provider (an AKA name), plus one with no identifiers
        self.write_api_file(infile, [
            make_api_row(),
            make_api_row(**{'Also known as': 'Sunrise'}),
            make_api_row(**{PROVIDER_ID_FIELD: '1-200000001',
                            'Provider name': 'Name Only Care',
                            'Companies House Number': '', 'Charity Number': ''}),
        ])
        do_csv_processing(str(infile), str(outfile), CQCDataHandler())

        with open(outfile, newline='') as f:
            out_rows = {r['uid']: r for r in csv.DictReader(f)}

        assert set(out_rows) == {'GB-CQC-1-101601999', 'GB-CQC-1-200000001'}
        with_ids = out_rows['GB-CQC-1-101601999']
        assert with_ids['companyid'] == '04378206'
        assert with_ids['charitynumber'] == '1103190'
        assert with_ids['registerdate'] == '01/10/2010'
        without_ids = out_rows['GB-CQC-1-200000001']
        assert without_ids['companyid'] == ''
        assert without_ids['charitynumber'] == ''

    def test_two_runs_in_one_session(self, tmp_path):
        # compress_org_details removes 'iteration' from the tmp_fields list it is
        # given; the handler must hand over an instance-level copy so a second
        # handler instance still works (the class attribute must stay intact)
        for i in (1, 2):
            infile = tmp_path / f'api_{i}.csv'
            outfile = tmp_path / f'out_{i}.spine.csv'
            self.write_api_file(infile, [make_api_row(), make_api_row(**{'Also known as': 'Sunrise'})])
            do_csv_processing(str(infile), str(outfile), CQCDataHandler())
        assert CQCDataHandler.tmp_fields == ['iteration', 'charitynumber']
