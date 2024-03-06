import pytest

from .mutuals import MutualsDataHandler
from .base_definitions import spine_entry_creator



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
    "normalisedname": 'SOMETHING',
    "primaryid":'12',
    "fulladdress":'33 STREET,CITY,LA',
    "city":'',
    "postcode":'postcode',
    "primarysource":'mutuals'
    })
    assert MutualsDataHandler().format_row(namefield,row) == new_row


def test_row_formatting():
    row = mutuals_entry_creator({
"societynumber":'12',
"organisationname":'something',
"address":'33 street, city, postcode',
"city":'city',
"source":'mutuals',
"postcode":'postcode',

    })
    namefield = 'organisationname'
    new_row = spine_entry_creator({
    "uid" : 'GB-MPR-12',
    "organisationname" : 'something',
    "normalisedname": 'SOMETHING',
    "primaryid":'12',
    "fulladdress":'33 STREET',
    "city":'CITY',
    "postcode":'postcode',
    "primarysource":'mutuals'
    })
    assert MutualsDataHandler().format_row(namefield,row) == new_row
