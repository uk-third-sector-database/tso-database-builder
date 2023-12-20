import pytest

from .co_ops import CoOpsDataHandler
from .base_definitions import spine_entry_creator



def co_op_entry_creator(overrides):
    entry = {
        "CUK Organisation ID" : "",
        "Registered Number" : "",
        "Registrar" : "",
        "Registered Name" : "",
        "Trading Name" : "",
        "Legal Form" : "",
        "Registered Street" : "",
        "Registered City" : "",
        "Registered State/Province" : "",
        "Registered Postcode" : "",
        "UK Nation" : "",
        "SIC Code" : "",
        "SIC section" : "",
        "SIC code  - level 2" : "",
        "SIC code  - level 2 description" : "",
        "SIC code  - level 3" : "",
        "SIC code  - level 3 description" : "",
        "SIC code  - level 4" : "",
        "SIC code  - level 4 description" : "",
        "SIC code  - level 5" : "",
        "SIC code  - level 5 description" : "",
        "Sector - Simplified, High Level" : "",
        "Ownership Classification" : "",
        "Registered Status" : "",
        "Incorporation Date" : "",
        "Dissolved Date" : "",
        "Website" : "",
        "Registered Admin County Code" : "",
        "Registered Admin County Name" : "",
        "Registered Admin District Code" : "",
        "Registered Admin District Name" : "",
        "Registered Admin Ward Code" : "",
        "Registered Admin Ward Name" : "",
        "Registered Constituency Code" : "",
        "Registered Constituency Name" : "",
        "Registered LSOA Name" : "",
        "Registered MSOA Name" : "",
        "Registered Parish Code" : "",
        "Registered Parish Name" : ""
        
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
    assert CoOpsDataHandler().all_filters(value) == expected """



def test_find_name_keys_noextranames():
    row = co_op_entry_creator({"Registered Name": 'Something'})
    keys = ["Registered Name"]
    assert CoOpsDataHandler().find_names(row) == keys



def test_row_formatting():
    row = co_op_entry_creator({
    "Registered Name": 'Something Name',
    "Registered Number" : '1234',
    "Registered Street": "a1",
    "Registered City": "town",
    "Registered Postcode": "code"})
    namefield = 'Registered Name'
    new_row = spine_entry_creator({
    "uid" : 'GB-COOP-1234',
    "organisationname" : 'Something Name',
    "normalisedname": '',
    "companyid":'1234',
    "housenumber":'',
    "addressline1":'a1',
    "addressline2":'',
    "addressline3":'',
    "addressline4":'',
    "addressline5":'',
    "city":'town',
    "localauthority":'',
    "postcode":'code',
    "source":'CoOps'
    })
    assert CoOpsDataHandler().format_row(namefield,row) == new_row

