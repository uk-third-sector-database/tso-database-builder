from .build_public_spine import *
import pytest
from copy import deepcopy
from handler.base_definitions import public_spine_entry_creator, sub_spine_entry_creator, extra_csv_entry_creator, match_csv_entry_creator, MATCHES_CSV_FIELDS, SUB_SPINE_CSV_FIELDS, SPINE_CSV_FIELDS, EXTRA_DETAILS_CSV_FIELDS
import tempfile


def build_spine_for_test(files):
    # the external linkage files (dkane sameas / oscr linkage) are not part of these fixtures:
    # point at clearly-nonexistent paths and allow them to be missing, so every test runs with
    # empty linkage tables regardless of what is on the machine
    return process_csvs_to_build_spine(files,
                                       allow_missing_linkage=True,
                                       sameas_file='no_such_sameas_fixture.csv',
                                       oscr_links_file='no_such_oscr_linkage_fixture.csv')


def expected_public_spine_row(overrides):
    # the published spine writes is_cic as the literal string "False" (or "True"):
    # to_main_csv() fills a blank is_cic with "False". Expected main rows therefore use
    # "False" unless a test overrides it.
    entry = public_spine_entry_creator({"is_cic" : "False"})
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


def write_csv(file_name, data, fieldnames):
    with open(file_name, mode='w+', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in data:
            if any(field.strip() for field in row.values()):
                filtered_row = {key: row[key] for key in fieldnames if key in row}
                writer.writerow(filtered_row)
    # print(f'Data saved to {file_name}')
    return file_name

def write_expected_data_to_tmp_file(data, supplementarydata, matchesdata):
    with tempfile.NamedTemporaryFile(mode='w', delete=False, newline='', suffix='.csv') as tmp_file:
#        base_name = tmp_file.name.strip('.csv')
        base_name, file_ext = os.path.splitext(tmp_file.name)
        main_file = write_csv(tmp_file.name, data, SPINE_CSV_FIELDS)
        supplementary_file = write_csv(f'{base_name}.supplementary.csv', supplementarydata, EXTRA_DETAILS_CSV_FIELDS)
        matches_file = write_csv(f'{base_name}.matches.csv', matchesdata, MATCHES_CSV_FIELDS)
    
    return main_file, supplementary_file, matches_file

def write_input_data_to_tmp_file(data, supplementarydata, fieldnames):
    with tempfile.NamedTemporaryFile(mode='w', delete=False, newline='', suffix='.csv') as tmp_file:
        #base_name = tmp_file.name.strip('.csv')
        base_name, file_ext = os.path.splitext(tmp_file.name)
        
        main_file = write_csv(tmp_file.name, data, fieldnames)
        supplementary_file = write_csv(f'{base_name}.supplementary.csv', supplementarydata, EXTRA_DETAILS_CSV_FIELDS)
        print(f'{base_name}.supplementary.csv')
        
    return main_file

@pytest.fixture
def setup_base_oscr_orgs():
    b = sub_spine_entry_creator({
        "uid" : "GB-SC-101",
        "organisationname" : "101 Trust Fund",
        "normalisedname" : "101 TRUST FUND",
        "fulladdress" : "1 Trust Fund Lane",
        "city" : "Dundee",
        "postcode" : "LL1 1LL",
        "companyid" : "",
        "registerdate" : "23/06/1961",
        "removeddate" : "23/06/2019",
        "source" : "oscr",
        "id_in_source" : "101",})

    b1 = sub_spine_entry_creator({
        "uid" : "GB-SC-102",
        "organisationname" : "The Charity group",
        "normalisedname" : "THE CHARITY GROUP",
        "fulladdress" : "High Street House",
        "city" : "Edinburgh",
        "postcode" : "EH1 1EH",
        "companyid" : "",
        "registerdate" : "01/06/1998",
        "removeddate" : "",
        "source" : "oscr",
        "id_in_source" : "102",})
    
    b2 = sub_spine_entry_creator({
        "uid" : "GB-SC-103",
        "organisationname" : "The 41st Charity group",
        "normalisedname" : "THE 41ST CHARITY GROUP",
        "fulladdress" : "High Street House",
        "city" : "Glasgow",
        "postcode" : "G1 1EH",
        "companyid" : "",
        "registerdate" : "01/12/1999",
        "removeddate" : "",
        "source" : "oscr",
        "id_in_source" : "103",})
    
    b['crossborder']='1'
    b1['crossborder']=''
    b2['crossborder']=''

    return [b,b1,b2]

@pytest.fixture
def setup_base_ccew_orgs():
    b = sub_spine_entry_creator({
       "uid" : "GB-CHC-1001",
       "organisationname" : "101 Trust Fund",
       "normalisedname" : "101 TRUST FUND",
       "fulladdress" : "1 Trust Fund Lane",
       "city" : "Dundee",
       "postcode" : "LL1 1LL",
       "companyid" : "1234",
       "registerdate" : "23/06/1961",
       "removeddate" : "23/06/2019",
       "source" : "ccew",
       "id_in_source" : "1001",})
    
    b1 = sub_spine_entry_creator({
       "uid" : "GB-CHC-1002",
       "organisationname" : "The Charity group",
       "normalisedname" : "THE CHARITY GROUP",
       "fulladdress" : "High Street House",
       "city" : "Edinburgh",
       "postcode" : "EH1 1EH",
       "companyid" : "",
       "registerdate" : "01/06/1998",
       "removeddate" : "",
       "source" : "ccew",
       "id_in_source" : "1002",})
   
    b2 = sub_spine_entry_creator({
       "uid" : "GB-CHC-1003",
       "organisationname" : "The 51st Charity group",
       "normalisedname" : "THE 51ST CHARITY GROUP",
       "fulladdress" : "High Street House",
       "city" : "Glasgow",
       "postcode" : "G1 1EH",
       "companyid" : "",
       "registerdate" : "01/12/1990",
       "removeddate" : "",
       "source" : "ccew",
       "id_in_source" : "1003",})
    
    b['cqc_reg'] = ''
    b1['cqc_reg'] = ''
    b2['cqc_reg'] = ''
    
    return [b,b1,b2]
    
# add a @pytest.mark.parametrize() to run this with different inputs/expectations
# change a SC entry so it has to go to extras
# change a CHC entry so the match is multiple
# 

def test_oscr_merge_in(setup_base_ccew_orgs,setup_base_oscr_orgs):
    oscr_datarows = setup_base_oscr_orgs
    ccew_datarows = setup_base_ccew_orgs
    oscr_extras = [extra_csv_entry_creator({})]
    ccew_extras = [extra_csv_entry_creator({})]
    
    oscr_file = write_input_data_to_tmp_file(oscr_datarows,oscr_extras,SUB_SPINE_CSV_FIELDS+['crossborder'])
    ccew_file = write_input_data_to_tmp_file(ccew_datarows,ccew_extras,SUB_SPINE_CSV_FIELDS)
    
    main_orgs = build_spine_for_test([ccew_file,oscr_file])
    

    # Write out to temporary files in a temp directory
    with tempfile.TemporaryDirectory() as temp_dir:
        print(temp_dir)
        main_file = f"{temp_dir}/main.csv"
        extra_file = f"{temp_dir}/extra.csv"
        match_file = f"{temp_dir}/match.csv"
        main_orgs.write_out(main_file, extra_file, match_file)
        # Read the contents of the temporary files
        with open(main_file) as main_csv_file:
            main_csv = main_csv_file.read()
            print(f'main_csv, output of process_csvs_to_build_spine: {main_csv}')
        with open(extra_file) as extra_csv_file:
            extra_csv = extra_csv_file.read()
        with open(match_file) as match_csv_file:
            match_csv = match_csv_file.read()

    expected_main_rows = [
    expected_public_spine_row({
        "uid" : "GB-CHC-1001",
        "organisationname" : "101 Trust Fund",
        "normalisedname" : "101 TRUST FUND",
        "fulladdress" : "1 Trust Fund Lane",
        "city" : "Dundee",
        "postcode" : "LL1 1LL",
        "registerdate" : "23/06/1961",
        "removeddate" : "23/06/2019",}),
    expected_public_spine_row({
        "uid" : "GB-CHC-1002",
        "organisationname" : "The Charity group",
        "normalisedname" : "THE CHARITY GROUP",
        "fulladdress" : "High Street House",
        "city" : "Edinburgh",
        "postcode" : "EH1 1EH",
        "registerdate" : "01/06/1998",
        }),
    expected_public_spine_row({
        "uid" : "GB-CHC-1003",
        "organisationname" : "The 51st Charity group",
        "normalisedname" : "THE 51ST CHARITY GROUP",
        "fulladdress" : "High Street House",
        "city" : "Glasgow",
        "postcode" : "G1 1EH",
        "registerdate" : "01/12/1990",
        }),
    expected_public_spine_row({"uid" : "GB-SC-102",
        "organisationname" : "The Charity group",
        "normalisedname" : "THE CHARITY GROUP",
        "fulladdress" : "High Street House",
        "city" : "Edinburgh",
        "postcode" : "EH1 1EH",
        "companyid" : "",
        "registerdate" : "01/06/1998",
        "removeddate" : "",
        }),
    expected_public_spine_row({
        "uid" : "GB-SC-103",
        "organisationname" : "The 41st Charity group",
        "normalisedname" : "THE 41ST CHARITY GROUP",
        "fulladdress" : "High Street House",
        "city" : "Glasgow",
        "postcode" : "G1 1EH",
        "registerdate" : "01/12/1999",
        }),]


    expected_extra_rows = []#extra_csv_entry_creator({})]

    expected_main_csv,expected_extra_csv,b = write_expected_data_to_tmp_file(expected_main_rows,expected_extra_rows,[])

    with open(expected_main_csv) as csv_file:
        expected_main_csv = csv_file.read()

    assert_files_basically_same(main_csv, expected_main_csv)

    with open(expected_extra_csv) as csv_file:
        expected_extra_csv = csv_file.read()

    assert_files_basically_same(extra_csv, expected_extra_csv)
    

def test_oscr_merge_extras(setup_base_ccew_orgs,setup_base_oscr_orgs):
    oscr_datarows = setup_base_oscr_orgs
    ccew_datarows = setup_base_ccew_orgs

    # edit OSCR to create a link with additional data
    oscr_datarows[0]['city'] = 'Perth'
    oscr_datarows[0]['postcode'] = 'PL1 1LL'
    print(f'oscr_datarows = {oscr_datarows}')
    oscr_extras = [extra_csv_entry_creator({})]
    ccew_extras = [extra_csv_entry_creator({})]
    
    oscr_file = write_input_data_to_tmp_file(oscr_datarows,oscr_extras,SUB_SPINE_CSV_FIELDS+['crossborder'])
    ccew_file = write_input_data_to_tmp_file(ccew_datarows,ccew_extras,SUB_SPINE_CSV_FIELDS)

    main_orgs = build_spine_for_test([ccew_file,oscr_file])
    print('STORES: ')
    print(f'_store = {main_orgs._store}')
    print(f'byname = {main_orgs.byname}')
    print(f'bycompanyid = {main_orgs.bycompanyid}')
    print(f'bysourceid = {main_orgs.bysourceid}')

    print(f'\n\nMainOrgs =  {[(i.uid,i.matched_orgs) for i in main_orgs._store.values()]}')

    # Write out to temporary files in a temp directory
    with tempfile.TemporaryDirectory() as temp_dir:
        print(temp_dir)
        main_file = f"{temp_dir}/main.csv"
        extra_file = f"{temp_dir}/extra.csv"
        match_file = f"{temp_dir}/match.csv"

        # function being tested:
        main_orgs.write_out(main_file, extra_file, match_file)
        
        # Read the contents of the temporary files
        with open(main_file) as main_csv_file, open(extra_file) as extra_csv_file, open(match_file) as match_csv_file:
            main_csv = main_csv_file.read()
            extra_csv = extra_csv_file.read()
            match_csv = match_csv_file.read()

        
        
        
    expected_main_rows = [
    expected_public_spine_row({
        "uid" : "GB-CHC-1001",
        "organisationname" : "101 Trust Fund",
        "normalisedname" : "101 TRUST FUND",
        "fulladdress" : "1 Trust Fund Lane",
        "city" : "Dundee",
        "postcode" : "LL1 1LL",
        "registerdate" : "23/06/1961",
        "removeddate" : "23/06/2019",
        }),
    expected_public_spine_row({
        "uid" : "GB-CHC-1002",
        "organisationname" : "The Charity group",
        "normalisedname" : "THE CHARITY GROUP",
        "fulladdress" : "High Street House",
        "city" : "Edinburgh",
        "postcode" : "EH1 1EH",
        "registerdate" : "01/06/1998",
        }),
    expected_public_spine_row({
        "uid" : "GB-CHC-1003",
        "organisationname" : "The 51st Charity group",
        "normalisedname" : "THE 51ST CHARITY GROUP",
        "fulladdress" : "High Street House",
        "city" : "Glasgow",
        "postcode" : "G1 1EH",
        "registerdate" : "01/12/1990",
        }),
    expected_public_spine_row({"uid" : "GB-SC-102",
        "organisationname" : "The Charity group",
        "normalisedname" : "THE CHARITY GROUP",
        "fulladdress" : "High Street House",
        "city" : "Edinburgh",
        "postcode" : "EH1 1EH",
        "companyid" : "",
        "registerdate" : "01/06/1998",
        "removeddate" : "",
        }),
    expected_public_spine_row({
        "uid" : "GB-SC-103",
        "organisationname" : "The 41st Charity group",
        "normalisedname" : "THE 41ST CHARITY GROUP",
        "fulladdress" : "High Street House",
        "city" : "Glasgow",
        "postcode" : "G1 1EH",
        "registerdate" : "01/12/1999",
        })]
    
    expected_extra_rows = [extra_csv_entry_creator({"uid" : "GB-SC-101",
                                                "city" : "Perth",
                                                "fulladdress" : "1 Trust Fund Lane",
                                                "postcode" : "PL1 1LL",
                                                "source" : "oscr",})]
    
    expected_match_row = [match_csv_entry_creator({"uid" : 'GB-CHC-1001',
    "orgA_id_in_source" : "1001",
    "orgA_source" : "ccew",
    "orgA_uid" : "GB-CHC-1001",
    "orgB_id_in_source" : "101",
    "orgB_source" : "oscr",
    "orgB_uid" : "GB-SC-101",
    'match_type' : "name - crossborder",})]

    expected_main_csv, expected_extra_csv, expected_matches_csv = write_expected_data_to_tmp_file(expected_main_rows,expected_extra_rows,expected_match_row)
    print(f' expected_MAIN_csv = {expected_main_csv}')
    print(f' expected_EXTRAS_csv = {expected_extra_csv}')
    print(f' expected_MATCHES_csv = {expected_matches_csv}')
    with open(expected_main_csv) as csv_file:
        expected_main_csv = csv_file.read()

    assert main_csv == expected_main_csv

    with open(expected_extra_csv) as csv_file:
        expected_extra_csv = csv_file.read()

    print(' extra_csv = ', extra_csv)
    assert_files_basically_same(extra_csv, expected_extra_csv)

    
    with open(expected_matches_csv) as csv_file:
        expected_matches_csv = csv_file.read()
    
    assert_files_basically_same(match_csv, expected_matches_csv)


@pytest.mark.parametrize('reg_dateA,reg_dateB,expected_primary_date,expected_extra_date,expected_extra_source',
[('01/01/2010','','01/01/2010','',''),
('01/01/2010','01/04/2010','01/01/2010','01/04/2010','oscr'),
('01/01/2010','01/04/2009','01/04/2009','01/01/2010','ccew')
])
def test_merge_dates(reg_dateA, reg_dateB, expected_primary_date, expected_extra_date, expected_extra_source):
    baserow = sub_spine_entry_creator({
        "uid" : "GB-CHC-001",
        "organisationname" : "org",
        "normalisedname" : "ORG",
        "registerdate" : reg_dateA,
        "source" : "ccew",
        "id_in_source" : "001",})
    if reg_dateB:
        new_row = sub_spine_entry_creator({
            "uid" : "GB-SC-44",
            "organisationname" : "org",
            "normalisedname" : "ORG",
            "registerdate" : reg_dateB,
            "source" : "oscr",
            "crossborder" : '1',
            "id_in_source" : "44",})
        if expected_extra_source == 'oscr': uid = "GB-SC-44"
        else: uid =  "GB-CHC-001"
        expected_extra = extra_csv_entry_creator({"uid" : uid,
          "registerdate" : expected_extra_date,
            "source" : expected_extra_source,})
    else:
        new_row = sub_spine_entry_creator({})
        expected_extra = extra_csv_entry_creator({})

    expected_main = expected_public_spine_row({
        "uid" : "GB-CHC-001",
        "organisationname" : "org",
        "normalisedname" : "ORG",
        "registerdate" : expected_primary_date,
        })

    base_file = write_input_data_to_tmp_file([baserow],[],SUB_SPINE_CSV_FIELDS)
    print(f'base_file = {base_file}')
    new_file = write_input_data_to_tmp_file([new_row],[],SUB_SPINE_CSV_FIELDS+['crossborder'])

    expected_main_csv, expected_extra_csv, expected_matches_csv = write_expected_data_to_tmp_file([expected_main],[expected_extra],[])
    print(f'expected_main_csv = {expected_main_csv}')
    with open(expected_main_csv) as csv_file: expected_main_csv = csv_file.read()
    with open(expected_extra_csv) as csv_file: expected_extra_csv = csv_file.read()

    
    main_orgs = build_spine_for_test([base_file,new_file])
    print('STORES after process_csvs_to_build_spine: ')
    print(f'_store = {main_orgs._store}')
    print(f'byname = {main_orgs.byname}')
    print(f'bycompanyid = {main_orgs.bycompanyid}')
    print(f'bysourceid = {main_orgs.bysourceid}')
    
    # Write out to temporary files in a temp directory
    with tempfile.TemporaryDirectory() as temp_dir:
        main_file = f"{temp_dir}/main.csv"
        extra_file = f"{temp_dir}/extra.csv"
        match_file = f"{temp_dir}/match.csv"

        # function being tested:
        main_orgs.write_out(main_file, extra_file, match_file)
        print('\n\nSTORES after write_out: ')
        print(f'_store = {main_orgs._store}')
        print(f'byname = {main_orgs.byname}')
        print(f'bycompanyid = {main_orgs.bycompanyid}')
        print(f'bysourceid = {main_orgs.bysourceid}')
        
        # Read the contents of the temporary files
        with open(main_file) as main_csv_file, open(extra_file) as extra_csv_file, open(match_file) as match_csv_file:
            main_csv = main_csv_file.read()
            extra_csv = extra_csv_file.read()
            match_csv = match_csv_file.read()

        
        
    
    assert main_csv == expected_main_csv
    assert_files_basically_same(extra_csv, expected_extra_csv)

def test_sort_extras():
    baserow = sub_spine_entry_creator({
        "uid" : "GB-CHC-001",
        "organisationname" : "org",
        "normalisedname" : "ORG",
        "registerdate" : '01/01/1990',
        "source" : "ccew",
        "id_in_source" : "001",})        
    new_row = sub_spine_entry_creator({
        "uid" : "GB-SC-44",
        "organisationname" : "org",
        "normalisedname" : "ORG",
        "registerdate" : '01/01/1991',
        "source" : "oscr",
        "crossborder" : '1',
        "id_in_source" : "44",})
    
    expected_main = expected_public_spine_row({
        "uid" : "GB-CHC-001",
        "organisationname" : "org",
        "normalisedname" : "ORG",
        "registerdate" : '01/01/1990',
        }),
    expected_extra = extra_csv_entry_creator(
        {"uid" : "GB-SC-44",
        "registerdate" : '01/01/1991',
        "source" : "oscr",})

    base_file = write_input_data_to_tmp_file([baserow],[],SUB_SPINE_CSV_FIELDS)
    new_file = write_input_data_to_tmp_file([new_row],[],SUB_SPINE_CSV_FIELDS+['crossborder'])

        
    main_orgs = build_spine_for_test([base_file,new_file])
    print('STORES after process_csvs_to_build_spine: ')
    print(f'_store = {main_orgs._store}')
    print(f'byname = {main_orgs.byname}')
    print(f'bycompanyid = {main_orgs.bycompanyid}')
    print(f'bysourceid = {main_orgs.bysourceid}')
    
    expected_extra = ExtraInfo(
        uid = "GB-SC-44",
        registerdate = '01/01/1991',
        source = "oscr",)

    main_orgs._store["GB-CHC-001"].sort_matches()
    main_orgs._store["GB-CHC-001"].sort_extras()
    print('STORES after sort_extras: ')
    print(f'_store = {main_orgs._store}')
    assert main_orgs._store["GB-CHC-001"].extras == [expected_extra]
    


def test_extras_no_change():
    baserow = sub_spine_entry_creator({
    "uid" : "GB-SC-44",
    "organisationname" : "org",
    "normalisedname" : "ORG",
    "registerdate" : '01/01/1990',
    "source" : "oscr",
    "id_in_source" : "44",})  
    extra = extra_csv_entry_creator(
    {"uid" : "GB-SC-44",
    "registerdate" : '01/01/1991',
    "source" : "oscr",})      

    base_file = write_input_data_to_tmp_file([baserow],[extra],SUB_SPINE_CSV_FIELDS)
    supp_file = base_file.replace('.csv','.supplementary.csv')

    main_orgs = build_spine_for_test([base_file])
    with tempfile.TemporaryDirectory() as temp_dir:
        main_file = f"{temp_dir}/main.csv"
        extra_file = f"{temp_dir}/extra.csv"
        match_file = f"{temp_dir}/match.csv"

        main_orgs.write_out(main_file, extra_file, match_file)

        with open(main_file) as main_csv_file, open(extra_file) as extra_csv_file, open(base_file) as expected_main_file, open(supp_file) as expected_supp_file:
            main_csv = main_csv_file.read()
            extra_csv = extra_csv_file.read()


            expected_supp = expected_supp_file.read()
    
    assert_files_basically_same(extra_csv, expected_supp)

# (a commented-out xfail marker used to sit here: the per-uid compression it referred to is
# now implemented in build_public_spine.compress_extras_per_uid, applied in sort_extras)
def test_sort_extras_compressed(setup_base_ccew_orgs):
    '''supplementary file should have data compressed, so that all data for a given uid is on one line, unless the course provided more than one entry for a given field'''
    
    # one organisation:
    ccew_row = setup_base_ccew_orgs[0]
    print(ccew_row)
    # supplementary data:
    ccew_extras = [extra_csv_entry_creator({"uid" : "GB-CHC-1001",
                    "organisationname" : "1001 Trust Fund"}),
                extra_csv_entry_creator({"uid" : "GB-CHC-1001",
                    "fulladdress" : "An old address",
                    "city" : "Dundee",
                    "postcode" : "LL1 1LJ",}),
                extra_csv_entry_creator({"uid" : "GB-CHC-1001",
                    "registerdate" : "23/07/1961"}),
                extra_csv_entry_creator({"uid" : "GB-CHC-1001",
                    "removeddate" : "01/01/2019"})]
    
    # expected spine file:
    expected_spine = expected_public_spine_row({**ccew_row})
    print(expected_spine)
    # expected supplementary file:
    expected_supp = extra_csv_entry_creator({"uid" : "GB-CHC-1001",
                                            "organisationname" : "1001 Trust Fund",
                                            "fulladdress" : "An old address",
                                            "city" : "Dundee",
                                            "postcode" : "LL1 1LJ", # matches the input extra above (a previous expectation had a typo, 'LL1 1LLJ')
                                            "registerdate" : "23/07/1961",
                                            "removeddate" : "01/01/2019"})
    
    # write input data to files:
    ccew_file = write_input_data_to_tmp_file([ccew_row],ccew_extras,SUB_SPINE_CSV_FIELDS)
    supp_file = ccew_file.replace('.csv','.supplementary.csv')

    # process:
    main_orgs = build_spine_for_test([ccew_file])
    print(main_orgs)
    assert len(main_orgs._store["GB-CHC-1001"].extras) == len(ccew_extras)

    # write expected data to files:
    expected_main_csv, expected_extra_csv, _ = write_expected_data_to_tmp_file([expected_spine],[expected_supp],[])
    print(f'expected_main_csv = {expected_main_csv}')
    with open(expected_main_csv) as csv_file: expected_main_csv = csv_file.read()
    with open(expected_extra_csv) as csv_file: expected_extra_csv = csv_file.read()

    # do the write_out process - this is what we're testing
    with tempfile.TemporaryDirectory() as temp_dir:
        main_file = f"{temp_dir}/main.csv"
        extra_file = f"{temp_dir}/extra.csv"
        match_file = f"{temp_dir}/match.csv"
        main_orgs.write_out(main_file, extra_file, match_file)
        with open(main_file) as main_csv_file, open(extra_file) as extra_csv_file:
            main_csv = main_csv_file.read()
            extra_csv = extra_csv_file.read()

    assert_files_basically_same(extra_csv, expected_extra_csv)



def test_build_subspine_list(setup_base_oscr_orgs):

    oscr_datarows = setup_base_oscr_orgs
        
    oscr_file = write_input_data_to_tmp_file(oscr_datarows,[],SUB_SPINE_CSV_FIELDS+['crossborder'])

    # build list:
    l = convert_csv_to_list_of_subspine_orgs(oscr_file)

    expected_l = [SubSpineOrg(**row) for row in oscr_datarows]

    assert expected_l == l


# repeat CIS tests for CQC (@pytest.mark.parameterise)
@pytest.mark.parametrize('basesource,mergesource,basename,mergename,match_expected',
[('oscr','CareInspectorateScot','ORG','ORG',True),
('ccew','CareInspectorateScot','ORG','ORG',False),

])
def test_CIS_link(basesource,mergesource,basename,mergename,match_expected):
    baserow = sub_spine_entry_creator({
        "uid" : "GB-SC-001",
        "organisationname" : "org",
        "normalisedname" : basename,
        "registerdate" : '01/01/1990',
        "source" : basesource,
        "id_in_source" : "001",})
    cis_row = sub_spine_entry_creator({
            "uid" : "GB-CIS-44",
            "organisationname" : "org",
            "normalisedname" : mergename,
            "registerdate" : '01/01/1991',
            "source" : mergesource,
            "id_in_source" : "44",})


    expected_main = expected_public_spine_row({
        "uid" : "GB-SC-001",
        "organisationname" : "org",
        "normalisedname" : basename,
        "registerdate" : '01/01/1990',
        })
    if match_expected:
        expected_extra = extra_csv_entry_creator({"uid" : "GB-CIS-44",
            "registerdate" : '01/01/1991',
            "source" : "CareInspectorateScot",})
        expected_match = match_csv_entry_creator({
            "uid" : 'GB-SC-001',
            "orgA_id_in_source" : "001",
            "orgA_source" : basesource,
            "orgA_uid" : 'GB-SC-001',
            "orgB_id_in_source" : "44",
            "orgB_source" : mergesource,
            "orgB_uid" : "GB-CIS-44",
            'match_type' : "name - care",})
    else:
        expected_match = match_csv_entry_creator({})
        expected_extra = extra_csv_entry_creator({})
    

    base_file = write_input_data_to_tmp_file([baserow],[],SUB_SPINE_CSV_FIELDS)
    new_file = write_input_data_to_tmp_file([cis_row],[],SUB_SPINE_CSV_FIELDS)

    expected_main_csv, expected_extra_csv, expected_matches_csv = write_expected_data_to_tmp_file([expected_main],[expected_extra],[expected_match])
    print(f'expected_main_csv = {expected_main_csv}')
    with open(expected_main_csv) as csv_file: expected_main_csv = csv_file.read()
    with open(expected_extra_csv) as csv_file: expected_extra_csv = csv_file.read()
    with open(expected_matches_csv) as csv_file: expected_match_csv = csv_file.read()

    
    main_orgs = build_spine_for_test([base_file,new_file])
    print('STORES after process_csvs_to_build_spine: ')
    print(f'_store = {main_orgs._store}')
    print(f'byname = {main_orgs.byname}')
    print(f'bycompanyid = {main_orgs.bycompanyid}')
    print(f'bysourceid = {main_orgs.bysourceid}')
    
    # Write out to temporary files in a temp directory
    with tempfile.TemporaryDirectory() as temp_dir:
        main_file = f"{temp_dir}/main.csv"
        extra_file = f"{temp_dir}/extra.csv"
        match_file = f"{temp_dir}/match.csv"

        # function being tested:
        main_orgs.write_out(main_file, extra_file, match_file)
        print('\n\nSTORES after write_out: ')
        print(f'_store = {main_orgs._store}')
        print(f'byname = {main_orgs.byname}')
        print(f'bycompanyid = {main_orgs.bycompanyid}')
        print(f'bysourceid = {main_orgs.bysourceid}')
        
        # Read the contents of the temporary files
        with open(main_file) as main_csv_file, open(extra_file) as extra_csv_file, open(match_file) as match_csv_file:
            main_csv = main_csv_file.read()
            extra_csv = extra_csv_file.read()
            match_csv = match_csv_file.read()

        
        
    
    assert main_csv == expected_main_csv
    assert_files_basically_same(extra_csv, expected_extra_csv)
    assert_files_basically_same(match_csv, expected_match_csv)

@pytest.mark.parametrize('ccew_remdate,oscr_remdate',
[('01/02/2019',''),
('','01/02/2019')])
def test_degreg_date(setup_base_ccew_orgs,setup_base_oscr_orgs,ccew_remdate,oscr_remdate):
    # when there's a match, only fill spine dereg date if all matched orgs have also been deregistered
    
    oscr_datarow = [setup_base_oscr_orgs[0]]
    ccew_datarow = [setup_base_ccew_orgs[0]]
    ccew_datarow[0]['removeddate'] =  ccew_remdate
    oscr_datarow[0]['removeddate'] = oscr_remdate
    oscr_extras = [extra_csv_entry_creator({})]
    ccew_extras = [extra_csv_entry_creator({})]
    
    oscr_file = write_input_data_to_tmp_file(oscr_datarow,oscr_extras,SUB_SPINE_CSV_FIELDS+['crossborder'])
    ccew_file = write_input_data_to_tmp_file(ccew_datarow,ccew_extras,SUB_SPINE_CSV_FIELDS)
    
    main_orgs = build_spine_for_test([ccew_file,oscr_file])
    

    # Write out to temporary files in a temp directory
    with tempfile.TemporaryDirectory() as temp_dir:
        print(temp_dir)
        main_file = f"{temp_dir}/main.csv"
        extra_file = f"{temp_dir}/extra.csv"
        match_file = f"{temp_dir}/match.csv"
        main_orgs.write_out(main_file, extra_file, match_file)
        # Read the contents of the temporary files
        with open(main_file) as main_csv_file:
            main_csv = main_csv_file.read()
            print(f'main_csv, output of process_csvs_to_build_spine: {main_csv}')
        with open(extra_file) as extra_csv_file:
            extra_csv = extra_csv_file.read()
        with open(match_file) as match_csv_file:
            match_csv = match_csv_file.read()

    expected_main_rows = [
    expected_public_spine_row({
        "uid" : "GB-CHC-1001",
        "organisationname" : "101 Trust Fund",
        "normalisedname" : "101 TRUST FUND",
        "fulladdress" : "1 Trust Fund Lane",
        "city" : "Dundee",
        "postcode" : "LL1 1LL",
        "registerdate" : "23/06/1961",
        # deliberate behaviour (March change): CCEW is the primary register, so a CCEW removal
        # date stands in the spine even when a matched record (here OSCR) is still active.
        # When CCEW has no removal date, the spine removal date stays blank.
        "removeddate" : ccew_remdate,}),
    ]


    expected_extra_rows = []#extra_csv_entry_creator({})]

    expected_main_csv,expected_extra_csv,b = write_expected_data_to_tmp_file(expected_main_rows,expected_extra_rows,[])

    with open(expected_main_csv) as csv_file:
        expected_main_csv = csv_file.read()

    assert_files_basically_same(main_csv, expected_main_csv)

        



def test_empty_extras():
    e = ExtraInfo(uid='1')
    assert e.isempty() == True


def test_missing_linkage_files():
    # a missing external linkage file must be a hard error naming the file, unless the
    # caller explicitly opts out with allow_missing_linkage=True (empty linkage tables)
    row = sub_spine_entry_creator({
        "uid" : "GB-CHC-900",
        "organisationname" : "org",
        "normalisedname" : "ORG",
        "source" : "ccew",
        "id_in_source" : "900",})
    base_file = write_input_data_to_tmp_file([row],[],SUB_SPINE_CSV_FIELDS)

    with pytest.raises(RuntimeError, match='no_such_sameas_fixture.csv'):
        process_csvs_to_build_spine([base_file],
                                    sameas_file='no_such_sameas_fixture.csv',
                                    oscr_links_file='no_such_oscr_linkage_fixture.csv')

    main_orgs = process_csvs_to_build_spine([base_file],
                                            allow_missing_linkage=True,
                                            sameas_file='no_such_sameas_fixture.csv',
                                            oscr_links_file='no_such_oscr_linkage_fixture.csv')
    assert list(main_orgs._store.keys()) == ['GB-CHC-900']

    from spine import build_public_spine as bps
    assert bps.ftc_dict == {}
    assert bps.oscr_linkage_lookup == {}


def test_name_rule_matches_only_qualifying_candidates():
    # regression test for the over-merge fix: three same-name organisations are in the spine
    # (oscr + ccew + Companies House), then a careinspectoratescot record of the same name
    # arrives. The 'name - care' rule qualifies only the OSCR organisation, so the record must
    # merge into it alone - not into every organisation sharing the name.
    base_rows = [
        sub_spine_entry_creator({
            "uid" : "GB-SC-301",
            "organisationname" : "Shared Name",
            "normalisedname" : "SHARED NAME",
            "source" : "oscr",
            "id_in_source" : "301",}),
        sub_spine_entry_creator({
            "uid" : "GB-CHC-302",
            "organisationname" : "Shared Name",
            "normalisedname" : "SHARED NAME",
            "source" : "ccew",
            "id_in_source" : "302",}),
        sub_spine_entry_creator({
            "uid" : "GB-COH-303",
            "organisationname" : "Shared Name",
            "normalisedname" : "SHARED NAME",
            "source" : "CH",
            "id_in_source" : "303",}),
    ]
    cis_row = sub_spine_entry_creator({
        "uid" : "GB-CIS-304",
        "organisationname" : "Shared Name",
        "normalisedname" : "SHARED NAME",
        "source" : "careinspectoratescot",
        "id_in_source" : "304",})

    base_file = write_input_data_to_tmp_file(base_rows,[],SUB_SPINE_CSV_FIELDS)
    cis_file = write_input_data_to_tmp_file([cis_row],[],SUB_SPINE_CSV_FIELDS)

    main_orgs = build_spine_for_test([base_file,cis_file])

    absorbed_into = [org for org in main_orgs._store.values()
                     if any(m.uid == 'GB-CIS-304' for m,mt in org.matched_orgs)]
    assert len(absorbed_into) == 1
    assert absorbed_into[0].uid == 'GB-SC-301'
    # the same-name ccew and Companies House organisations are untouched
    assert main_orgs._store['GB-CHC-302'].matched_orgs == []
    assert main_orgs._store['GB-COH-303'].matched_orgs == []
    # the record was merged, not added as its own spine organisation
    assert 'GB-CIS-304' not in main_orgs._store


def test_same_name_record_merged_into_one_org_only():
    # regression test for the multi-merge fix (reviewer's scenario): two CCEW charities and a
    # Companies House company all named "COMMUNITY ASSOCIATION" are in the spine; a
    # socialhousingengland record of the same name arrives. It must be merged into at most one
    # CCEW organisation (the best match), never into the Companies House record, and the other
    # CCEW organisation keeps an association-only match row (blank uid, not absorbed).
    ccew_rows = [
        sub_spine_entry_creator({
            "uid" : "GB-CHC-2001",
            "organisationname" : "Community Association",
            "normalisedname" : "COMMUNITY ASSOCIATION",
            "source" : "ccew",
            "id_in_source" : "2001",}),
        sub_spine_entry_creator({
            "uid" : "GB-CHC-2002",
            "organisationname" : "Community Association",
            "normalisedname" : "COMMUNITY ASSOCIATION",
            "source" : "ccew",
            "id_in_source" : "2002",}),
    ]
    ch_row = sub_spine_entry_creator({
        "uid" : "GB-COH-2003",
        "organisationname" : "Community Association",
        "normalisedname" : "COMMUNITY ASSOCIATION",
        "source" : "CH",
        "id_in_source" : "2003",})
    she_row = sub_spine_entry_creator({
        "uid" : "GB-SHPE-2004",
        "organisationname" : "Community Association",
        "normalisedname" : "COMMUNITY ASSOCIATION",
        "source" : "socialhousingengland",
        "id_in_source" : "2004",})

    ccew_file = write_input_data_to_tmp_file(ccew_rows,[],SUB_SPINE_CSV_FIELDS)
    ch_file = write_input_data_to_tmp_file([ch_row],[],SUB_SPINE_CSV_FIELDS)
    she_file = write_input_data_to_tmp_file([she_row],[],SUB_SPINE_CSV_FIELDS)

    main_orgs = build_spine_for_test([ccew_file,ch_file,she_file])

    absorbed_into = [org for org in main_orgs._store.values()
                     if any(m.uid == 'GB-SHPE-2004' for m,mt in org.matched_orgs)]
    # merged into exactly one organisation, and it is a CCEW charity
    assert len(absorbed_into) == 1
    assert absorbed_into[0].source.lower() == 'ccew'
    # never merged into the Companies House record
    assert not any(m.uid == 'GB-SHPE-2004' for m,mt in main_orgs._store['GB-COH-2003'].matched_orgs)
    # the record does not become its own spine organisation
    assert 'GB-SHPE-2004' not in main_orgs._store
    # the other CCEW organisation keeps an association-only match row (blank uid)
    other_ccew = [org for org in main_orgs._store.values()
                  if org.source.lower() == 'ccew' and org.uid != absorbed_into[0].uid]
    assert len(other_ccew) == 1
    assert any(r.orgB_uid == 'GB-SHPE-2004' and r.uid == '' and r.match_type == 'name - housing'
               for r in other_ccew[0].sorted_matches)


# ---------------------------------------------------------------------------
# CQC identifier-based matching (CQC API data carries Companies House and
# charity numbers - see acquire/cqc_api.py and handler/careQC.py)
# ---------------------------------------------------------------------------

def make_cqc_row(**overrides):
    row = sub_spine_entry_creator({
        "uid" : "GB-CQC-1-101601999",
        "organisationname" : "Sunrise Care Provider",
        "normalisedname" : "SUNRISE CARE PROVIDER",
        "source" : "carequalitycommission",
        "id_in_source" : "1-101601999",})
    row['charitynumber'] = ''
    row.update(**overrides)
    return row


def write_spine_and_read(main_orgs):
    with tempfile.TemporaryDirectory() as temp_dir:
        main_orgs.write_out(f"{temp_dir}/main.csv", f"{temp_dir}/extra.csv", f"{temp_dir}/match.csv")
        with open(f"{temp_dir}/main.csv") as f: main_csv = f.read()
        with open(f"{temp_dir}/match.csv") as f: match_csv = f.read()
    return main_csv, match_csv


def test_cqc_companyid_match():
    # a CQC provider carrying a Companies House number links to the Companies House
    # organisation via the 'companyid - cqc' rule, even though the names differ
    ch_row = sub_spine_entry_creator({
        "uid" : "GB-COH-04378206",
        "organisationname" : "Sunrise Care Ltd",
        "normalisedname" : "SUNRISE CARE LTD",
        "source" : "CH",
        "id_in_source" : "04378206",})
    cqc_row = make_cqc_row(companyid='04378206')

    ch_file = write_input_data_to_tmp_file([ch_row],[],SUB_SPINE_CSV_FIELDS)
    cqc_file = write_input_data_to_tmp_file([cqc_row],[],SUB_SPINE_CSV_FIELDS+['charitynumber'])

    main_orgs = build_spine_for_test([ch_file,cqc_file])

    ch_org = main_orgs._store['GB-COH-04378206']
    assert [(m.uid,mt) for m,mt in ch_org.matched_orgs] == [('GB-CQC-1-101601999','companyid - cqc')]
    # the CQC record was merged, not added as its own organisation
    assert 'GB-CQC-1-101601999' not in main_orgs._store

    main_csv, match_csv = write_spine_and_read(main_orgs)
    assert 'GB-CQC' not in main_csv          # CQC records are match-only, never spine rows
    match_rows = [r for r in csv.DictReader(match_csv.splitlines())]
    assert any(r['match_type'] == 'companyid - cqc' and r['uid'] == 'GB-COH-04378206'
               and r['orgB_uid'] == 'GB-CQC-1-101601999' for r in match_rows)


def test_cqc_companyid_match_when_company_absorbed_into_charity():
    # the production build order ingests ccew before CH, so a company matching a charity
    # (via 'companyid - id_in_source') is absorbed into the charity and GB-COH-<number>
    # is no longer a spine entry of its own. A CQC provider carrying that company number
    # must still link - to the charity that absorbed the company.
    ccew_row = sub_spine_entry_creator({
        "uid" : "GB-CHC-5001",
        "organisationname" : "Helping Hands",
        "normalisedname" : "HELPING HANDS",
        "companyid" : "05001000",
        "source" : "ccew",
        "id_in_source" : "5001",})
    ch_row = sub_spine_entry_creator({
        "uid" : "GB-COH-05001000",
        "organisationname" : "Helping Hands Ltd",
        "normalisedname" : "HELPING HANDS LTD",
        "source" : "CH",
        "id_in_source" : "05001000",})
    cqc_row = make_cqc_row(companyid='05001000')

    ccew_file = write_input_data_to_tmp_file([ccew_row],[],SUB_SPINE_CSV_FIELDS)
    ch_file = write_input_data_to_tmp_file([ch_row],[],SUB_SPINE_CSV_FIELDS)
    cqc_file = write_input_data_to_tmp_file([cqc_row],[],SUB_SPINE_CSV_FIELDS+['charitynumber'])

    main_orgs = build_spine_for_test([ccew_file,ch_file,cqc_file])

    # the company was absorbed into the charity first
    assert 'GB-COH-05001000' not in main_orgs._store
    ccew_org = main_orgs._store['GB-CHC-5001']
    assert ('GB-COH-05001000','companyid - id_in_source') in [(m.uid,mt) for m,mt in ccew_org.matched_orgs]
    # and the CQC provider then linked to the charity through the company number
    assert ('GB-CQC-1-101601999','companyid - cqc') in [(m.uid,mt) for m,mt in ccew_org.matched_orgs]
    assert 'GB-CQC-1-101601999' not in main_orgs._store

    main_csv, match_csv = write_spine_and_read(main_orgs)
    assert 'GB-CQC' not in main_csv
    match_rows = [r for r in csv.DictReader(match_csv.splitlines())]
    assert any(r['match_type'] == 'companyid - cqc' and r['uid'] == 'GB-CHC-5001'
               and r['orgB_uid'] == 'GB-CQC-1-101601999' for r in match_rows)


def test_cqc_charityno_match():
    # a CQC provider carrying a charity number links to the CCEW charity via the
    # 'charityno - cqc' rule, even though the names differ
    ccew_row = sub_spine_entry_creator({
        "uid" : "GB-CHC-1103190",
        "organisationname" : "The Sunshine Charity",
        "normalisedname" : "THE SUNSHINE CHARITY",
        "source" : "ccew",
        "id_in_source" : "1103190",})
    cqc_row = make_cqc_row(charitynumber='1103190')

    ccew_file = write_input_data_to_tmp_file([ccew_row],[],SUB_SPINE_CSV_FIELDS)
    cqc_file = write_input_data_to_tmp_file([cqc_row],[],SUB_SPINE_CSV_FIELDS+['charitynumber'])

    main_orgs = build_spine_for_test([ccew_file,cqc_file])

    ccew_org = main_orgs._store['GB-CHC-1103190']
    assert [(m.uid,mt) for m,mt in ccew_org.matched_orgs] == [('GB-CQC-1-101601999','charityno - cqc')]
    assert 'GB-CQC-1-101601999' not in main_orgs._store

    main_csv, match_csv = write_spine_and_read(main_orgs)
    assert 'GB-CQC' not in main_csv
    match_rows = [r for r in csv.DictReader(match_csv.splitlines())]
    assert any(r['match_type'] == 'charityno - cqc' and r['uid'] == 'GB-CHC-1103190'
               and r['orgB_uid'] == 'GB-CQC-1-101601999' for r in match_rows)


def test_cqc_name_only_still_uses_name_rule():
    # a CQC provider with neither number falls back to the name rules as before
    ccew_row = sub_spine_entry_creator({
        "uid" : "GB-CHC-3001",
        "organisationname" : "Rose Cottage Care",
        "normalisedname" : "ROSE COTTAGE CARE",
        "source" : "ccew",
        "id_in_source" : "3001",})
    ccew_row['cqc_reg'] = '1'
    cqc_row = make_cqc_row(
        organisationname="Rose Cottage Care",
        normalisedname="ROSE COTTAGE CARE")

    ccew_file = write_input_data_to_tmp_file([ccew_row],[],SUB_SPINE_CSV_FIELDS+['cqc_reg'])
    cqc_file = write_input_data_to_tmp_file([cqc_row],[],SUB_SPINE_CSV_FIELDS+['charitynumber'])

    main_orgs = build_spine_for_test([ccew_file,cqc_file])

    ccew_org = main_orgs._store['GB-CHC-3001']
    matched = [(m.uid,mt) for m,mt in ccew_org.matched_orgs]
    assert ('GB-CQC-1-101601999','name - cqc') in matched
    assert 'GB-CQC-1-101601999' not in main_orgs._store


def test_cqc_same_name_best_candidate_and_never_a_spine_row():
    # a name-only CQC provider whose name is shared by TWO charities follows the standard
    # same-name behaviour: merged into exactly one (the best match), with the runner-up
    # keeping an association-only match row (blank uid). And no CQC record ever becomes a
    # public spine row - whether matched or wholly unmatched.
    ccew_rows = []
    for i in ('4001','4002'):
        r = sub_spine_entry_creator({
            "uid" : f"GB-CHC-{i}",
            "organisationname" : "United Charities",
            "normalisedname" : "UNITED CHARITIES",
            "source" : "ccew",
            "id_in_source" : i,})
        r['cqc_reg'] = '1'
        ccew_rows.append(r)
    cqc_same_name = make_cqc_row(
        organisationname="United Charities",
        normalisedname="UNITED CHARITIES")
    cqc_unmatched = make_cqc_row(
        uid="GB-CQC-1-999",
        id_in_source="1-999",
        organisationname="Wholly Unmatched Care",
        normalisedname="WHOLLY UNMATCHED CARE",
        companyid='09999999')  # a company number matching nothing in the spine

    ccew_file = write_input_data_to_tmp_file(ccew_rows,[],SUB_SPINE_CSV_FIELDS+['cqc_reg'])
    cqc_file = write_input_data_to_tmp_file([cqc_same_name,cqc_unmatched],[],SUB_SPINE_CSV_FIELDS+['charitynumber'])

    main_orgs = build_spine_for_test([ccew_file,cqc_file])

    # merged into exactly one organisation, and it is a CCEW charity
    absorbed_into = [org for org in main_orgs._store.values()
                     if any(m.uid == 'GB-CQC-1-101601999' for m,mt in org.matched_orgs)]
    assert len(absorbed_into) == 1
    assert absorbed_into[0].source.lower() == 'ccew'
    # the CQC record does not become its own store entry via a name match
    assert 'GB-CQC-1-101601999' not in main_orgs._store
    # the runner-up charity keeps an association-only match row (blank uid)
    runner_up = [org for org in main_orgs._store.values()
                 if org.source.lower() == 'ccew' and org.uid != absorbed_into[0].uid]
    assert len(runner_up) == 1
    assert any(r.orgB_uid == 'GB-CQC-1-101601999' and r.uid == '' and r.match_type == 'name - cqc'
               for r in runner_up[0].sorted_matches)

    main_csv, match_csv = write_spine_and_read(main_orgs)
    # the match-only invariant: no CQC record in the public spine, ever - the matched
    # provider was absorbed, and the wholly unmatched provider is excluded at write-out
    assert 'GB-CQC' not in main_csv
    assert 'carequalitycommission' not in main_csv.lower()
    # the name link is recorded in the matches file
    assert 'name - cqc' in match_csv


    
	
	
	
	
	
	