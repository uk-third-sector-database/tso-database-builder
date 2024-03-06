import pytest

from .ScotHousingReg import ScotHousingRegDataHandler 
from .base_definitions import spine_entry_creator



def SHR_entry_creator(overrides):
    entry = {
        "Financial Year" : "",
        "Reg No" : "",
        "Social Landlord" : "",
        "Constitution" : "",
        "Clients" : "",
        "Landlord type" : "",
        "Settlement" : "",
        "National Operator" : ""
    }
    entry.update(**overrides)
    return entry

""" 
@pytest.mark.parametrize(
    "company_category,expected",
    [("Limited Liability Partnership", False), ("Something else", True)],
)
def test_filters(company_category, expected):
    value = co_op_entry_creator({"CompanyCategory": company_category})
    assert CoOpsDataHandler().all_filters(value) == expected 



def test_find_name_keys_noextranames():
    row = co_op_entry_creator({"Registered Name": 'Something'})
    keys = ["Registered Name"]
    assert CoOpsDataHandler().find_names(row) == keys
"""


def test_row_formatting():
    row = SHR_entry_creator({
        "Reg No" : "1234",
        "Social Landlord" : "Something Name",

})
    namefield = 'Social Landlord'
    
    new_row = spine_entry_creator({
    "uid" : 'GB-SHR-1234',
    "organisationname" : 'Something Name',
    "normalisedname": 'SOMETHING NAME',
    "primaryid":'1234',
    "primarysource":'ScottishHousingRegulator'
    })
    assert ScotHousingRegDataHandler().format_row(namefield,row) == new_row

