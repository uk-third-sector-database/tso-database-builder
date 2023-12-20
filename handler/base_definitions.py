# static definitions

ORG_ID_MAPPING = {
'CCEW':'CHC',
'OSCR':'SC',
'CCNI':'NIC',
'PRI/LTD BY GUAR/NSC (Private, limited by guarantee, no share capital)':'COH',
"PRI/LBG/NSC (Private, limited by guarantee, no share capital, use of 'Limited' exemption)":'COH',
'Charitable Incorporated Organisation':'COH',
'Community Interest Company':'COH',
'Registered Society':'COH',
'Scottish Charitable Incorporated Organisation':'COH',
'Industrial and Provident Society':'COH',
'CareQualityCommission':'CQC', # not in org_id - might need to update mapping
'ScottishHousingRegulator':'SHR',
'SocialHousingEngland':'SHPE',
'CoOps':'COOP', # not in org_id - might need to update mapping
'Mutuals Public Register': 'MPR'
}


def spine_entry_creator(overrides):
    entry = {
        "uid" : '',
        "organisationname" :  '',
        "normalisedname" : '',
        "companyid" : '' ,
        "charitynumber" : '',
        "fulladdress" : '',
        "city" : '' ,
        "postcode" :  '',
        "source" : '',
        "registrationdate" : '',
        "dissolutiondate" : '',
    }
    entry.update(**overrides)
    return entry



NEW_SPINE_CSV_FORMAT = [
    "uid",
    "organisationname",
    "normalisedname",
    "companyid",
    "charitynumber",
    "fulladdress",
    "city",
    "postcode",
    "source",
    "registrationdate",
    "dissolutiondate",
    "lat",
    "long",
    "imd",
    "country",
    "x",
    "y",
]

FINAL_SPINE_CSV_FORMAT = ['rowid'] + NEW_SPINE_CSV_FORMAT

