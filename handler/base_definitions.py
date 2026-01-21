# static definitions


SAMEAS_FILE = '../raw_data/FTC_data/dkane_relationships_sameas.csv'

OSCR_LINKS_FILE = '../raw_data/oscr.linkage.csv'



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


# sub_spine data - for initial ingest per data source
def sub_spine_entry_creator(overrides):
    entry = {
        "uid" : "",
        "organisationname" : "",
        "normalisedname" : "",
        "fulladdress" : "",
        "city" : "",
        "postcode" : "",
        "companyid" : "",
        "registerdate" : "",
        "removeddate" : "",
        "source" : "",
        "source_register" : "",
        "id_in_source" : "",
        "is_cic" : "",
    }
    entry.update(**overrides)
    return entry


def public_spine_entry_creator(overrides):
    entry = {
        "uid" : "",
        "organisationname" : "",
        "normalisedname" : "",
        "fulladdress" : "",
        "city" : "",
        "postcode" : "",
        "registerdate" : "",
        "removeddate" : "",
        "source_register" : "",
        "is_cic" : "",
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
        "registerdate" : "",
        "removeddate" : "",
        "source" : "",
        'source_register' : "",
        "id_in_source" : ""
        }
    entry.update(**overrides)
    return entry



def match_csv_entry_creator(overrides):
    entry = {           
        "uid" : "",
        "orgA_id_in_source" : "",
        "orgA_source" : "",
        "orgA_uid" : "",
        "orgB_id_in_source" : "",
        "orgB_source" : "",
        "orgB_uid" : "",
        'match_type' : "",
    }
    entry.update(**overrides)
    return entry


SUB_SPINE_CSV_FIELDS = [
    "uid",
    "organisationname",
    "normalisedname",
    "fulladdress",
    "city",
    "postcode",
    "companyid",
    "registerdate",
    "removeddate",
    "source",
    "source_register",
    "id_in_source",
    "is_cic"]


SPINE_CSV_FIELDS = [
    "uid",
    "organisationname",
    "normalisedname",
    "fulladdress",
    "city",
    "postcode", 
    "registerdate",
    "removeddate", 
    "source_register",
    "is_cic",  ]    


EXTRA_DETAILS_CSV_FIELDS = [
    "uid",
    "organisationname",
    "normalisedname",
    "fulladdress",
    "city",
    "postcode",
    "registerdate",
    "removeddate",
    "source_register",
    "id_in_source"
    ]

MATCHES_CSV_FIELDS = [
    "uid",
    "orgA_id_in_source",
    "orgA_source",
    "orgA_uid",
    'orgB_id_in_source',
    'orgB_source',
    "orgB_uid",
    'match_type',
]

FINAL_MATCHES_CSV_FIELDS = ['rowid'] + MATCHES_CSV_FIELDS

FINAL_SPINE_CSV_FORMAT = ['rowid'] + SPINE_CSV_FIELDS

FINAL_EXTRA_DETAILS_CSV_FIELDS = ['rowid', 'source'] + EXTRA_DETAILS_CSV_FIELDS
