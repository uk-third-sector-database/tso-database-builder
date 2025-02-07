import pytest

from .socialHousingEng import SocialHousingEngDataHandler  
from .base_definitions import public_spine_entry_creator



def SHE_entry_creator(overrides):
    entry = {
        "Organisation name" : '',
        "Registration number" : '',
        "Registration date" : '',
        "Designation" : '',
        "Corporate form" : '',
    }
    entry.update(**overrides)
    return entry


@pytest.mark.parametrize(
    "designation,expected",
    [("Profit", False), ("Non-profit", True)],
)
def test_filters(designation, expected):
    value = SHE_entry_creator({"Designation": designation})
    assert SocialHousingEngDataHandler().all_filters(value) == expected 



def test_row_formatting():
    row = SHE_entry_creator({
"Organisation name" : 'Something Name',
"Registration number" : '1234',
"Registration date" : '',
"Designation" : 'Non-profit',
"Corporate form" : '',
'Iteration':''
})
    namefield = 'Organisation name'
    new_row = public_spine_entry_creator({
    "uid" : 'GB-SHPE-1234',
    "organisationname" : 'Something Name',
    "normalisedname": 'SOMETHING NAME',
    "id_in_source":'1234',
    "source":'SocialHousingEngland',
    'iteration':'',
    'companyid':''
    })
    assert SocialHousingEngDataHandler().format_row(namefield,row) == new_row


def test_row_formatting_regdate():
    row = SHE_entry_creator({
"Organisation name" : 'Something Name',
"Registration number" : '1234',
"Registration date" : '12/12/1980',
"Designation" : 'Non-profit',
"Corporate form" : '',
'Iteration':''
})
    namefield = 'Organisation name'
    new_row = public_spine_entry_creator({
    "uid" : 'GB-SHPE-1234',
    "organisationname" : 'Something Name',
    "normalisedname": 'SOMETHING NAME',
    "id_in_source":'1234',
    "source":'SocialHousingEngland',
    "registerdate":'12/12/1980',
    'iteration':'',
    'companyid':''
    })
    assert SocialHousingEngDataHandler().format_row(namefield,row) == new_row

