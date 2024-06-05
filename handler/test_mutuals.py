import pytest

from .mutuals import MutualsDataHandler
from .base_definitions import sub_spine_entry_creator,extra_csv_entry_creator

import copy

def mutuals_entry_creator(overrides):
    entry = {
'Full Registration Number' : '',
'Society Name' : '',
'Society Address' : '',
'Registration Date' : '',
'Deregistration Date' : '',
'Iteration' : '',
    }
    entry.update(**overrides)
    return entry





def test_row_formatting():
    row = mutuals_entry_creator({
'Full Registration Number':'12',
'Society Name' :'something',
'Society Address' :'33 street, city, LA, A12 2DF',
'Iteration' : '12/2022'

    })
    namefield = 'Society Name'
    new_row = sub_spine_entry_creator({
    "uid" : 'GB-MPR-12',
    "organisationname" : 'something',
    "normalisedname": 'SOMETHING',
    "id_in_source":'12',
    "fulladdress":'33 STREET, CITY, LA',
    "source":'mutuals',
    "postcode" : 'A12 2DF',
    'iteration' : '12/2022'
    })
    assert MutualsDataHandler().format_row(namefield,row) == new_row


def test_row_formatting_dates():
    row = mutuals_entry_creator({
        'Full Registration Number':'12',
'Society Name' :'something',
'Society Address' :'33 street, city, LA, A12 2DF',
'Iteration' : '12/2022',
'Registration Date' : '1961-06-23',
'Deregistration Date' : '2019-06-23',


    })

    namefield = 'Society Name'
    new_row = sub_spine_entry_creator({
        "uid" : 'GB-MPR-12',
"organisationname" : 'something',
"normalisedname": 'SOMETHING',
"id_in_source":'12',
"fulladdress":'33 STREET, CITY, LA',
"source":'mutuals',
"postcode" : 'A12 2DF',
'iteration' : '12/2022',
'registerdate': '23/06/1961',
'removeddate' : '23/06/2019',
'source':'mutuals'
    })
    assert MutualsDataHandler().format_row(namefield,row) == new_row


def test_combine_org_details_name():
    row = sub_spine_entry_creator({
        "uid" : 'GB-MPR-12',
"organisationname" : 'something',
"normalisedname": 'SOMETHING',
"id_in_source":'12',
"fulladdress":'33 STREET, CITY, LA, A12 2DF',
"source":'mutuals',
"postcode" : 'A12 2DF',
'iteration' : '12/2022',
'registerdate': '23/06/1961',
'removeddate' : '23/06/2019',
'source':'mutuals'
    })
    row1 = copy.deepcopy(row)
    row1['iteration'] = '11/2022'
    row1['organisationname'] =  'A Previous Name'
    row1['normalisedname'] = 'A PREVIOUS NAME'

    subspine, extra = MutualsDataHandler().combine_org_details_per_source([row,row1])

    row.pop('iteration')
    assert subspine == row
    assert extra == [extra_csv_entry_creator({
        'organisationname' : 'A Previous Name',
        'normalisedname' : 'A PREVIOUS NAME',
        "uid" : 'GB-MPR-12',
'source':'mutuals'
    })]



def test_find_primary_name():
    n1 = ('something','SOMETHING','12/2022')
    n2 = ('A Previous Name','A PREVIOUS NAME','11/2022')

    expected_primary = ('something','SOMETHING')
    expected_extra = [('A Previous Name','A PREVIOUS NAME')]

    p,e = MutualsDataHandler().find_primary_info([n1,n2]) 
    assert expected_primary == p
    assert expected_extra == e



    
def test_combine_org_details_date():
    row = sub_spine_entry_creator({
        "uid" : 'GB-MPR-12',
"organisationname" : 'something',
"normalisedname": 'SOMETHING',
"id_in_source":'12',
"fulladdress":'33 STREET, CITY, LA, A12 2DF',
"source":'mutuals',
"postcode" : 'A12 2DF',
'iteration' : '12/2022',
'registerdate': '23/06/1961',
'removeddate' : '23/06/2019',
'source':'mutuals'
    })
    row1 = copy.deepcopy(row)
    row1['iteration'] = '11/2022'
    row1['organisationname'] =  'A Previous Name'
    row1['normalisedname'] = 'A PREVIOUS NAME'
    row1['removeddate'] = '24/05/2019'

    subspine, extra = MutualsDataHandler().combine_org_details_per_source([row,row1])

    row.pop('iteration')
    row['removeddate'] = '24/05/2019'
    assert subspine == row
    assert extra == [
        extra_csv_entry_creator({
        'organisationname' : 'A Previous Name',
        'normalisedname' : 'A PREVIOUS NAME',
        "uid" : 'GB-MPR-12',
'source':'mutuals'}),
        extra_csv_entry_creator({
        'removeddate' : '23/06/2019',
        "uid" : 'GB-MPR-12',
'source':'mutuals'})
        ]