import pytest

from .ccew import CCEWDataHandler
from .base_definitions import sub_spine_entry_creator, extra_csv_entry_creator, SUB_SPINE_CSV_FIELDS
from .base import compress_org_details


import copy

def ccew_entry_creator(overrides):
    entry = {
    "uid" : '',
    "charitynumber" : '',
    "organisationname" : '',
    "normalisedname" : '',
    "companyid" : '',
    "housenumber" : '',
    "addressline1" : '',
    "addressline2" : '',
    "addressline3" : '',
    "addressline4" : '',
    "addressline5" : '',
    "city" : '',
    "localauthority" : '',
    "postcode" : '',
    "registerdate" : '',
    "removeddate" : '',
    "name_origin" : '',
    "primary_name" : '',
    "address_origin" : '',
    "primary_address" : '',
    "regdate_origin" : '',
    "remdate_origin" : '',
    "iteration" : '',
    "source" : '',
    "cqc_reg" : ''
    }
    entry.update(**overrides)
    return entry


@pytest.fixture
def setup_data_ccew_format():
    # data from the ccew input file
    base_row = ccew_entry_creator({
    "charitynumber" : '101',
    "organisationname" : '101 Trust Fund',
    "companyid" : '80000',
    "addressline1" : '1 Trust Fund Lane',
    "addressline2" : 'Lincoln',
    "city" : 'Lincoln',
    "postcode" : 'LL1 1LL',
    "registerdate" : '23jun1961',
    "removeddate" : '23jun2019',
    "primary_name" : '1',
    "primary_address" : '1',
    "source" : 'ccew',
    "cqc_reg" : '1' })

    row1 = copy.deepcopy(base_row)

    row2 = copy.deepcopy(base_row)
    row2['primary_name'] = 0
    row2['primary_address'] = 0
    row2['organisationname'] = 'A Previous Name'

    row3 = copy.deepcopy(base_row)
    row3['primary_name'] = 0
    row3['primary_address'] = 0
    row3['addressline1'] = 'A Previous Address'


    return [row1, row2, row3]



@pytest.fixture
def setup_data_intermediate_file():
    base_row = sub_spine_entry_creator({
        "uid" : "GB-CHC-101",
        "organisationname" : "101 Trust Fund",
        "normalisedname" : "101 TRUST FUND",
        "fulladdress" : "1 Trust Fund Lane",
        "city" : "Lincoln",
        "postcode" : "LL1 1LL",
        "companyid" : "",
        "registerdate" : "23/06/1961",
        "removeddate" : "23/06/2019",
        "source" : "ccew",
        "id_in_source" : "101",

    })
    
    row1 = copy.deepcopy(base_row)
    row1['primary_name'] = '1'
    row1['primary_address'] = '1'

    row2 = copy.deepcopy(base_row)
    row2['primary_name'] = ''
    row2['primary_address'] = ''
    row2['organisationname'] = 'Previous Trust Fund'
    row2['normalisedname'] = 'PREVIOUS TRUST FUND'


    row3 = copy.deepcopy(base_row)
    row3['primary_name'] = ''
    row3['primary_address'] = ''
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
    subspine,e = CCEWDataHandler().combine_org_details_per_source(datarows)


    expected_subspine = sub_spine_entry_creator({'city': 'Lincoln',
    'companyid': '',
    'fulladdress': '1 Trust Fund Lane',
    'id_in_source': '101',
    "organisationname" : "101 Trust Fund",
    "normalisedname" : "101 TRUST FUND",
    'postcode': 'LL1 1LL',
    'registerdate':"23/06/1961",
    'removeddate': "23/06/2019",
    'source': 'ccew',
    'uid': 'GB-CHC-101'}
)
    assert subspine == expected_subspine

def test_combining_details_extra_rows(setup_data_intermediate_file):
    datarows = setup_data_intermediate_file
    print(f'datarows = {datarows}')
    s,extrarows = CCEWDataHandler().combine_org_details_per_source(datarows)
    
    expected_extrarows = []
    expected_extrarows.append(extra_csv_entry_creator({'city': '',
    'fulladdress': '',
    'normalisedname': 'PREVIOUS TRUST FUND',
    'organisationname': 'Previous Trust Fund',
    'postcode': '',
    'registerdate': '',
    'removeddate': '',
    'uid': 'GB-CHC-101',
    'source': 'ccew',}))
    expected_extrarows.append(extra_csv_entry_creator({'city': 'Lincoln',
    'fulladdress': '33 Previous Address Road',
    'normalisedname': '',
    'organisationname': '',
    'postcode': 'LL1 1LL',
    'registerdate': '',
    'removeddate': '',
    'uid': 'GB-CHC-101',
    'source': 'ccew',}))


    assert sorted(extrarows, key=lambda x: sorted(x.items())) == sorted(expected_extrarows, key=lambda x: sorted(x.items()))
   

def test_date_logic_regdate_primary(setup_data_intermediate_file):
    row1,row2,row3 = setup_data_intermediate_file
    row2['registerdate'] = '30/06/1980'
    row3['registerdate'] = "10/1/1960"
    subspine_row,extrarows = CCEWDataHandler().combine_org_details_per_source([row1,row2,row3])

    expected_subspine = sub_spine_entry_creator({'city': 'Lincoln',
    'companyid': '',
    'fulladdress': '1 Trust Fund Lane',
    'id_in_source': '101',
    "organisationname" : "101 Trust Fund",
    "normalisedname" : "101 TRUST FUND",
    'postcode': 'LL1 1LL',
    'registerdate':"10/1/1960",
    'removeddate': "23/06/2019",
    'source': 'ccew',
    'uid': 'GB-CHC-101'})

    assert subspine_row == expected_subspine
    
def test_date_logic_date_extras(setup_data_intermediate_file):
    row1,row2,row3 = setup_data_intermediate_file
    row2['registerdate'] = '30/06/1980'
    row2['removeddate'] = '30/06/2020'
    row3['registerdate'] = "10/1/1960"
    subspine_row,extrarows = CCEWDataHandler().combine_org_details_per_source([row1,row2,row3])
    expected_extrarows = []
    expected_extrarows.append(extra_csv_entry_creator({'city': '',
    'fulladdress': '',
    'normalisedname': 'PREVIOUS TRUST FUND',
    'organisationname': 'Previous Trust Fund',
    'postcode': '',
    'registerdate': '',
    'removeddate': '',
    'uid': 'GB-CHC-101',
    'source': 'ccew',}))
    expected_extrarows.append(extra_csv_entry_creator({'city': 'Lincoln',
    'fulladdress': '33 Previous Address Road',
    'normalisedname': '',
    'organisationname': '',
    'postcode': 'LL1 1LL',
    'registerdate': '',
    'removeddate': '',
    'uid': 'GB-CHC-101',
    'source': 'ccew',}))
    expected_extrarows.append(extra_csv_entry_creator({'city': '',
    'fulladdress': '',
    'normalisedname': '',
    'organisationname': '',
    'postcode': '',
    'registerdate': '23/06/1961',
    'removeddate': '',
    'uid': 'GB-CHC-101',
    'source': 'ccew',}))
    expected_extrarows.append(extra_csv_entry_creator({'city': '',
    'fulladdress': '',
    'normalisedname': '',
    'organisationname': '',
    'postcode': '',
    'registerdate': '30/06/1980',
    'removeddate': '',
    'uid': 'GB-CHC-101',
    'source': 'ccew',}))
    expected_extrarows.append(extra_csv_entry_creator({'city': '',
    'fulladdress': '',
    'normalisedname': '',
    'organisationname': '',
    'postcode': '',
    'registerdate': '',
    'removeddate': '23/06/2019',
    'uid': 'GB-CHC-101',
    'source': 'ccew',}))

    assert sorted(extrarows, key=lambda x: sorted(x.items())) == sorted(expected_extrarows, key=lambda x: sorted(x.items()))
   

def test_row_formatting(setup_data_ccew_format):
    ccew_data = setup_data_ccew_format

    expected_row = sub_spine_entry_creator({
        'uid': 'GB-CHC-101',
        "organisationname" : '101 Trust Fund',
        "normalisedname" : '101 TRUST FUND',
        "companyid" : '80000',
        "fulladdress" : '1 TRUST FUND LANE',
        "city" : 'LINCOLN',
        "postcode" : 'LL1 1LL',
        "registerdate" : '23/06/1961',
        "removeddate" : '23/06/2019',
        "primary_name" : '1',
        "primary_address" : '1',
        "source" : 'ccew',
        "id_in_source" : '101',
        "cqc_reg" : '1' })

    assert CCEWDataHandler().format_row('organisationname',ccew_data[0]) == expected_row




def test_find_primary_name():
    n1 = ('Primary Name','PRIMARY NAME','1')
    n2 = ('Other Name','OTHER NAME','')
    n3 = ('Other Name 2','OTHER NAME 2','')
    names = {n3,n2,n1}

    primary, additional = CCEWDataHandler().find_primary_info(names) 
    assert primary == n1[:-1]
    assert additional.sort() == [n3,n2].sort()


def test_find_no_primary_name():
    n1 = ('Primary Name','PRIMARY NAME','')
    n2 = ('Other Name','OTHER NAME','')
    n3 = ('Other Name 2','OTHER NAME 2','')
    names = {n3,n2,n1}

    primary, additional = CCEWDataHandler().find_primary_info(names) 
    assert primary == ('','')
    assert additional.sort() == [n1,n3,n2].sort()


def test_find_multiple_primary_name():
    n1 = ('Primary Name','PRIMARY NAME','1')
    n2 = ('Other Name','OTHER NAME','1')
    n3 = ('Other Name 2','OTHER NAME 2','')
    names = {n3,n2,n1}

    primary, additional = CCEWDataHandler().find_primary_info(names) 
    assert primary == ('','')
    assert additional.sort() == [n1,n3,n2].sort()


def test_find_primary_address():
    n1 = ('Primary address','TOWN','PC','1')
    n2 = ('Other address','','','')
    n3 = ('Other address 2','','','')
    addresses = {n3,n2,n1}

    primary, additional = CCEWDataHandler().find_primary_info(addresses) 
    assert primary == n1[:-1]
    assert additional.sort() == [n3,n2].sort()




'''


def test_row_formatting():
    row = ccew_entry_creator({
    "charitynumber" : '1234',
    "organisationname" : 'Something Name',
    "normalisedname" : '',
    "companyid" : '555',
    "housenumber" : 'A1',
    "addressline1" : 'This Street',
    "city":'Town',
    "postcode" : 'code',
    "source" : 'ccew'
   })

    namefield = 'organisationname'

    new_row = sub_spine_entry_creator({
    "uid" : 'GB-CHC-1234',
    "organisationname" : 'Something Name',
    "normalisedname": 'SOMETHING NAME',
    "fulladdress":'A1, THIS STREET',
    "city":'TOWN',
    "postcode":'code',
    "companyid" : '555',
    "source":'ccew',
    'id_in_source':'1234'
    })
    for field in CCEWDataHandler.tmp_fields:
        new_row[field] = ''
    assert CCEWDataHandler().format_row(namefield,row) == new_row




def test_row_formatting_addr_origin():
    row = ccew_entry_creator({
    "charitynumber" : '1234',
    "organisationname" : 'Something Name',
    "normalisedname" : '',
    "companyid" : '555',
    "housenumber" : 'A1',
    "addressline1" : 'This Street',
    "city":'Town',
    "postcode" : 'code',
    "source" : 'ccew',
    'address_origin' : '2001'
   })

    namefield = 'organisationname'

    new_row = sub_spine_entry_creator({
    "uid" : 'GB-CHC-1234',
    "organisationname" : 'Something Name',
    "normalisedname": 'SOMETHING NAME',
    "fulladdress":'A1, THIS STREET',
    "city":'TOWN',
    "postcode":'code',
    "companyid" : '555',
    "source":'ccew',
    'id_in_source':'1234'
    })
    for field in CCEWDataHandler.tmp_fields:
        new_row[field] = ''
    new_row['address_origin'] = '2001'

    assert CCEWDataHandler().format_row(namefield,row) == new_row


def test_row_formatting_addr_origin_other():
    row = ccew_entry_creator({
    "charitynumber" : '1234',
    "organisationname" : 'Something Name',
    "normalisedname" : '',
    "companyid" : '555',
    "housenumber" : 'A1',
    "addressline1" : 'This Street',
    "city":'Town',
    "postcode" : 'code',
    "source" : 'ccew',
    'address_origin' : 'other'
   })

    namefield = 'organisationname'

    new_row = sub_spine_entry_creator({
    "uid" : 'GB-CHC-1234',
    "organisationname" : 'Something Name',
    "normalisedname": 'SOMETHING NAME',
    "fulladdress":'A1, THIS STREET',
    "city":'TOWN',
    "postcode":'code',
    "companyid" : '555',
    "source":'ccew',
    'id_in_source':'1234'
    })
    for field in CCEWDataHandler.tmp_fields:
        new_row[field] = ''
    new_row['address_origin'] = '0'

    assert CCEWDataHandler().format_row(namefield,row) == new_row



def test_compress_details():

    # input data (intermediate ofile, as would be created in do_csv_processing format_row)
    base_row = sub_spine_entry_creator({
    "uid" : 'GB-CHC-1234',
    "organisationname" : 'Something Name',
    "normalisedname": 'SOMETHING NAME',
    "fulladdress":'A1, THIS STREET',
    "city":'TOWN',
    "postcode":'code',
    "companyid" : '555',
    "source":'ccew',
    'id_in_source':'1234',
    'name_origin' : '2001'})

    row1 = copy.deepcopy(base_row)
    row1['organisationname'] = 'Most Recent Name'
    row1['normalisedname'] = 'MOST RECENT NAME'
    row1['name_origin'] = '2014'

    row2 = copy.deepcopy(base_row)
    row2['organisationname'] = 'A previous name'
    row2['normalisedname'] = 'A PREVIOUS NAME'
    row2['name_origin'] = '0'

    row3 = copy.deepcopy(base_row)
    

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=SUB_SPINE_CSV_FIELDS+CCEWDataHandler.tmp_fields)
        writer.writeheader()
        writer.writerows([row1,row2,row3])
        csv_in = csvfile.name

    with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_csv:
        csv_out = temp_csv.name

    print(f'csv_in: {csv_in}, csv_out: {csv_out}')

    # carry out the function, which creates the .supplementary file as well as populating csv_out
    compress_org_details(csv_in, csv_out, CCEWDataHandler())

    details_csv_out = csv_out.split('.csv')[0] + '.supplementary.csv'

    # check that the function created the expected data
    spine_data = []
    with open(csv_in,'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            spine_data.append(row)
        
    details_data = []
    with open(details_csv_out,'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            details_data.append(row)

    # expected data
    uid = "GB-CHC-1234"
    spine_row = [sub_spine_entry_creator({
        "uid" : uid,
        "organisationname" : "Most Recent Name",
        "normalisedname" : "MOST RECENT NAME",
        "fulladdress" : "A1, THIS STREET",
        "city" : "TOWN",
        "postcode" : "code",
        "source":'ccew',
        "CHC_id" : "1234"})]
    

    extra_row1=extra_csv_entry_creator({"uid" : uid,
    "organisationname" : "A previous name",
    "normalisedname" : "A PREVIOUS NAME",
    "source" : "ccew"
    })

    extra_row2=extra_csv_entry_creator({"uid" : uid,
    "organisationname" : "Something Name",
    "normalisedname" : "SOMETHING NAME",
    "source" : "ccew"
    })

    extra_rows = [extra_row1,extra_row2]


    assert sorted(extra_rows, key=lambda x: sorted(x.items())) == sorted(details_data, key=lambda x: sorted(x.items()))
    assert sorted(spine_data, key=lambda x: sorted(x.items())) == sorted(spine_row, key=lambda x: sorted(x.items()))


def test_primary_name_matches_most_recent_name(setup_data_find_name):
    row1, row2, row3, expected_row, _ = setup_data_find_name

    s, _ = CCEWDataHandler().combine_org_details_per_source([row1, row2, row3,])
    s = sub_spine_entry_creator(s)

    assert sorted(s.items()) == sorted(expected_row.items())

def test_extra_rows_match_previous_and_original_name(setup_data_find_name):
    row1, row2, row3, _, extra_rows = setup_data_find_name
    print('setupdata = ',row1)
    print('expected = ',extra_rows)

    _, e = CCEWDataHandler().combine_org_details_per_source([row1, row2, row3])

    print('generated = ',e)
    assert sorted(e, key=lambda x: sorted(x.items())) == sorted(extra_rows, key=lambda x: sorted(x.items()))



@pytest.fixture
def setup_data_find_address():
    base_row = sub_spine_entry_creator({
        "uid": 'GB-CHC-1234',
        "organisationname": 'Something Name',
        "normalisedname": 'SOMETHING NAME',
        "fulladdress": 'A1, THIS STREET',
        "city": 'TOWN',
        "postcode": 'code',
        "companyid": '555',
        "source": 'ccew',
        'id_in_source': '1234',
        'address_origin': '2001'})

    row1 = copy.deepcopy(base_row)
    row1['fulladdress'] = 'Most Recent Address'
    row1['city'] = 'city'
    row1['postcode'] = 'AA1 888'
    row1['address_origin'] = '2014'

    row2 = copy.deepcopy(base_row)
    row2['fulladdress'] = 'A previous address'
    row2['city'] = ''
    row1['postcode'] = ''
    row2['address_origin'] = '0'

    row3 = copy.deepcopy(base_row)

    uid = "GB-CHC-1234"

    expected_subspine_row = sub_spine_entry_creator({
        "uid": uid,
        "organisationname": "Something Name",
        "normalisedname": "SOMETHING NAME",
        "fulladdress": "Most Recent Address",
        "city": "city",
        "postcode": "AA1 888",
        "companyid": '555',
        "source": 'ccew',
        'id_in_source': '1234',})

    extra_row1 = extra_csv_entry_creator({
        "uid": uid,
        "fulladdress": "A previous address",
        "source": 'ccew',
    })

    extra_row2 = extra_csv_entry_creator({
        "uid": uid,
        "fulladdress": "A1, THIS STREET",
        "city": 'TOWN',
        "postcode": 'code',
        "source": 'ccew',
    })

    expected_extra_rows = [extra_row1, extra_row2]

    return row1, row2, row3, expected_subspine_row, expected_extra_rows


def test_primary_address_matches_most_recent_address(setup_data_find_address):
    row1, row2, row3, expected_row, _ = setup_data_find_address

    s, _ = CCEWDataHandler().combine_org_details_per_source([row1, row2, row3,])
    s = sub_spine_entry_creator(s)

    assert sorted(s.items()) == sorted(expected_row.items())

def test_extra_rows_match_extra_addresses(setup_data_find_address):
    row1, row2, row3, _, extra_rows = setup_data_find_address

    _, e = CCEWDataHandler().combine_org_details_per_source([row1, row2, row3])

    print('generated = ',e)
    assert sorted(e, key=lambda x: sorted(x.items())) == sorted(extra_rows, key=lambda x: sorted(x.items()))

    '''