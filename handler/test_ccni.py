import pytest

from .ccni import CCNIDataHandler
from .base_definitions import sub_spine_entry_creator, extra_csv_entry_creator, SUB_SPINE_CSV_FIELDS
from .base import compress_org_details
import csv
import tempfile

import copy

def remove_empty_values(d):
    '''remove keys from dictionary d if d[key]==''
    '''
    return {k: v for k, v in d.items() if v != ''}

def ccni_entry_creator(overrides):
    entry = {
    "uid" : '',
    "charitynumber" : '',
    "organisationname" : '',
    "normalisedname" : '',
    "companyid" : '',
    "housenumber" : '',
    "address" : '',
    "city" : '',
    "localauthority" : '',
    "postcode" : '',
    "registerdate" : '',
    "source" : ''}
    entry.update(**overrides)
    return entry


@pytest.fixture
def setup_data_ccni_format():
    # data from the ccni input file
    base_row = ccni_entry_creator({
    "charitynumber" : '101',
    "organisationname" : '101 Trust Fund',
    "companyid" : '80000',
    "housenumber" : '1',
    "address" : 'Trust Fund Lane, Lincoln',
    "city" : 'Lincoln',
    "postcode" : 'LL1 1LL',
    "registerdate" : '18jun2014',
    "source" : 'ccni'
     })

    row1 = copy.deepcopy(base_row)

    row2 = copy.deepcopy(base_row)
    row2['organisationname'] = 'A Previous Name'

    row3 = copy.deepcopy(base_row)
    row3['addressline1'] = 'A Previous Address'


    return [row1, row2, row3]



@pytest.fixture
def setup_data_intermediate_file():
    base_row = sub_spine_entry_creator({
        "uid" : "GB-NIC-101",
        "organisationname" : "101 Trust Fund",
        "normalisedname" : "101 TRUST FUND",
        "fulladdress" : "1 Trust Fund Lane",
        "city" : "Lincoln",
        "postcode" : "LL1 1LL",
        "companyid" : "",
        "registerdate" : "23/06/1961",
        "removeddate" : "23/06/2019",
        'name_origin' : '2017 name',
        'iteration':'2017',
        "source" : "ccni",
        "id_in_source" : "101",

    })
    
    row1 = copy.deepcopy(base_row)

    row2 = copy.deepcopy(base_row)
    row2['name_origin'] = '2012 name'
    row2['iteration'] = '2012'
    row2['organisationname'] = 'Previous Trust Fund'
    row2['normalisedname'] = 'PREVIOUS TRUST FUND'


    row3 = copy.deepcopy(base_row)
    row3['name_origin'] = ''
    row3['iteration'] = '2012'
    row3['fulladdress'] = '33 Previous Address Road'
    

    return [row1, row2, row3]

'''

def test_combining_details_subspine(setup_data_intermediate_file):
    datarows = setup_data_intermediate_file
    print(f'datarows = {datarows}')
    subspine,e = CCNIDataHandler().combine_org_details_per_source(datarows)


    expected_subspine = sub_spine_entry_creator({'city': 'Lincoln',
    'companyid': '',
    'fulladdress': '1 Trust Fund Lane',
    'id_in_source': '101',
    "organisationname" : "101 Trust Fund",
    "normalisedname" : "101 TRUST FUND",
    'postcode': 'LL1 1LL',
    'registerdate':"23/06/1961",
    'removeddate': "23/06/2019",
    'source': 'ccni',
    'uid': 'GB-NIC-101'}
)
    assert subspine == expected_subspine
'''


def test_combining_details_extra_rows(setup_data_intermediate_file):
    datarows = setup_data_intermediate_file
    print(f'datarows = {datarows}')
    s,extrarows = CCNIDataHandler().combine_org_details_per_source(datarows[0])
    print(s)
    print(extrarows)
    
    assert extrarows == ''
    

def test_row_formatting(setup_data_ccni_format):
    ccni_data = setup_data_ccni_format

    expected_row = sub_spine_entry_creator({
        'uid': 'GB-NIC-101',
        "organisationname" : '101 Trust Fund',
        "normalisedname" : '101 TRUST FUND',
        "companyid" : '80000',
        "charitynumber" : '101',
        "fulladdress" : '1, TRUST FUND LANE',
        "city" : 'LINCOLN',
        "postcode" : 'LL1 1LL',
        "registerdate" : '18/06/2014',
        "source" : 'ccni',
        "id_in_source" : '101'})


    formatted_row = CCNIDataHandler().format_row('organisationname',ccni_data[0])

    # ignore items in dictionaries where values are empty
    d1 = remove_empty_values(formatted_row)
    d2 = remove_empty_values(expected_row)

    assert d1 == d2



