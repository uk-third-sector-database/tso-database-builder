import io
import os

import pytest

from spine.wrangling import concat, check_spine_format, consolidate_address, final_processing
from spine.wrangling import dict_indexed_by_field, dedupe_addr, combine_org_details
from handler.test_companies_house import spine_entry_creator

def new_spine_entry_creator(overrides):
    entry = {
        "uid" : '',
        "organisationname" :  '',
        "normalisedname" : '',
        "companyid" : '' ,
        "charitynumber" : '',
        "fulladdress" : '' ,
        "city":'',
        "postcode":'',
        "source" : '',
        "registrationdate" : '',
        "dissolutiondate" : ''
    }
    entry.update(**overrides)
    return entry

def final_spine_entry_creator(overrides):
    entry = {
        "rowid" : '',
        "uid" : '',
        "organisationname" :  '',
        "normalisedname" : '',
        "companyid" : '' ,
        "fulladdress" : '' ,
        "city":'',
        "postcode":'',
        "source" : '',
        "registrationdate" : '',
        "dissolutiondate" : ''
    }
    entry.update(**overrides)
    return entry

def assert_files_basically_same(a,b,ignore=False):
    def filter_na_lines(line):
        return not line.startswith('n/a')
    
    a_lines = a.split('\n')
    b_lines = b.split('\n')
    
    if ignore:
        compare_pairs = [(a_line,b_line) for a_line,b_line in zip(filter(filter_na_lines,a_lines),filter(filter_na_lines,b_lines))]
    else:
        compare_pairs = zip(a.split('\n'),b.split('\n'))
    for a_line, b_line in compare_pairs:
        assert a_line.strip() == b_line.strip()

def test_concat__2_files_success():
    # test data strings
    for_f1 = '''uid,organisationname,normalisedname,companyid,housenumber,addressline1,addressline2,addressline3,addressline4,addressline5,city,localauthority,postcode,source,registrationdate,dissolutiondate
        CH_14413082,! HEAL UR TECH LTD,,14413082,,5 BRIDGE STREET,,,,,GUILDFORD,,GU1 4RY,companies house
        CH_13220580,""" BORA "" 2 LTD",,13220580,,26 CARMICHAEL CLOSE,WINSTANLEY ESTATE,,,,LONDON,BATTERSEA,SW11 2HS,companies house'''
    
    for_f2 = '''uid,organisationname,normalisedname,companyid,housenumber,addressline1,addressline2,addressline3,addressline4,addressline5,city,localauthority,postcode,source,registrationdate,dissolutiondate
        CH_CE000952,"""20-20 VOICE"" CANCER",,CE000952,,,,,,,,,,companies house
        CH_05914136,"""243 RUGBY ROAD MANAGEMENT COMPANY LIMITED""",,05914136,,94 PARK LANE,,,,,CROYDON,SURREY,CR0 1JB,companies house
        CH_12459056,"""AN IDEAL LIFE???"" CIC",,12459056,,197 CLAREMONT ROAD,,,,,MANCHESTER,,M14 4JF,companies house'''
    
    expected_f3 = '''uid,organisationname,normalisedname,companyid,charitynumber,fulladdress,city,postcode,source,registrationdate,dissolutiondate
        CH_14413082,! HEAL UR TECH LTD,HEAL UR TECH LTD,14413082,,5 BRIDGE STREET,GUILDFORD,GU1 4RY,companies house,,
        CH_13220580,""" BORA "" 2 LTD",BORA 2 LTD,13220580,,"26 CARMICHAEL CLOSE, WINSTANLEY ESTATE",LONDON,SW11 2HS,companies house,,
        CH_CE000952,"""20-20 VOICE"" CANCER",2020 VOICE CANCER,CE000952,,,,,companies house,,
        CH_05914136,"""243 RUGBY ROAD MANAGEMENT COMPANY LIMITED""",243 RUGBY ROAD MANAGEMENT COMPANY LIMITED,05914136,,94 PARK LANE,CROYDON,CR0 1JB,companies house,,
        CH_12459056,"""AN IDEAL LIFE???"" CIC",AN IDEAL LIFE CIC,12459056,,197 CLAREMONT ROAD,MANCHESTER,M14 4JF,companies house,,'''
    f1 = io.StringIO(for_f1)
    
    f2 = io.StringIO(for_f2)

    f3 = io.StringIO()

    concat([f1, f2], f3)

    f3.seek(0)

    assert_files_basically_same(f3.read(), expected_f3)


def test_concat_mixture_file_formats():
    # test data strings
    for_f1 = '''uid,organisationname,normalisedname,companyid,housenumber,addressline1,addressline2,addressline3,addressline4,addressline5,city,localauthority,postcode,source,registrationdate,dissolutiondate
        CH_14413082,! HEAL UR TECH LTD,,14413082,,5 BRIDGE STREET,,,,,GUILDFORD,,GU1 4RY,companies house
        CH_13220580,""" BORA "" 2 LTD",,13220580,,26 CARMICHAEL CLOSE,WINSTANLEY ESTATE,,,,LONDON,BATTERSEA,SW11 2HS,companies house'''
    
    for_f2 ='''uid,organisationname,normalisedname,companyid,charitynumber,fulladdress,city,postcode,source,registrationdate,dissolutiondate
        CH_CE000952,"""20-20 VOICE"" CANCER",,CE000952,,,,,companies house
        CH_05914136,"""243 RUGBY ROAD MANAGEMENT COMPANY LIMITED""",,05914136,,94 PARK LANE,CROYDON,CR0 1JB,companies house
        CH_12459056,"""AN IDEAL LIFE???"" CIC",,12459056,,197 CLAREMONT ROAD,MANCHESTER,M14 4JF,companies house'''
    
    expected_f3 = '''uid,organisationname,normalisedname,companyid,charitynumber,fulladdress,city,postcode,source,registrationdate,dissolutiondate
        CH_14413082,! HEAL UR TECH LTD,HEAL UR TECH LTD,14413082,,5 BRIDGE STREET,GUILDFORD,GU1 4RY,companies house,,
        CH_13220580,""" BORA "" 2 LTD",BORA 2 LTD,13220580,,"26 CARMICHAEL CLOSE, WINSTANLEY ESTATE",LONDON,SW11 2HS,companies house,,
        CH_CE000952,"""20-20 VOICE"" CANCER",2020 VOICE CANCER,CE000952,,,,,companies house,,
        CH_05914136,"""243 RUGBY ROAD MANAGEMENT COMPANY LIMITED""",243 RUGBY ROAD MANAGEMENT COMPANY LIMITED,05914136,,94 PARK LANE,CROYDON,CR0 1JB,companies house,,
        CH_12459056,"""AN IDEAL LIFE???"" CIC",AN IDEAL LIFE CIC,12459056,,197 CLAREMONT ROAD,MANCHESTER,M14 4JF,companies house,,'''
    f1 = io.StringIO(for_f1)
    
    f2 = io.StringIO(for_f2)

    f3 = io.StringIO()

    concat([f1, f2], f3)

    f3.seek(0)

    assert_files_basically_same(f3.read(), expected_f3)



@pytest.mark.xfail()
def test_concat__fails_when_incorrect_format():
    f1 = io.StringIO("first\n")
    f2 = io.StringIO("second")
    f3 = io.StringIO()

    with pytest.raises(Exception) as e_info:
        concat([f1, f2], f3)


def test_check_spine_format_fails():
    # does a file with different fields (top row) fail?
    fields = {'uid':'123','norm_name':'NAME'}
    assert check_spine_format(fields.keys()) == False

    
def test_check_spine_format_passes():
    fields = spine_entry_creator({'uid':'123'})
    assert check_spine_format(fields.keys())

def test_norm_name():
    pass
    

def test_create_uid_dict():
    # need fake file handler with data in 
    for_f1 = '''uid,organisationname,normalisedname,companyid,charitynumber,fulladdress,postcode,source
GB-CIS-CS2003000137,East Park School,EAST PARK SCHOOL,CS2003000137,,"1092 Maryhill Road, Glasgow, Glasgow City",G20 9TD,CareInspectorateScot
GB-CIS-CS2003000137,East Park,EAST PARK,CS2003000137,,"1092 Maryhill Road, Glasgow, Glasgow City",G20 9TD,CareInspectorateScot
GB-CIS-CS2003000150,Church of Scotland Trading as Crossreach,CHURCH OF SCOTLAND TRADING AS CROSSREACH,CS2003000150,,"Templeton Business Centre, Building 5, Unit 5, The Doges, Glasgow, Glasgow City",G40 1DA,CareInspectorateScot
GB-CIS-CS2003000150,Threshold Glasgow Day Opportunities,THRESHOLD GLASGOW DAY OPPORTUNITIES,CS2003000150,,"Templeton Business Centre, Building 5, Unit 5, The Doges, Glasgow, Glasgow City",G40 1DA,CareInspectorateScot
GB-CIS-CS2003000153,Jewish Care Scotland,JEWISH CARE SCOTLAND,CS2003000153,,"Walton Community Care Centre, May Terrace, Giffnock, East Renfrewshire",G46 6LD,CareInspectorateScot
GB-CIS-CS2003000153,Aviv Club,AVIV CLUB,CS2003000153,,"Walton Community Care Centre, May Terrace, Giffnock, East Renfrewshire",G46 6LD,CareInspectorateScot'''
    
    f1 = io.StringIO(for_f1)
    
    expected_dict = {
        'GB-CIS-CS2003000137':['East Park School,EAST PARK SCHOOL,CS2003000137,,"1092 Maryhill Road, Glasgow, Glasgow City",G20 9TD,CareInspectorateScot,',
                               'East Park,EAST PARK,CS2003000137,,"1092 Maryhill Road, Glasgow, Glasgow City",G20 9TD,CareInspectorateScot'],
        'GB-CIS-CS2003000150':['Church of Scotland Trading as Crossreach,CHURCH OF SCOTLAND TRADING AS CROSSREACH,CS2003000150,,"Templeton Business Centre, Building 5, Unit 5, The Doges, Glasgow, Glasgow City",G40 1DA,CareInspectorateScot',
                           'Threshold Glasgow Day Opportunities,THRESHOLD GLASGOW DAY OPPORTUNITIES,CS2003000150,,"Templeton Business Centre, Building 5, Unit 5, The Doges, Glasgow, Glasgow City",G40 1DA,CareInspectorateScot'],
        'GB-CIS-CS2003000153':['Jewish Care Scotland,JEWISH CARE SCOTLAND,CS2003000153,,"Walton Community Care Centre, May Terrace, Giffnock, East Renfrewshire",G46 6LD,CareInspectorateScot',
                       'Aviv Club,AVIV CLUB,CS2003000153,,"Walton Community Care Centre, May Terrace, Giffnock, East Renfrewshire",G46 6LD,CareInspectorateScot']

    }
    assert dict_indexed_by_field(f1,'uid').keys() == expected_dict.keys()
    

def test_consolidate_address():
    orig = spine_entry_creator({
        'housenumber':'5',
        'addressline1':'York Street',
        'addressline2':'TownArea',
        'city': 'ThisCity',
        'postcode': 'AS1 2DF',
    })
   
    fulladdress= '5, York Street, TownArea'#, ThisCity'
        
    assert consolidate_address(orig) == fulladdress

def test_dedupe_addr():
    a = [('1 King St','city','RR4 4RR'),
         ('','','RR4 4RR'),
         ('','','as3 3ad')]

    expected = [('1 King St','city','RR4 4RR'),
         ('','','as3 3ad')]

    assert dedupe_addr(a)==expected


def test_dedupe_addr_city():
    a = [('1 King St','city','RR4 4RR'),
         ('1 King St, city','','RR4 4RR'),
         ('','','as3 3ad')]

    expected = [('1 King St','city','RR4 4RR'),
         ('','','as3 3ad')]


    assert dedupe_addr(a)==expected


def test_combine_org_details():
    r1 = new_spine_entry_creator({'uid':12, 'organisationname':'name'})
    r2 = new_spine_entry_creator({'uid':12})
    r3 = new_spine_entry_creator({'uid':12,'organisationname':'other name'})
    rows = [r1,r2,r3]

    expected = [r1,r3]


    assert combine_org_details(rows,False)==expected


def test_combine_org_details_null_addr():
    r1 = new_spine_entry_creator({'uid':12, 'organisationname':'name','fulladdress':'street','postcode':'abc'})
    r2 = new_spine_entry_creator({'uid':12})
    r3 = new_spine_entry_creator({'uid':12,'organisationname':'other name'})
    rows = [r1,r2,r3]

    r4 = new_spine_entry_creator({'uid':12,'organisationname':'other name','fulladdress':'street','postcode':'abc'})
    expected = [r1,r4]


    assert combine_org_details(rows,False)==expected


def test_final_processing():
    r1 = new_spine_entry_creator({'uid':12, 'charitynumber' : 1234, 'organisationname':'name','fulladdress':'street','postcode':'abc'})
    expected = final_spine_entry_creator({'rowid':1,'uid':12,'organisationname':'name','fulladdress':'street','postcode':'abc'})

    for_f1 = '''uid,organisationname,normalisedname,companyid,charitynumber,fulladdress,city,postcode,source,registrationdate,dissolutiondate
GB-CIS-CS2003000137,East Park School,EAST PARK SCHOOL,CS2003000137,,"1092 Maryhill Road, Glasgow", Glasgow City,G20 9TD,CareInspectorateScot,,
GB-CIS-CS2003000137,East Park,EAST PARK,CS2003000137,,"1092 Maryhill Road, Glasgow", Glasgow City,G20 9TD,CareInspectorateScot,,
GB-CIS-CS2003000150,Church of Scotland Trading as Crossreach,CHURCH OF SCOTLAND TRADING AS CROSSREACH,CS2003000150,,"Templeton Business Centre, Building 5, Unit 5, The Doges", Glasgow,G40 1DA,CareInspectorateScot,,
GB-CIS-CS2003000150,Threshold Glasgow Day Opportunities,THRESHOLD GLASGOW DAY OPPORTUNITIES,CS2003000150,,"Templeton Business Centre, Building 5, Unit 5, The Doges, Glasgow", Glasgow City,G40 1DA,CareInspectorateScot,,
GB-CIS-CS2003000153,Jewish Care Scotland,JEWISH CARE SCOTLAND,CS2003000153,,"Walton Community Care Centre, May Terrace, Giffnock, East Renfrewshire",,G46 6LD,CareInspectorateScot,,
GB-CIS-CS2003000153,Aviv Club,AVIV CLUB,CS2003000153,,"Walton Community Care Centre, May Terrace, Giffnock, East Renfrewshire",,G46 6LD,CareInspectorateScot,,'''
    
    f1 = open('test_csvs/test_final_processing.csv','w+')
    f1.write(for_f1)
    f1.close()

    final_processing(open('test_csvs/test_final_processing.csv','r'))

    outputfile = 'test_csvs/test_final_processing.final.csv'
    assert os.path.exists(outputfile)
    
    outputdata = open(outputfile).read()
    
    expected =  '''rowid,uid,organisationname,normalisedname,companyid,fulladdress,city,postcode,source,registrationdate,dissolutiondate
1,GB-CIS-CS2003000137,East Park School,EAST PARK SCHOOL,CS2003000137,"1092 Maryhill Road, Glasgow", Glasgow City,G20 9TD,CareInspectorateScot,,
2,GB-CIS-CS2003000137,East Park,EAST PARK,CS2003000137,"1092 Maryhill Road, Glasgow", Glasgow City,G20 9TD,CareInspectorateScot,,
3,GB-CIS-CS2003000150,Church of Scotland Trading as Crossreach,CHURCH OF SCOTLAND TRADING AS CROSSREACH,CS2003000150,"Templeton Business Centre, Building 5, Unit 5, The Doges", Glasgow,G40 1DA,CareInspectorateScot,,
4,GB-CIS-CS2003000150,Threshold Glasgow Day Opportunities,THRESHOLD GLASGOW DAY OPPORTUNITIES,CS2003000150,"Templeton Business Centre, Building 5, Unit 5, The Doges, Glasgow", Glasgow City,G40 1DA,CareInspectorateScot,,
5,GB-CIS-CS2003000153,Jewish Care Scotland,JEWISH CARE SCOTLAND,CS2003000153,"Walton Community Care Centre, May Terrace, Giffnock, East Renfrewshire",,G46 6LD,CareInspectorateScot,,
6,GB-CIS-CS2003000153,Aviv Club,AVIV CLUB,CS2003000153,"Walton Community Care Centre, May Terrace, Giffnock, East Renfrewshire",,G46 6LD,CareInspectorateScot,,'''
    
    assert_files_basically_same(outputdata.strip(), expected)
    