import pytest

from .companies_house import CompaniesHouseDataHandler

def companies_house_entry_creator(overrides):
    entry = {
        " CompanyName": "",
        " CompanyNumber": "",
        "RegAddress.CareOf": "",
        "RegAddress.POBox": "",
        "RegAddress.AddressLine1": "",
        " RegAddress.AddressLine2": "",
        "RegAddress.PostTown": "",
        "RegAddress.County": "",
        "RegAddress.Country": "",
        "RegAddress.PostCode": "",
        "CompanyCategory": "",
        "CompanyStatus": "",
        "CountryOfOrigin": "",
        "DissolutionDate": "",
        "IncorporationDate": "",
        "Accounts.AccountRefDay": "",
        "Accounts.AccountRefMonth": "",
        "Accounts.NextDueDate": "",
        "Accounts.LastMadeUpDate": "",
        "Accounts.AccountCategory": "",
        "Returns.NextDueDate": "",
        "Returns.LastMadeUpDate": "",
        "Mortgages.NumMortCharges": "",
        "Mortgages.NumMortOutstanding": "",
        "Mortgages.NumMortPartSatisfied": "",
        "Mortgages.NumMortSatisfied": "",
        "SICCode.SicText_1": "",
        "SICCode.SicText_2": "",
        "SICCode.SicText_3": "",
        "SICCode.SicText_4": "",
        "LimitedPartnerships.NumGenPartners": "",
        "LimitedPartnerships.NumLimPartners": "",
        "URI": "",
        "PreviousName_1.CONDATE": "",
        "PreviousName_1.CompanyName": "",
        "PreviousName_2.CONDATE": "",
        "PreviousName_2.CompanyName": "",
        "PreviousName_3.CONDATE": "",
        "PreviousName_3.CompanyName": "",
        "PreviousName_4.CONDATE": "",
        "PreviousName_4.CompanyName": "",
        "PreviousName_5.CONDATE": "",
        "PreviousName_5.CompanyName": "",
        "PreviousName_6.CONDATE": "",
        "PreviousName_6.CompanyName": "",
        "PreviousName_7.CONDATE": "",
        "PreviousName_7.CompanyName": "",
        "PreviousName_8.CONDATE": "",
        "PreviousName_8.CompanyName": "",
        "PreviousName_9.CONDATE": "",
        "PreviousName_9.CompanyName": "",
        "PreviousName_10.CONDATE": "",
        "PreviousName_10.CompanyName": "",
        "ConfStmtNextDueDate": "",
        "ConfStmtLastMadeUpDate": "",
    }
    entry.update(**overrides)
    return entry


@pytest.mark.parametrize(
    "company_category,expected",
    [("Limited Liability Partnership", False), ("Something else", True)],
)
def test_filters(company_category, expected):
    value = companies_house_entry_creator({"CompanyCategory": company_category})
    assert CompaniesHouseDataHandler().all_filters(value) == expected



@pytest.mark.parametrize(
    'row,keys',
    [(companies_house_entry_creator({"CompanyName": 'Something'}),["CompanyName"])]
)
def test_find_name_keys_noextranames(row,keys):
    assert CompaniesHouseDataHandler().find_names(row) == keys


def test_find_name_keys_2previousnames():#row,keys):
    row = companies_house_entry_creator({" CompanyName": 'Something',
    "PreviousName_1.CompanyName": 'Something1',
    "PreviousName_2.CompanyName": 'Something2'})
    keys = [" CompanyName","PreviousName_1.CompanyName","PreviousName_2.CompanyName"]
    assert CompaniesHouseDataHandler().find_names(row) == keys

def test_find_address_keys_ignore_CO():
    row = companies_house_entry_creator({
        "RegAddress.CareOf": "text here",
        "RegAddress.POBox": "text here",
        "RegAddress.PostCode": "text here"})

    keys = ["RegAddress.POBox",
        "RegAddress.PostCode"]
    
    assert CompaniesHouseDataHandler().find_addresses(row) == keys

def test_find_address_keys():
    row = companies_house_entry_creator({
        "RegAddress.AddressLine1": "text here",
        " RegAddress.AddressLine2": "text here",
        "RegAddress.PostTown": "text here",
        "RegAddress.County": "text here",
        "RegAddress.Country": "text here",
        "RegAddress.PostCode": "text here"})

    keys = ["RegAddress.AddressLine1",
        " RegAddress.AddressLine2",
        "RegAddress.PostTown",
        "RegAddress.County",
        "RegAddress.Country",
        "RegAddress.PostCode"]
    print(row)
    assert CompaniesHouseDataHandler().find_addresses(row) == keys


def test_row_formatting_POBox():
    row = companies_house_entry_creator({
    " CompanyName": 'Something Name',
    "PreviousName_1.CompanyName": 'Something1 Name',
    " CompanyNumber" : '1234',
    "RegAddress.POBox": "POBox text",
    "RegAddress.AddressLine1": "a1",
    " RegAddress.AddressLine2": "a2",
    "RegAddress.PostTown": "town",
    "RegAddress.PostCode": "code",
    "CompanyCategory":'category'})
    namefield = ' CompanyName'
    new_row = spine_entry_creator({
    "uid" : 'GB-COH-1234',
    "organisationname" : 'Something Name',
    "normalisedname": '',
    "companyid":'1234',
    "housenumber":'',
    "addressline1":'POBox text',
    "addressline2":'a1',
    "addressline3":'a2',
    "addressline4":'',
    "addressline5":'',
    "city":'town',
    "localauthority":'',
    "postcode":'code',
    "source":'2023_download category'
    })
    assert CompaniesHouseDataHandler().format_row(namefield,row) == new_row

def test_row_formatting_prev_name_no_POBox():
    row = companies_house_entry_creator({
    " CompanyName": 'Something Name',
    "PreviousName_1.CompanyName": 'Something1 Name',
    " CompanyNumber" : '1234',
    "RegAddress.AddressLine1": "a1",
    " RegAddress.AddressLine2": "a2",
    "RegAddress.PostTown": "town",
    "RegAddress.PostCode": "code",
    "CompanyCategory":'category'})
    namefield = 'PreviousName_1.CompanyName'
    new_row = spine_entry_creator({
    "uid" : 'GB-COH-1234',
    "organisationname" : 'Something1 Name',
    "normalisedname": '',
    "companyid":'1234',
    "housenumber":'',
    "addressline1":'a1',
    "addressline2":'a2',
    "addressline3":'',
    "addressline4":'',
    "addressline5":'',
    "city":'town',
    "localauthority":'',
    "postcode":'code',
    "source":'2023_download category'
    })
    assert CompaniesHouseDataHandler().format_row(namefield,row) == new_row

