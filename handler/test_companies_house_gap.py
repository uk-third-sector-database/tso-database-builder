import pytest

from .companies_house_gap_decade import CompaniesHouseGapDataHandler
from .test_companies_house import spine_entry_creator


def companies_house_entry_creator(overrides):
    entry = {
    "etag" : '',
    "hits" : '',
    "company_name" : '',
    "company_number" : '',
    "company_status" : '',
    "company_subtype" : '',
    "company_type" : '',
    "date_of_cessation" : '',
    "date_of_creation" : '',
    "sic_codes" : '',
    "kind" : '',
    "address_line_1" : '',
    "address_line_2" : '',
    "country" : '',
    "locality" : '',
    "postal_code" : '',
    "region" : '',
    }
    entry.update(**overrides)
    return entry


@pytest.mark.parametrize(
    "company_category,expected",
    [("Limited Liability Partnership", False), ("Something else", True)],
)
def test_filters(company_category, expected):
    value = companies_house_entry_creator({"company_type": company_category})
    assert CompaniesHouseGapDataHandler().all_filters(value) == expected


@pytest.mark.xfail
@pytest.mark.parametrize(
        'row,result',
        [(companies_house_entry_creator({'date_of_creation': '2010-1-1'}),False),
          (companies_house_entry_creator({'date_of_creation': '2015-1-1'}),True)]
)
def test_filter_by_incorporation(row,result):
    assert CompaniesHouseGapDataHandler().all_filters(row) == result

def test_row_formatting():
    row = companies_house_entry_creator({
        "company_name" : 'Something Name',
        "company_number" : '1234',
        "address_line_1" : '4 This Street',
        "locality": 'Anything', 
        "postal_code": 'AB1 4AB',
        "company_subtype":'category',
    })
                                         
                                         
                                    
    namefield = 'company_name'
    new_row = spine_entry_creator({
    "uid" : 'GB-COH-1234',
    "organisationname" : 'Something Name',
    "normalisedname": '',
    "companyid":'1234',
    "housenumber":'',
    "addressline1":'4 This Street',
    "addressline2":'',
    "addressline3":'',
    "addressline4":'',
    "addressline5":'',
    "city":'Anything',
    "localauthority":'',
    "postcode":'AB1 4AB',
    "source":'adv_api  category'
    })
    assert CompaniesHouseGapDataHandler().format_row(namefield,row) == new_row
