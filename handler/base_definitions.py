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
        "uid" : "",
        "organisationname" : "",
        "normalisedname" : "",
        "fulladdress" : "",
        "city" : "",
        "postcode" : "",
        "primarysource" : "",
        "primaryid" : "",
        "primaryregdate" : "",
        "dissolutiondate" : "",
        "secondarysource" : "",
        "secondaryid" : "",
        "secondaryregdate" : "",
           }
    entry.update(**overrides)
    return entry


def extra_csv_entry_creator(overrides):
    entry = {
        "uid" : "",
        "organisationname" : "",
        "normalisedname" : "",
        "fulladdress" : "",
        "city" : "",
        "postcode" : "",
        "source" : "",
        }
    entry.update(**overrides)
    return entry


SPINE_CSV_FIELDS = [
    "uid",
    "organisationname",
    "normalisedname",
    "fulladdress",
    "city",
    "postcode",
    "primarysource",
    "primaryid",
    "primaryregdate",
    "dissolutiondate",
    "secondarysource",
    "secondaryid",
    "secondaryregdate"]

EXTRA_DETAILS_CSV_FIELDS = [
    "uid",
    "organisationname",
    "normalisedname",
    "fulladdress",
    "city",
    "postcode",
    "source",
]


FINAL_SPINE_CSV_FORMAT = ['rowid'] + SPINE_CSV_FIELDS

FINAL_EXTRA_DETAILS_CSV_FIELDS = ['rowid'] + EXTRA_DETAILS_CSV_FIELDS
