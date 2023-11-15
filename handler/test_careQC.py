import pytest

from .careQC import CQCDataHandler  
from .test_companies_house import spine_entry_creator



def CQC_entry_creator(overrides):
    entry = {
        "Name" : '',
        "Also known as" : '',
        "Address" : '',
        "Postcode" : '',
        "Phone number" : '',
        "Service's website (if available)" : '',
        "Service types" : '',
        "Date of latest check" : '',
        "Specialisms/services" : '',
        "Provider name" : '',
        "Local authority" : '',
        "Region" : '',
        "Location URL" : '',
        "CQC Location ID (for office use only)" : '',
        "CQC Provider ID (for office use only)" : '',
    }
    entry.update(**overrides)
    return entry





def test_row_formatting():
    row = CQC_entry_creator({
        "CQC Provider ID (for office use only)" :'1234',
        "Name" :'Something Name',
        "Also known as" : 'Something something',

})
    namefield = 'Name'
    new_row = spine_entry_creator({
    "uid" : 'GB-CQC-1234',
    "organisationname" : 'Something Name',
    "normalisedname": '',
    "companyid":'1234',
    "source":'CareQualityCommission'
    })
    assert CQCDataHandler().format_row(namefield,row) == new_row

def test_row_formatting_alt_name():
    row = CQC_entry_creator({
        "CQC Provider ID (for office use only)" :'1234',
        "Name" :'Something Name',
        "Also known as" : 'Something something',

})
    namefield = 'Also known as'
    new_row = spine_entry_creator({
    "uid" : 'GB-CQC-1234',
    "organisationname" : 'Something something',
    "normalisedname": '',
    "companyid":'1234',
    "source":'CareQualityCommission'
    })
    assert CQCDataHandler().format_row(namefield,row) == new_row
