import pytest

from .careInspectScot import CareInspScotDataHandler  
from .base_definitions import spine_entry_creator



def CIS_entry_creator(overrides):
    entry = {
        "CSNumber" :'',
        "Combined_Service_" :'',
        "CaseNumber_Combined" :'',
        "CareService" :'',
        "Subtype" :'',
        "Service" :'',
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
    }
    entry.update(**overrides)
    return entry


@pytest.mark.parametrize(
    "servicetype,expected",
    [("Private", False), ("Voluntary or Not for Profit", True)],
)
def test_filters(servicetype, expected):
    value = CIS_entry_creator({"ServiceType": servicetype})
    assert CareInspScotDataHandler().all_filters(value) == expected 



def test_row_formatting():
    row = CIS_entry_creator({
        "CSNumber" :'1234',
        "ServiceName" :'Something Name',

})
    namefield = 'ServiceName'
    new_row = spine_entry_creator({
    "uid" : 'GB-CIS-1234',
    "organisationname" : 'Something Name',
    "normalisedname": 'SOMETHING NAME',
    "companyid":'1234',
    "source":'CareInspectorateScot'
    })
    assert CareInspScotDataHandler().format_row(namefield,row) == new_row


def test_row_formatting_addr():
    row = CIS_entry_creator({
        "CSNumber" :'1234',
        "ServiceName" :'Something Name',
        "Address_line_1" :'House',
        "Address_line_2" :'Street',
        "Address_line_3" :'Town',
        "Address_line_4" :'',
        "Service_town" :'Town',
        "Service_Postcode" :'PC1 1PC',

})
    namefield = 'ServiceName'
    new_row = spine_entry_creator({
    "uid" : 'GB-CIS-1234',
    "organisationname" : 'Something Name',
    "normalisedname": 'SOMETHING NAME',
    "companyid":'1234',
    "source":'CareInspectorateScot',
    "fulladdress" : "HOUSE, STREET",
    "city" : 'TOWN',
    "postcode" : "PC1 1PC"
    })
    assert CareInspScotDataHandler().format_row(namefield,row) == new_row

