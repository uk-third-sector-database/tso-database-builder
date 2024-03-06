import pytest

from .companies_house_2014 import CompaniesHouse2014DataHandler
from .base_definitions import spine_entry_creator



def companies_house_entry_creator(overrides):
    entry = {"companynumber" : '',
    "regaddresspostcode" : '',
    "companyname" : '',
    "companycategory" : '',
    "chregy" : '',
    "chremy" : '',
    }
    entry.update(**overrides)
    return entry


@pytest.mark.parametrize(
    "company_category,expected",
    [("Limited Liability Partnership", False), ("Something else", True)],
)
def test_filters(company_category, expected):
    value = companies_house_entry_creator({"companycategory": company_category})
    assert CompaniesHouse2014DataHandler().all_filters(value) == expected



@pytest.mark.parametrize(
    'row,keys',
    [(companies_house_entry_creator({"companyname": 'Something'}),["companyname"])]
)
def test_find_name_keys_noextranames(row,keys):
    assert CompaniesHouse2014DataHandler().find_names(row) == keys


@pytest.mark.parametrize(
        'row,result',
        [(companies_house_entry_creator({'chremy': '1980'}),True),
          (companies_house_entry_creator({'chremy': ''}),True)]
)
def test_filter_by_dissolution(row,result):
    assert CompaniesHouse2014DataHandler().all_filters(row) == result

def test_row_formatting():
    row = companies_house_entry_creator({
    "companyname": 'Something Name',
    "companynumber" : '1234',
    "regaddresspostcode": "code",
    "companycategory":'category',})
    namefield = 'companyname'
    new_row = spine_entry_creator({
    "uid" : 'GB-COH-1234',
    "organisationname" : 'Something Name',
    "normalisedname": 'SOMETHING NAME',
    "primaryid":'1234',
    "postcode":'code',
    "primarysource":'2014_prior category',
    })
    assert CompaniesHouse2014DataHandler().format_row(namefield,row) == new_row

