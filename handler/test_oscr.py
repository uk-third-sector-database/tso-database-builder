import pytest

from .oscr import OSCRDataHandler
from .base_definitions import sub_spine_entry_creator, extra_csv_entry_creator, SUB_SPINE_CSV_FIELDS
from .base import compress_org_details
import csv
import tempfile

import copy

def remove_empty_values(d):
    return {k: v for k, v in d.items() if v != ''}

def oscr_entry_creator(overrides):
    entry = {
    "uid" : '',
    "charitynumber" : '',
    "organisationname" : '',
    "normalisedname" : '',
    "companyid" : '',
    "address" : '',
    "housenumber" : '',
    "addressline1" : '',
    "addressline2" : '',
    "addressline3" : '',
    "addressline4" : '',
    "addressline5" : '',
    "addressline6" : '',
    "addressline7" : '',
    "addressline8" : '',
    "city" : '',
    "localauthority" : '',
    "postcode" : '',
    "registerdate" : '',
    "removeddate" : '',
    "name_origin" : '',
    "iteration" : '',
    "charitynumber_2012" : '',
    "companyid1_2012" : '',
    "companyid2_2012" : '',
    "companyid3_2012" : '',
    "source" : '',
    "crossborder" : ''
    }
    entry.update(**overrides)
    return entry


@pytest.fixture
def setup_data_oscr_format():
    # data from the oscr input file
    base_row = oscr_entry_creator({
    "charitynumber" : '101',
    "organisationname" : '101 Trust Fund',
    "companyid" : '80000',
    "addressline1" : '1 Trust Fund Lane',
    "addressline2" : 'Lincoln',
    "city" : 'Lincoln',
    "postcode" : 'LL1 1LL',
    "registerdate" : '23jun1961',
    "removeddate" : '23jun2019',
    "source" : 'oscr',
    'iteration':'2017',
    'name_origin' : '2017 name'
     })

    row1 = copy.deepcopy(base_row)

    row2 = copy.deepcopy(base_row)
    row2['name_origin'] = ''
    row2['organisationname'] = 'A Previous Name'

    row3 = copy.deepcopy(base_row)
    row3['name_origin'] = ''
    row3['addressline1'] = 'A Previous Address'


    return [row1, row2, row3]



@pytest.fixture
def setup_data_intermediate_file():
    base_row = sub_spine_entry_creator({
        "uid" : "GB-SC-101",
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
        "source" : "oscr",
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


@pytest.fixture
def setup_data_subspine_files():
    base_row_ss = sub_spine_entry_creator({})

    row1 = copy.deepcopy(base_row_ss)
    row2 = copy.deepcopy(base_row_ss)
    row3 = copy.deepcopy(base_row_ss)

    base_row_supp = extra_csv_entry_creator({})

    row4 = copy.deepcopy(base_row_supp)
    row5 = copy.deepcopy(base_row_supp)
    row6 = copy.deepcopy(base_row_supp)

    return [row1, row2, row3] , [row4, row5, row6]


def test_combining_details_subspine(setup_data_intermediate_file):
    datarows = setup_data_intermediate_file
    print(f'datarows = {datarows}')
    subspine,e = OSCRDataHandler().combine_org_details_per_source(datarows)


    expected_subspine = sub_spine_entry_creator({'city': 'Lincoln',
    'companyid': '',
    'fulladdress': '1 Trust Fund Lane',
    'id_in_source': '101',
    "organisationname" : "101 Trust Fund",
    "normalisedname" : "101 TRUST FUND",
    'postcode': 'LL1 1LL',
    'registerdate':"23/06/1961",
    'removeddate': "23/06/2019",
    'source': 'oscr',
    'uid': 'GB-SC-101'}
)
    assert subspine == expected_subspine

def test_combining_details_extra_rows(setup_data_intermediate_file):
    datarows = setup_data_intermediate_file
    print(f'datarows = {datarows}')
    s,extrarows = OSCRDataHandler().combine_org_details_per_source(datarows)
    
    expected_extrarows = []
    expected_extrarows.append(extra_csv_entry_creator({
    'normalisedname': 'PREVIOUS TRUST FUND',
    'organisationname': 'Previous Trust Fund',
    'uid': 'GB-SC-101',
    'source': 'oscr',}))
    expected_extrarows.append(extra_csv_entry_creator({'city': 'Lincoln',
    'fulladdress': '33 Previous Address Road',
    'postcode': 'LL1 1LL',
    'uid': 'GB-SC-101',
    'source': 'oscr',}))

    print(f'extrarows = {extrarows}')
    print(f'expected_extrarows = {expected_extrarows}')
    assert sorted(extrarows, key=lambda x: sorted(x.items())) == sorted(expected_extrarows, key=lambda x: sorted(x.items()))
   

def test_date_logic_regdate_primary(setup_data_intermediate_file):
    row1,row2,row3 = setup_data_intermediate_file
    row2['registerdate'] = '30/06/1980'
    row3['registerdate'] = "10/1/1960"
    subspine_row,extrarows = OSCRDataHandler().combine_org_details_per_source([row1,row2,row3])

    expected_subspine = sub_spine_entry_creator({'city': 'Lincoln',
    'companyid': '',
    'fulladdress': '1 Trust Fund Lane',
    'id_in_source': '101',
    "organisationname" : "101 Trust Fund",
    "normalisedname" : "101 TRUST FUND",
    'postcode': 'LL1 1LL',
    'registerdate':"10/1/1960",
    'removeddate': "23/06/2019",
    'source': 'oscr',
    'uid': 'GB-SC-101'})

    assert subspine_row == expected_subspine
    
def test_date_logic_date_extras(setup_data_intermediate_file):
    row1,row2,row3 = setup_data_intermediate_file
    row2['registerdate'] = '30/06/1980'
    row2['removeddate'] = '30/06/2020'
    row3['registerdate'] = "10/1/1960"
    subspine_row,extrarows = OSCRDataHandler().combine_org_details_per_source([row1,row2,row3])
    expected_extrarows = []
    expected_extrarows.append(extra_csv_entry_creator({'city': '',
    'fulladdress': '',
    'normalisedname': 'PREVIOUS TRUST FUND',
    'organisationname': 'Previous Trust Fund',
    'postcode': '',
    'registerdate': '',
    'removeddate': '',
    'uid': 'GB-SC-101',
    'source': 'oscr',}))
    expected_extrarows.append(extra_csv_entry_creator({'city': 'Lincoln',
    'fulladdress': '33 Previous Address Road',
    'normalisedname': '',
    'organisationname': '',
    'postcode': 'LL1 1LL',
    'registerdate': '',
    'removeddate': '',
    'uid': 'GB-SC-101',
    'source': 'oscr',}))
    expected_extrarows.append(extra_csv_entry_creator({'city': '',
    'fulladdress': '',
    'normalisedname': '',
    'organisationname': '',
    'postcode': '',
    'registerdate': '23/06/1961',
    'removeddate': '',
    'uid': 'GB-SC-101',
    'source': 'oscr',}))
    expected_extrarows.append(extra_csv_entry_creator({'city': '',
    'fulladdress': '',
    'normalisedname': '',
    'organisationname': '',
    'postcode': '',
    'registerdate': '30/06/1980',
    'removeddate': '',
    'uid': 'GB-SC-101',
    'source': 'oscr',}))
    expected_extrarows.append(extra_csv_entry_creator({'city': '',
    'fulladdress': '',
    'normalisedname': '',
    'organisationname': '',
    'postcode': '',
    'registerdate': '',
    'removeddate': '23/06/2019',
    'uid': 'GB-SC-101',
    'source': 'oscr',}))

    assert sorted(extrarows, key=lambda x: sorted(x.items())) == sorted(expected_extrarows, key=lambda x: sorted(x.items()))
   

def test_row_formatting(setup_data_oscr_format):
    oscr_data = setup_data_oscr_format

    expected_row = sub_spine_entry_creator({
        'uid': 'GB-SC-101',
        "organisationname" : '101 Trust Fund',
        "normalisedname" : '101 TRUST FUND',
        "companyid" : '80000',
        "fulladdress" : '1 TRUST FUND LANE',
        "city" : 'LINCOLN',
        "postcode" : 'LL1 1LL',
        "registerdate" : '23/06/1961',
        "removeddate" : '23/06/2019',
        "source" : 'oscr',
        'iteration':'2017',
        'name_origin' : '2017 name',
        "id_in_source" : '101'})


    formatted_row = OSCRDataHandler().format_row('organisationname',oscr_data[0])

    # ignore items in dictionaries where values are empty
    d1 = remove_empty_values(formatted_row)
    d2 = remove_empty_values(expected_row)

    assert d1 == d2




def test_find_primary_name():
    n1 = ('Primary Name','PRIMARY NAME','2012 name')
    n2 = ('Other Name','OTHER NAME','')
    n3 = ('Other Name 2','OTHER NAME 2','')
    names = [n3,n2,n1]

    primary, additional = OSCRDataHandler().find_primary_name(names) 
    assert primary == n1[:-1]
    assert additional.sort() == [n3,n2].sort()


def test_find_no_primary_name():
    n1 = ('Primary Name','PRIMARY NAME','')
    n2 = ('Other Name','OTHER NAME','')
    n3 = ('Other Name 2','OTHER NAME 2','')
    names = [n3,n2,n1]

    primary, additional = OSCRDataHandler().find_primary_name(names) 
    assert primary == ('','')
    assert additional.sort() == [n1,n3,n2].sort()


def test_find_primary_name_when_multiple():
    n1 = ('Primary Name','PRIMARY NAME','2012 name')
    n2 = ('Other Name','OTHER NAME','2020 name')
    n3 = ('Other Name 2','OTHER NAME 2','2023 name')
    names = [n3,n2,n1]

    primary, additional = OSCRDataHandler().find_primary_name(names) 
    assert primary == n3[:-1]
    assert additional.sort() == [n1,n2].sort()



def test_find_primary_address():
    n1 = ('Primary address','TOWN','PC','2023')
    n2 = ('Other address','','','2012')
    n3 = ('Other address 2','','','')
    addresses = {n3,n2,n1}

    primary, additional = OSCRDataHandler().find_primary_info(addresses) 
    assert primary == n1[:-1]
    assert additional.sort() == [n3,n2].sort()


def test_find_primary_address_3_options():
    n1 = ('Primary address','TOWN','PC','2023')
    n2 = ('Other address','','','2012')
    n3 = ('Other address 2','','','2020')
    addresses = {n3,n2,n1}

    primary, additional = OSCRDataHandler().find_primary_info(addresses) 
    assert primary == n1[:-1]
    assert additional.sort() == [n3,n2].sort()
