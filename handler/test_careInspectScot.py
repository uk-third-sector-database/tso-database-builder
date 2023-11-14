import pytest

from .careInspectScot import CareInspScotDataHandler  
from .test_companies_house import spine_entry_creator



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
    "normalisedname": '',
    "companyid":'1234',
    "source":'CareInspectorateScot'
    })
    assert CareInspScotDataHandler().format_row(namefield,row) == new_row

