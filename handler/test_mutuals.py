import pytest

from .mutuals import MutualsDataHandler
from .test_companies_house import spine_entry_creator



def mutuals_entry_creator(overrides):
    entry = {
"societynumber":'',
"organisationname":'',
"address":'',
"source":'',
"uid":'',
"normalisedname":'',
"companyid":'',
"housenumber":'',
"city":'',
"localauthority":'',
"postcode":'',
    }
    entry.update(**overrides)
    return entry





def test_row_formatting():
    row = mutuals_entry_creator({
"societynumber":'12',
"organisationname":'something',
"address":'33 street, city, LA, postcode',
"source":'mutuals',
"postcode":'postcode',

    })
    namefield = 'organisationname'
    new_row = spine_entry_creator({
    "uid" : 'GB-MPR-12',
    "organisationname" : 'something',
    "normalisedname": '',
    "companyid":'12',
    "housenumber":'',
    "addressline1":'33 street,city,LA',
    "addressline2":'',
    "addressline3":'',
    "addressline4":'',
    "addressline5":'',
    "city":'',
    "localauthority":'',
    "postcode":'postcode',
    "source":'mutuals'
    })
    assert MutualsDataHandler().format_row(namefield,row) == new_row

