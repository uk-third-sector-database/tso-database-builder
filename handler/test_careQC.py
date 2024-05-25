import pytest

from .careQC import CQCDataHandler  
from .base_definitions import sub_spine_entry_creator



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
        'Iteration':''
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
    new_row = sub_spine_entry_creator({
    "uid" : 'GB-CQC-1234',
    "organisationname" : 'Something Name',
    "normalisedname": 'SOMETHING NAME',
    "id_in_source":'1234',
    "source":'CareQualityCommission',
    'iteration':''
    })
    assert CQCDataHandler().format_row(namefield,row) == new_row

def test_row_formatting_provider_name():
    row = CQC_entry_creator({
        "CQC Provider ID (for office use only)" :'1234',
        "Name" :'Something Name',
        "Also known as" : 'Something something',
        'Provider name' : 'Provider name',

})
    namefield = 'Provider name'
    new_row = sub_spine_entry_creator({
    "uid" : 'GB-CQC-1234',
    "organisationname" : 'Provider name',
    "normalisedname": 'PROVIDER NAME',
    "id_in_source":'1234',
    "source":'CareQualityCommission',
    'iteration':''
    })
    assert CQCDataHandler().format_row(namefield,row) == new_row
