import pytest

from .careInspectScot import CareInspScotDataHandler  
from .base_definitions import sub_spine_entry_creator,extra_csv_entry_creator

import copy



def CIS_entry_creator(overrides):
    entry = {
        "CSNumber" :'',
        "Combined_Service_" :'',
        "CaseNumber_Combined" :'',
        "CareService" :'',
        "Subtype" :'',
        "Service" :'',
        "ServiceType"
        "ServiceName" :'',
        "Address_line_1" :'',
        "Address_line_2" :'',
        "Address_line_3" :'',
        "Address_line_4" :'',
        "Service_town" :'',
        "Service_Postcode" :'',
        "ManagerName" :'',
        "Council_Area_Name" : '',
        "Health_Board_Name" : '',
        "DateReg" : '',
        "Iteration" : '',
    }
    entry.update(**overrides)
    return entry



@pytest.fixture
def setup_data_CIS_format():
    # data from CIS  input file
    base_row = CIS_entry_creator({
        "CSNumber" : 'CS2003000137',
        "ServiceName" : 'East Park',
        "ServiceType" : 'Voluntary or Not for Profit',
        "Address_line_1" : '1092 Maryhill Road',
        "Service_town" : 'Glasgow',
        "Service_Postcode" : 'G20 9TD',
        "Council_Area_Name" : 'Glasgow City',
        "Health_Board_Name" : 'Greater Glasgow & Clyde',
        "DateReg" : '01/04/2002',
        "Iteration" : '2019',
    })

    row1 = copy.deepcopy(base_row)

    row2 = copy.deepcopy(base_row)
    row2['Iteration'] = '2018'
    row2['ServiceName'] = 'A Previous Name'

    row3 = copy.deepcopy(base_row)
    row3['addressline1'] = 'A Previous Address'
    row3['Iteration'] = '2016'


    return [row1, row2, row3]

@pytest.fixture
def setup_intermediate_file():
    base_row = sub_spine_entry_creator({
        'uid' : 'GB-CIS-CS2003000137',
        'organisationname' : 'East Park',
        'normalisedname' : 'EAST PARK',
        'fulladdress' : '1092 MARYHILL ROAD',
        'city' : 'GLASGOW',
        'postcode' : 'G20 9TD',
        'registerdate' : "01/04/2002",
        'source' : 'CareInspectorateScot',
        'id_in_source' : 'CS2003000137',
        'iteration' : '2019'
    })

    row1 = copy.deepcopy(base_row)

    row2 = copy.deepcopy(base_row)
    row2['iteration'] = '2018'
    row2['organisationname'] = 'A Previous Name'
    row2['normalisedname'] = 'A PREVIOUS NAME'
    row2['fulladdress'] = ''
    row2['city'] = ''
    row2['postcode'] = ''

    row3 = copy.deepcopy(base_row)
    row3['iteration'] = '2016'
    row3['fulladdress'] = 'A PREVIOUS ADDRESS'

    return [row1, row2, row3]


@pytest.mark.parametrize(
    "servicetype,expected",
    [("Private", False), ("Voluntary or Not for Profit", True)],
)
def test_filters(servicetype, expected):
    value = CIS_entry_creator({"ServiceType": servicetype})
    assert CareInspScotDataHandler().all_filters(value) == expected 



def test_row_formatting(setup_data_CIS_format,setup_intermediate_file):
    cis_row = setup_data_CIS_format
    int_row = setup_intermediate_file

    namefield = 'ServiceName'

    assert CareInspScotDataHandler().format_row(namefield,cis_row[0]) == int_row[0]



def test_combine_subspine_details(setup_intermediate_file):
    datarows = setup_intermediate_file
    subspine, e = CareInspScotDataHandler().combine_org_details_per_source(datarows)

    expected_row = datarows[0]
    expected_row.pop('iteration')
    assert subspine == expected_row



def test_combine_extra_details(setup_intermediate_file):
    datarows = setup_intermediate_file
    _, extrarows = CareInspScotDataHandler().combine_org_details_per_source(datarows)

    expected_extra_rows = []
    expected_extra_rows.append(extra_csv_entry_creator({
        'organisationname' : 'A Previous Name',
        'normalisedname' : 'A PREVIOUS NAME',
        'uid' : 'GB-CIS-CS2003000137'
    }))
    expected_extra_rows.append(extra_csv_entry_creator({
        'fulladdress' : 'A PREVIOUS ADDRESS',
        'city': 'GLASGOW',
        'postcode': 'G20 9TD',
        'uid' : 'GB-CIS-CS2003000137'
    }))
    assert sorted(extrarows, key=lambda x: sorted(x.items())) == sorted(expected_extra_rows, key=lambda x: sorted(x.items()))

def test_sort_by_iteration_date(setup_intermediate_file):
    datarows = setup_intermediate_file
    datarows[0]['iteration'] = '2010'
    # now most recent name is 'A previous name' and most recent address 'A previous address'

    expected_subspine = sub_spine_entry_creator({
        'uid' : 'GB-CIS-CS2003000137',
        'organisationname' : 'A Previous Name',
        'normalisedname' : 'A PREVIOUS NAME',
        'fulladdress' : 'A PREVIOUS ADDRESS',
        'city' : 'GLASGOW',
        'postcode' : 'G20 9TD',
        'registerdate' : "01/04/2002",
        'source' : 'CareInspectorateScot',
        'id_in_source' : 'CS2003000137',
    })
        
    subspine, e = CareInspScotDataHandler().combine_org_details_per_source(datarows)
    assert subspine == expected_subspine


def test_sort_by_iteration_date(setup_intermediate_file):
    datarows = setup_intermediate_file
    datarows[0]['iteration'] = '2010'
    # now most recent name is 'A previous name' and most recent address 'A previous address


    expected_extrarows = []
    expected_extrarows.append(extra_csv_entry_creator({
        'uid' : 'GB-CIS-CS2003000137',
        'organisationname' : 'East Park',
        'normalisedname' : 'EAST PARK',
    }))
    expected_extrarows.append(extra_csv_entry_creator({
        'uid' : 'GB-CIS-CS2003000137',
        'fulladdress' : '1092 MARYHILL ROAD',
        'city' : 'GLASGOW',
        'postcode' : 'G20 9TD',    
        }))
        
    _, extrarows = CareInspScotDataHandler().combine_org_details_per_source(datarows)
    assert sorted(extrarows, key=lambda x: sorted(x.items())) == sorted(expected_extrarows, key=lambda x: sorted(x.items()))
