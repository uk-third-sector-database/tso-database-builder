import pytest

import pandas as pd



def new_spine_entry_creator(overrides):
    entry = {
        "uid" : '',
        "organisationname" :  '',
        "normalisedname" : '',
        "companyid" : '' ,
        "charitynumber" : '',
        "fulladdress" : '' ,
        "source" : '',
    }
    entry.update(**overrides)
    return entry