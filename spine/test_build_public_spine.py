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
        # A final organisation is active while either consolidated regulator
        # record is active, irrespective of which register supplies its UID.
        "removeddate" : "",}),
    ]


    expected_extra_rows = []#extra_csv_entry_creator({})]

    expected_main_csv,expected_extra_csv,b = write_expected_data_to_tmp_file(expected_main_rows,expected_extra_rows,[])

    with open(expected_main_csv) as csv_file:
        expected_main_csv = csv_file.read()

    assert_files_basically_same(main_csv, expected_main_csv)

        



def test_empty_extras():
    e = ExtraInfo(uid='1')
    assert e.isempty() == True


def test_current_status_ignores_historical_supplementary_removal():
    row = sub_spine_entry_creator({
        "uid": "GB-COH-00000001",
        "organisationname": "Restored Company",
        "normalisedname": "RESTORED COMPANY",
        "source": "CH",
        "source_register": "Companies House",
        "id_in_source": "00000001",
        "removeddate": "",
    })
    org = SubSpineOrg(
        **row,
        extras=[
            ExtraInfo(
                uid=row["uid"],
                source=row["source"],
                source_register=row["source_register"],
                removeddate="07/03/2023",
            )
        ],
    )

    assert org.removed() is False


def test_active_matched_org_with_removal_history_blanks_parent_removal():
    parent_row = sub_spine_entry_creator({
        "uid": "GB-COH-00000001",
        "organisationname": "Parent Company",
        "normalisedname": "PARENT COMPANY",
        "source": "CH",
        "source_register": "Companies House",
        "id_in_source": "00000001",
        "removeddate": "07/03/2023",
    })
    active_row = sub_spine_entry_creator({
        "uid": "GB-SC-SC000001",
        "organisationname": "Active Partner",
        "normalisedname": "ACTIVE PARTNER",
        "source": "OSCR",
        "source_register": "Scottish Charity Register",
        "id_in_source": "SC000001",
        "removeddate": "",
    })
    active_partner = SubSpineOrg(
        **active_row,
        extras=[
            ExtraInfo(
                uid=active_row["uid"],
                source=active_row["source"],
                source_register=active_row["source_register"],
                removeddate="01/02/2020",
            )
        ],
    )
    parent = CoreOrganisation(**parent_row)
    parent.matched_orgs = [(active_partner, "ftc")]

    parent.sort_extras()

    assert parent.removeddate == ""
    assert any(
        extra.uid == parent.uid and extra.removeddate == "07/03/2023"
        for extra in parent.extras
    )


def test_ccew_status_is_authoritative_for_cio_shadow_record():
    ccew_row = sub_spine_entry_creator({
        "uid": "GB-CHC-1001",
        "organisationname": "Removed CIO",
        "normalisedname": "REMOVED CIO",
        "source": "ccew",
        "source_register": "Charity Commission for England and Wales",
        "id_in_source": "1001-0",
        "removeddate": "07/03/2023",
    })
    cio_row = sub_spine_entry_creator({
        "uid": "GB-COH-CE000001",
        "organisationname": "Removed CIO",
        "normalisedname": "REMOVED CIO",
        "source": "CH",
        "source_register": "Companies House",
        "id_in_source": "CE000001",
        "removeddate": "",
    })
    parent = CoreOrganisation(**ccew_row)
    parent.matched_orgs = [
        (SubSpineOrg(**cio_row), "companyid - id_in_source")
    ]

    parent.sort_extras()

    assert parent.removeddate == "07/03/2023"


def _society_parent(removeddate):
    return CoreOrganisation(**sub_spine_entry_creator({
        "uid": "GB-MPR-17815R",
        "organisationname": "Grasmere Club Limited",
        "normalisedname": "GRASMERE CLUB LIMITED",
        "source": "mutuals",
        "source_register": "Mutuals Public Register",
        "id_in_source": "17815R",
        "removeddate": removeddate,
    }))


def _live_link(uid, source, source_register, id_in_source):
    return SubSpineOrg(**sub_spine_entry_creator({
        "uid": uid,
        "organisationname": "Grasmere Club Limited",
        "normalisedname": "GRASMERE CLUB LIMITED",
        "source": source,
        "source_register": source_register,
        "id_in_source": id_in_source,
        "removeddate": "",
    }))


def test_fca_deregistration_is_authoritative_for_a_society():
    # live society-number Companies House mirror, Co-operatives UK and housing
    # records do not keep an FCA-deregistered society open
    parent = _society_parent("19/08/2024")
    parent.matched_orgs = [
        (_live_link("GB-COH-IP17815R", "CH", "Companies House", "IP17815R"), "ftc"),
        (_live_link("GB-COOP-R010095", "CoOps", "Co-operatives", "R010095"),
         "companyid - coop mutual"),
        (_live_link("GB-SHPE-L0001", "socialhousingengland", "Social Housing England",
                    "L0001"), "name - housing"),
    ]

    parent.sort_extras()

    assert parent.removeddate == "19/08/2024"


@pytest.mark.parametrize("number", ["RS007840", "SP2696RS", "NP000256", "NO000004"])
def test_every_society_number_prefix_is_a_mirror(number):
    parent = _society_parent("05/09/2022")
    parent.matched_orgs = [
        (_live_link("GB-COH-" + number, "CH", "Companies House", number), "ftc"),
    ]

    parent.sort_extras()

    assert parent.removeddate == "05/09/2022"


def test_society_converted_to_a_live_company_stays_open():
    parent = _society_parent("19/08/2024")
    parent.matched_orgs = [
        (_live_link("GB-COH-05123456", "CH", "Companies House", "05123456"), "ftc"),
    ]

    parent.sort_extras()

    assert parent.removeddate == ""
    assert any(extra.removeddate == "19/08/2024" for extra in parent.extras)


def test_society_rule_does_not_touch_a_live_society_or_other_leads():
    live_society = _society_parent("")
    live_society.matched_orgs = [
        (_live_link("GB-COH-IP17815R", "CH", "Companies House", "IP17815R"), "ftc"),
    ]
    live_society.sort_extras()
    assert live_society.removeddate == ""

    # a removed charity lead is still held open by a live society-number record:
    # the exception belongs to FCA-led organisations only
    charity = CoreOrganisation(**sub_spine_entry_creator({
        "uid": "GB-CHC-1001",
        "organisationname": "Removed Charity",
        "normalisedname": "REMOVED CHARITY",
        "source": "ccew",
        "source_register": "Charity Commission for England and Wales",
        "id_in_source": "1001-0",
        "removeddate": "07/03/2023",
    }))
    charity.matched_orgs = [
        (_live_link("GB-COH-IP17815R", "CH", "Companies House", "IP17815R"),
         "companyid - id_in_source"),
    ]
    charity.sort_extras()
    assert charity.removeddate == ""


def test_absorbed_uid_is_not_rematerialised_by_another_association():
    def core(uid):
        return CoreOrganisation(**sub_spine_entry_creator({
            "uid": uid,
            "organisationname": uid,
            "normalisedname": uid,
            "source": "ccew",
            "source_register": "Charity Commission for England and Wales",
            "id_in_source": uid.removeprefix("GB-CHC-") + "-0",
        }))

    child_row = sub_spine_entry_creator({
        "uid": "GB-CHC-3",
        "organisationname": "Child",
        "normalisedname": "CHILD",
        "source": "ccew",
        "source_register": "Charity Commission for England and Wales",
        "id_in_source": "3-0",
    })
    child = SubSpineOrg(**child_row)
    association_parent = core("GB-CHC-1")
    absorbing_parent = core("GB-CHC-2")
    association_parent.matched_orgs = [
        (child, "companyid - companyid")
    ]
    absorbing_parent.matched_orgs = [(child, "ftc")]
    organisations = MainOrgList()
    organisations.add_to_stores(association_parent)
    organisations.add_to_stores(absorbing_parent)

    organisations.sort_matches()

    assert "GB-CHC-3" not in organisations._store


def test_same_source_status_conflict_stops_the_build(monkeypatch):
    removed_row = sub_spine_entry_creator({
        "uid": "GB-CHC-1",
        "organisationname": "Earlier Removed Charity",
        "normalisedname": "EARLIER REMOVED CHARITY",
        "source": "ccew",
        "source_register": "Charity Commission for England and Wales",
        "id_in_source": "1-0",
        "removeddate": "01/01/2020",
    })
    active_row = sub_spine_entry_creator({
        "uid": "GB-CHC-2",
        "organisationname": "Current Active Charity",
        "normalisedname": "CURRENT ACTIVE CHARITY",
        "source": "ccew",
        "source_register": "Charity Commission for England and Wales",
        "id_in_source": "2-0",
        "removeddate": "",
    })
    removed = CoreOrganisation(**removed_row)
    incoming = SubSpineOrg(**active_row)
    organisations = MainOrgList()
    organisations.add_to_stores(removed)

    monkeypatch.setattr(
        SubSpineOrg,
        "matches",
        lambda self, *_args, **_kwargs: [(removed, "ftc")],
    )

    with pytest.raises(RuntimeError, match="has no removal date"):
        organisations.merge([incoming])


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
    assert absorbed_into[0].uid == 'GB-CHC-2001'
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


def test_ftc_equal_rule_tie_uses_uid_not_set_order(tmp_path):
    base_rows = [
        sub_spine_entry_creator({
            "uid": "GB-CHC-100",
            "organisationname": "Candidate 100",
            "normalisedname": "CANDIDATE 100",
            "source": "ccew",
            "id_in_source": "100",
        }),
        sub_spine_entry_creator({
            "uid": "GB-CHC-200",
            "organisationname": "Candidate 200",
            "normalisedname": "CANDIDATE 200",
            "source": "ccew",
            "id_in_source": "200",
        }),
    ]
    incoming = sub_spine_entry_creator({
        "uid": "GB-COH-900",
        "organisationname": "Incoming Company",
        "normalisedname": "INCOMING COMPANY",
        "source": "CH",
        "id_in_source": "900",
    })
    base_file = write_input_data_to_tmp_file(
        base_rows, [], SUB_SPINE_CSV_FIELDS
    )
    incoming_file = write_input_data_to_tmp_file(
        [incoming], [], SUB_SPINE_CSV_FIELDS
    )
    oscr_links = write_csv(
        str(tmp_path / "oscr-links.csv"),
        [],
        ["org_id_a", "org_id_b", "source"],
    )

    edges = [
        {
            "org_id_a": "GB-COH-900",
            "org_id_b": "GB-CHC-200",
            "source": "manual",
        },
        {
            "org_id_a": "GB-COH-900",
            "org_id_b": "GB-CHC-100",
            "source": "manual",
        },
    ]

    winners = []
    for index, edge_order in enumerate((edges, list(reversed(edges)))):
        sameas = write_csv(
            str(tmp_path / f"sameas-{index}.csv"),
            edge_order,
            ["org_id_a", "org_id_b", "source"],
        )
        main_orgs = process_csvs_to_build_spine(
            [base_file, incoming_file],
            sameas_file=sameas,
            oscr_links_file=oscr_links,
        )
        absorbed_into = [
            org.uid for org in main_orgs._store.values()
            if any(m.uid == "GB-COH-900" for m, _ in org.matched_orgs)
        ]
        assert absorbed_into == ["GB-CHC-100"]
        winners.append(absorbed_into[0])

    assert winners == ["GB-CHC-100", "GB-CHC-100"]


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
    assert absorbed_into[0].uid == 'GB-CHC-4001'
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


# ---------------------------------------------------------------------------
# Association-only (companyid - companyid) handling: regression tests for the
# RNIB/UCLH wrong cross-border match
# (docs/spine-docs/rnib-wrong-match-investigation-2026-07-19.md).
# ---------------------------------------------------------------------------

def ccew_assoc_entry(uid, name, companyid):
    return sub_spine_entry_creator({
        "uid": uid,
        "organisationname": name,
        "normalisedname": name,
        "source": "ccew",
        "source_register": "Charity Commission for England and Wales",
        "id_in_source": uid.removeprefix("GB-CHC-") + "-0",
        "companyid": companyid,
    })


def test_association_only_endpoint_stays_matchable_by_name():
    # Miniature RNIB/UCLH scenario. Two unrelated CCEW charities share a
    # company number, which creates an association-only link. The second
    # charity must remain a matchable organisation in its own right, so that
    # a later cross-border OSCR record with its exact name absorbs into it
    # and not into the association partner.
    ccew_file = write_input_data_to_tmp_file(
        [ccew_assoc_entry("GB-CHC-1", "UCLH CHARITY", "55555555"),
         ccew_assoc_entry("GB-CHC-2", "RNIB CHARITY", "55555555")],
        [], SUB_SPINE_CSV_FIELDS)
    oscr_row = sub_spine_entry_creator({
        "uid": "GB-SC-SC1",
        "organisationname": "RNIB Charity",
        "normalisedname": "RNIB CHARITY",
        "source": "oscr",
        "source_register": "Scottish Charity Register",
        "id_in_source": "SC1",
    })
    oscr_row["crossborder"] = "1"
    oscr_file = write_input_data_to_tmp_file(
        [oscr_row], [], SUB_SPINE_CSV_FIELDS + ["crossborder"])

    m = build_spine_for_test([ccew_file, oscr_file])

    # the association endpoint is a standalone organisation during the build
    assert "GB-CHC-2" in m._store
    twin = m._store["GB-CHC-2"]
    assert any(x.uid == "GB-SC-SC1" and mt == "name - crossborder"
               for x, mt in twin.matched_orgs)
    stranger = m._store["GB-CHC-1"]
    assert not any(x.uid == "GB-SC-SC1" for x, _ in stranger.matched_orgs)

    # write-out must keep the twin's absorption: the association partner's
    # re-materialisation pass must not clobber the standalone store entry
    m.sort_matches()
    assert "GB-SC-SC1" not in m._store
    assert any(x.uid == "GB-SC-SC1"
               for x, _ in m._store["GB-CHC-2"].matched_orgs)


def test_parent_not_indexed_under_association_partner_keys():
    # An organisation must not be findable under the names/ids of its
    # association-only partners; it must remain findable under the keys of
    # records it genuinely absorbed (mergers depend on that).
    parent = CoreOrganisation(**ccew_assoc_entry("GB-CHC-1", "PARENT", "11110001"))
    assoc = SubSpineOrg(**ccew_assoc_entry("GB-CHC-2", "ASSOC PARTNER", "22220002"))
    absorbed = SubSpineOrg(**ccew_assoc_entry("GB-CHC-3", "ABSORBED TWIN", "33330003"))
    parent.matched_orgs = [(assoc, "companyid - companyid"), (absorbed, "ftc")]
    m = MainOrgList()

    m.add_to_stores(parent)

    assert "ASSOC PARTNER" not in m.byname
    assert "22220002" not in m.bycompanyid
    assert "2-0" not in m.bysourceid
    assert [o.uid for o in m.byname["ABSORBED TWIN"]] == ["GB-CHC-1"]
    assert [o.uid for o in m.bycompanyid["33330003"]] == ["GB-CHC-1"]


def test_placeholder_companyid_shared_by_four_is_suppressed():
    # A company number held by four or more distinct organisations of the
    # same source is register junk (e.g. CCEW's literal 12345678) and must
    # not produce companyid - companyid links at all.
    rows = [ccew_assoc_entry(f"GB-CHC-{i}", f"CHARITY NUMBER {i}", "12345678")
            for i in range(1, 5)]
    f = write_input_data_to_tmp_file(rows, [], SUB_SPINE_CSV_FIELDS)

    m = build_spine_for_test([f])

    assert len(m._store) == 4
    for org in m._store.values():
        assert org.matched_orgs == []


def test_small_companyid_clusters_still_link():
    # Two- and three-charity clusters are plausibly genuine re-registrations
    # of the same corporate body and must keep their association links.
    pair = [ccew_assoc_entry("GB-CHC-1", "OLD REGISTRATION", "07770001"),
            ccew_assoc_entry("GB-CHC-2", "NEW REGISTRATION", "07770001")]
    f = write_input_data_to_tmp_file(pair, [], SUB_SPINE_CSV_FIELDS)
    m = build_spine_for_test([f])
    assert any(x.uid == "GB-CHC-2" and mt == "companyid - companyid"
               for x, mt in m._store["GB-CHC-1"].matched_orgs)

    trio = [ccew_assoc_entry(f"GB-CHC-{i}", f"REREG {i}", "07770002")
            for i in (1, 2, 3)]
    f = write_input_data_to_tmp_file(trio, [], SUB_SPINE_CSV_FIELDS)
    m = build_spine_for_test([f])
    assert any(mt == "companyid - companyid"
               for _, mt in m._store["GB-CHC-1"].matched_orgs)


def test_socialhousingengland_matches_mutual_by_name():
    # Registered-society housing providers (e.g. co-operatives) appear on the FCA Mutuals
    # Public Register, not the charity register, and the RSH register carries no company
    # number to join on. The 'name - housing' rule must therefore treat a same-name mutual
    # as an eligible counterpart. Real-world case: "Stirchley Co-operative Development
    # Limited" is both GB-MPR-4496 (mutuals) and GB-SHPE-5234 (socialhousingengland).
    # mutuals is loaded before the housing registers in the real build, so order the files
    # the same way here.
    mutual_row = sub_spine_entry_creator({
        "uid" : "GB-MPR-4496",
        "organisationname" : "Stirchley Co-operative Development Limited",
        "normalisedname" : "STIRCHLEY CO OPERATIVE DEVELOPMENT LIMITED",
        "source" : "mutuals",
        "id_in_source" : "4496",})
    # an unrelated mutual with a different name must NOT be pulled in
    other_mutual_row = sub_spine_entry_creator({
        "uid" : "GB-MPR-9999",
        "organisationname" : "Somewhere Else Society Limited",
        "normalisedname" : "SOMEWHERE ELSE SOCIETY LIMITED",
        "source" : "mutuals",
        "id_in_source" : "9999",})
    she_row = sub_spine_entry_creator({
        "uid" : "GB-SHPE-5234",
        "organisationname" : "Stirchley Co-operative Development Limited",
        "normalisedname" : "STIRCHLEY CO OPERATIVE DEVELOPMENT LIMITED",
        "source" : "socialhousingengland",
        "id_in_source" : "5234",})

    mutuals_file = write_input_data_to_tmp_file([mutual_row, other_mutual_row], [], SUB_SPINE_CSV_FIELDS)
    she_file = write_input_data_to_tmp_file([she_row], [], SUB_SPINE_CSV_FIELDS)

    main_orgs = build_spine_for_test([mutuals_file, she_file])

    # the housing record is absorbed into exactly one organisation: the same-name mutual,
    # via the 'name - housing' rule
    absorbed_into = [org for org in main_orgs._store.values()
                     if any(m.uid == 'GB-SHPE-5234' for m, mt in org.matched_orgs)]
    assert len(absorbed_into) == 1
    assert absorbed_into[0].uid == 'GB-MPR-4496'
    assert any(m.uid == 'GB-SHPE-5234' and mt == 'name - housing'
               for m, mt in absorbed_into[0].matched_orgs)
    # it did not become its own standalone spine organisation
    assert 'GB-SHPE-5234' not in main_orgs._store
    # the unrelated mutual is untouched
    assert main_orgs._store['GB-MPR-9999'].matched_orgs == []


def test_scottishhousingregulator_matches_mutual_by_name():
    # Same rule, Scottish side: a Scottish Housing Regulator provider that is a registered
    # society must match its same-name Mutuals Public Register record via 'name - housing'.
    mutual_row = sub_spine_entry_creator({
        "uid" : "GB-MPR-2302RS",
        "organisationname" : "Yorkhill Housing Association Ltd",
        "normalisedname" : "YORKHILL HOUSING ASSOCIATION LTD",
        "source" : "mutuals",
        "id_in_source" : "2302RS",})
    shr_row = sub_spine_entry_creator({
        "uid" : "GB-SHR-209",
        "organisationname" : "Yorkhill Housing Association Ltd",
        "normalisedname" : "YORKHILL HOUSING ASSOCIATION LTD",
        "source" : "scottishhousingregulator",
        "id_in_source" : "209",})

    mutuals_file = write_input_data_to_tmp_file([mutual_row], [], SUB_SPINE_CSV_FIELDS)
    shr_file = write_input_data_to_tmp_file([shr_row], [], SUB_SPINE_CSV_FIELDS)

    main_orgs = build_spine_for_test([mutuals_file, shr_file])

    absorbed_into = [org for org in main_orgs._store.values()
                     if any(m.uid == 'GB-SHR-209' for m, mt in org.matched_orgs)]
    assert len(absorbed_into) == 1
    assert absorbed_into[0].uid == 'GB-MPR-2302RS'
    assert any(m.uid == 'GB-SHR-209' and mt == 'name - housing'
               for m, mt in absorbed_into[0].matched_orgs)
    assert 'GB-SHR-209' not in main_orgs._store


    
	
	
	
	
	
	



# ---------------------------------------------------------------------------
# 'name - ni charity': a Northern Irish company and its CCNI charity registration
# ---------------------------------------------------------------------------

def _ccni_charity(uid, name, normalised, **overrides):
    row = {
        "uid" : uid,
        "organisationname" : name,
        "normalisedname" : normalised,
        "source" : "ccni",
        "source_register" : "Charity Commission for Northern Ireland",
        "id_in_source" : uid.rsplit('-', 1)[-1],}
    row.update(overrides)
    return sub_spine_entry_creator(row)


def _ni_company(uid, name, normalised, **overrides):
    row = {
        "uid" : uid,
        "organisationname" : name,
        "normalisedname" : normalised,
        "source" : "ch",
        "source_register" : "Companies House",
        "id_in_source" : uid.removeprefix('GB-COH-'),}
    row.update(overrides)
    return sub_spine_entry_creator(row)


def test_ni_company_matches_ccni_charity_by_name():
    # CCNI publishes a company number for only part of its register, so for most
    # Northern Irish charitable companies a shared normalised name is the only
    # evidence available. Real-world case: GB-COH-NI652013 / GB-NIC-107323.
    # CCNI is loaded before Companies House in the real build; order the files the
    # same way here.
    charity = _ccni_charity('GB-NIC-107323', 'Oak Counselling Services Ltd',
                            'OAK COUNSELLING SERVICES LTD',
                            registerdate='10/02/2020', removeddate='29/01/2024')
    company = _ni_company('GB-COH-NI652013', 'Oak Counselling Services Ltd',
                          'OAK COUNSELLING SERVICES LTD',
                          registerdate='10/02/2020')
    other_charity = _ccni_charity('GB-NIC-100001', 'Somewhere Else Trust',
                                  'SOMEWHERE ELSE TRUST')

    ccni_file = write_input_data_to_tmp_file([charity, other_charity], [], SUB_SPINE_CSV_FIELDS)
    ch_file = write_input_data_to_tmp_file([company], [], SUB_SPINE_CSV_FIELDS)

    main_orgs = build_spine_for_test([ccni_file, ch_file])

    absorbed_into = [org for org in main_orgs._store.values()
                     if any(m.uid == 'GB-COH-NI652013' for m, mt in org.matched_orgs)]
    assert len(absorbed_into) == 1
    # the charity survives as the spine organisation, the company is the matched record
    assert absorbed_into[0].uid == 'GB-NIC-107323'
    assert any(m.uid == 'GB-COH-NI652013' and mt == 'name - ni charity'
               for m, mt in absorbed_into[0].matched_orgs)
    assert 'GB-COH-NI652013' not in main_orgs._store
    assert main_orgs._store['GB-NIC-100001'].matched_orgs == []

    # the match row records the charity as orgA and the company as orgB
    main_orgs.sort_matches()
    match_rows = main_orgs._store['GB-NIC-107323'].to_match_csv()
    ni_rows = [r for r in match_rows if r['match_type'] == 'name - ni charity']
    assert len(ni_rows) == 1
    assert ni_rows[0]['uid'] == 'GB-NIC-107323'
    assert ni_rows[0]['orgA_uid'] == 'GB-NIC-107323'
    assert ni_rows[0]['orgB_uid'] == 'GB-COH-NI652013'


def test_ni_rule_leaves_a_removed_charity_active_when_its_company_is_live():
    # A charity removed from the CCNI register whose company is still on the
    # Companies House register is an active organisation: consolidation moves the
    # charity removal date into supplementary history and blanks it on the spine
    # row. This is what keeps the population source-alignment gate satisfied when an
    # active Companies House record is absorbed into a removed charity.
    charity = _ccni_charity('GB-NIC-107323', 'Oak Counselling Services Ltd',
                            'OAK COUNSELLING SERVICES LTD',
                            registerdate='10/02/2020', removeddate='29/01/2024')
    company = _ni_company('GB-COH-NI652013', 'Oak Counselling Services Ltd',
                          'OAK COUNSELLING SERVICES LTD',
                          registerdate='10/02/2020')

    ccni_file = write_input_data_to_tmp_file([charity], [], SUB_SPINE_CSV_FIELDS)
    ch_file = write_input_data_to_tmp_file([company], [], SUB_SPINE_CSV_FIELDS)

    main_orgs = build_spine_for_test([ccni_file, ch_file])
    main_orgs.sort_extras()

    parent = main_orgs._store['GB-NIC-107323']
    assert parent.removeddate == ''
    assert any(x.removeddate == '29/01/2024' for x in parent.extras)


def test_non_ni_company_does_not_match_ccni_charity_by_name():
    charity = _ccni_charity('GB-NIC-107323', 'Oak Counselling Services Ltd',
                            'OAK COUNSELLING SERVICES LTD')
    company = _ni_company('GB-COH-07654321', 'Oak Counselling Services Ltd',
                          'OAK COUNSELLING SERVICES LTD')

    ccni_file = write_input_data_to_tmp_file([charity], [], SUB_SPINE_CSV_FIELDS)
    ch_file = write_input_data_to_tmp_file([company], [], SUB_SPINE_CSV_FIELDS)

    main_orgs = build_spine_for_test([ccni_file, ch_file])

    assert main_orgs._store['GB-NIC-107323'].matched_orgs == []
    assert 'GB-COH-07654321' in main_orgs._store


def test_two_ccni_charities_with_the_same_name_block_the_ni_rule():
    # The name no longer identifies one charity, so there is no safe counterpart.
    charity_a = _ccni_charity('GB-NIC-107323', 'Oak Counselling Services Ltd',
                              'OAK COUNSELLING SERVICES LTD')
    charity_b = _ccni_charity('GB-NIC-107324', 'Oak Counselling Services Ltd',
                              'OAK COUNSELLING SERVICES LTD')
    company = _ni_company('GB-COH-NI652013', 'Oak Counselling Services Ltd',
                          'OAK COUNSELLING SERVICES LTD')

    ccni_file = write_input_data_to_tmp_file([charity_a, charity_b], [], SUB_SPINE_CSV_FIELDS)
    ch_file = write_input_data_to_tmp_file([company], [], SUB_SPINE_CSV_FIELDS)

    main_orgs = build_spine_for_test([ccni_file, ch_file])

    assert main_orgs._store['GB-NIC-107323'].matched_orgs == []
    assert main_orgs._store['GB-NIC-107324'].matched_orgs == []
    assert 'GB-COH-NI652013' in main_orgs._store


def test_two_ni_companies_with_the_same_name_block_the_ni_rule():
    # Incomer-side half of the one-to-one guard: two NI companies share the name,
    # so neither can be assigned to the single charity that holds it.
    charity = _ccni_charity('GB-NIC-107323', 'Oak Counselling Services Ltd',
                            'OAK COUNSELLING SERVICES LTD')
    company_a = _ni_company('GB-COH-NI652013', 'Oak Counselling Services Ltd',
                            'OAK COUNSELLING SERVICES LTD')
    company_b = _ni_company('GB-COH-NI652014', 'Oak Counselling Services Ltd',
                            'OAK COUNSELLING SERVICES LTD')

    ccni_file = write_input_data_to_tmp_file([charity], [], SUB_SPINE_CSV_FIELDS)
    ch_file = write_input_data_to_tmp_file([company_a, company_b], [], SUB_SPINE_CSV_FIELDS)

    main_orgs = build_spine_for_test([ccni_file, ch_file])

    assert main_orgs._store['GB-NIC-107323'].matched_orgs == []
    assert 'GB-COH-NI652013' in main_orgs._store
    assert 'GB-COH-NI652014' in main_orgs._store


def test_ccew_charity_is_not_matched_by_the_ni_rule():
    # Only CCNI charities are eligible counterparts, whatever the name says.
    charity = sub_spine_entry_creator({
        "uid" : "GB-CHC-1234567",
        "organisationname" : "Oak Counselling Services Ltd",
        "normalisedname" : "OAK COUNSELLING SERVICES LTD",
        "source" : "ccew",
        "source_register" : "Charity Commission for England and Wales",
        "id_in_source" : "1234567",})
    company = _ni_company('GB-COH-NI652013', 'Oak Counselling Services Ltd',
                          'OAK COUNSELLING SERVICES LTD')

    ccew_file = write_input_data_to_tmp_file([charity], [], SUB_SPINE_CSV_FIELDS)
    ch_file = write_input_data_to_tmp_file([company], [], SUB_SPINE_CSV_FIELDS)

    main_orgs = build_spine_for_test([ccew_file, ch_file])

    assert main_orgs._store['GB-CHC-1234567'].matched_orgs == []
    assert 'GB-COH-NI652013' in main_orgs._store


def test_companyid_rule_outranks_the_ni_name_rule():
    # When CCNI does publish the company number both rules point at the same charity.
    # MATCHTYPE_ORDER must make the identifier rule the absorbing one, and the record
    # must be absorbed exactly once.
    assert (MATCHTYPE_RANK['companyid - id_in_source']
            < MATCHTYPE_RANK['name - ni charity'])

    charity = _ccni_charity('GB-NIC-107323', 'Oak Counselling Services Ltd',
                            'OAK COUNSELLING SERVICES LTD',
                            companyid='NI652013')
    company = _ni_company('GB-COH-NI652013', 'Oak Counselling Services Ltd',
                          'OAK COUNSELLING SERVICES LTD')

    ccni_file = write_input_data_to_tmp_file([charity], [], SUB_SPINE_CSV_FIELDS)
    ch_file = write_input_data_to_tmp_file([company], [], SUB_SPINE_CSV_FIELDS)

    main_orgs = build_spine_for_test([ccni_file, ch_file])

    absorbed_into = [org for org in main_orgs._store.values()
                     if any(m.uid == 'GB-COH-NI652013' for m, mt in org.matched_orgs)]
    assert len(absorbed_into) == 1
    assert absorbed_into[0].uid == 'GB-NIC-107323'
    assert 'GB-COH-NI652013' not in main_orgs._store

    main_orgs.sort_matches()
    rows = [r for r in main_orgs._store['GB-NIC-107323'].to_match_csv()
            if r['orgB_uid'] == 'GB-COH-NI652013']
    # The pair keeps one row per rule that found it - the established behaviour for
    # any pair two rules agree on - and the stronger identifier rule sorts first.
    # What matters is that there is a single absorption: every row names the same
    # parent and none is an association-only (blank uid) row.
    assert rows[0]['match_type'] == 'companyid - id_in_source'
    assert {r['match_type'] for r in rows} == {'companyid - id_in_source',
                                               'name - ni charity'}
    assert all(r['uid'] == 'GB-NIC-107323' for r in rows)



def test_ni_rule_counts_a_ccni_charity_already_absorbed_by_another_register(tmp_path):
    # A CCNI charity linked by the Find That Charity table to a CCEW charity is
    # absorbed into that CCEW parent, and the parent is then indexed under the
    # charity's name while keeping source 'ccew'. Counting only x.source would see
    # one visible CCNI holder of the name and fire the rule; the name in fact
    # belongs to two Northern Irish charities, so it must not fire.
    ccew_parent = sub_spine_entry_creator({
        "uid" : "GB-CHC-500",
        "organisationname" : "Different Ccew Name",
        "normalisedname" : "DIFFERENT CCEW NAME",
        "source" : "ccew",
        "source_register" : "Charity Commission for England and Wales",
        "id_in_source" : "500",})
    charity_a = _ccni_charity('GB-NIC-107323', 'Oak Counselling Services Ltd',
                              'OAK COUNSELLING SERVICES LTD')
    charity_b = _ccni_charity('GB-NIC-107324', 'Oak Counselling Services Ltd',
                              'OAK COUNSELLING SERVICES LTD')
    company = _ni_company('GB-COH-NI652013', 'Oak Counselling Services Ltd',
                          'OAK COUNSELLING SERVICES LTD')

    ccew_file = write_input_data_to_tmp_file([ccew_parent], [], SUB_SPINE_CSV_FIELDS)
    ccni_file = write_input_data_to_tmp_file([charity_a, charity_b], [], SUB_SPINE_CSV_FIELDS)
    ch_file = write_input_data_to_tmp_file([company], [], SUB_SPINE_CSV_FIELDS)

    sameas = write_csv(
        str(tmp_path / "sameas.csv"),
        [{"org_id_a": "GB-NIC-107324", "org_id_b": "GB-CHC-500", "source": "manual"}],
        ["org_id_a", "org_id_b", "source"],
    )
    oscr_links = write_csv(
        str(tmp_path / "oscr-links.csv"), [], ["org_id_a", "org_id_b", "source"],
    )

    main_orgs = process_csvs_to_build_spine(
        [ccew_file, ccni_file, ch_file],
        sameas_file=sameas,
        oscr_links_file=oscr_links,
    )

    # the fixture works: charity B really was absorbed into the CCEW parent
    assert 'GB-NIC-107324' not in main_orgs._store
    assert any(m.uid == 'GB-NIC-107324' and mt == 'ftc'
               for m, mt in main_orgs._store['GB-CHC-500'].matched_orgs)
    # and the NI company is left standalone: two charities hold the name
    assert 'GB-COH-NI652013' in main_orgs._store
    assert main_orgs._store['GB-NIC-107323'].matched_orgs == []
    assert not any(mt == 'name - ni charity'
                   for m, mt in main_orgs._store['GB-CHC-500'].matched_orgs)


def test_ni_rules_pointing_at_different_charities_absorb_only_once():
    # Charity A publishes the company number; charity B happens to share the
    # company's name. The identifier rule wins the absorption, and the name rule
    # leaves B an association-only row rather than a second absorption.
    charity_a = _ccni_charity('GB-NIC-107323', 'Alpha Charity',
                              'ALPHA CHARITY', companyid='NI652013')
    charity_b = _ccni_charity('GB-NIC-107324', 'Oak Counselling Services Ltd',
                              'OAK COUNSELLING SERVICES LTD')
    company = _ni_company('GB-COH-NI652013', 'Oak Counselling Services Ltd',
                          'OAK COUNSELLING SERVICES LTD')

    ccni_file = write_input_data_to_tmp_file([charity_a, charity_b], [], SUB_SPINE_CSV_FIELDS)
    ch_file = write_input_data_to_tmp_file([company], [], SUB_SPINE_CSV_FIELDS)

    main_orgs = build_spine_for_test([ccni_file, ch_file])

    absorbed_into = [org for org in main_orgs._store.values()
                     if any(m.uid == 'GB-COH-NI652013' for m, mt in org.matched_orgs)]
    assert len(absorbed_into) == 1
    assert absorbed_into[0].uid == 'GB-NIC-107323'
    assert 'GB-COH-NI652013' not in main_orgs._store
    # B is untouched as an organisation and keeps its own spine row
    assert main_orgs._store['GB-NIC-107324'].matched_orgs == []

    main_orgs.sort_matches()
    a_rows = [r for r in main_orgs._store['GB-NIC-107323'].to_match_csv()
              if r['orgB_uid'] == 'GB-COH-NI652013']
    assert len(a_rows) == 1
    assert a_rows[0]['uid'] == 'GB-NIC-107323'
    assert a_rows[0]['match_type'] == 'companyid - id_in_source'

    b_rows = list(main_orgs._store['GB-NIC-107324'].to_match_csv())
    assert len(b_rows) == 1
    assert b_rows[0]['uid'] == ''
    assert b_rows[0]['orgA_uid'] == 'GB-NIC-107324'
    assert b_rows[0]['orgB_uid'] == 'GB-COH-NI652013'
    assert b_rows[0]['match_type'] == 'name - ni charity'
# ---------------------------------------------------------------------------
# "Bridge merge": an incoming record that matches TWO spine organisations from
# different registers is treated as proof that those two are the same body, and
# they are folded into one (instead of one absorbing the record while the other
# keeps a blank-uid association row). Real case: Clyde Valley Housing
# Association is both OSCR GB-SC-SC037244 and Mutuals GB-MPR-2489RS, bridged by
# Scottish Housing Regulator record GB-SHR-291 via 'name - housing'.
# The rule is deliberately narrow: three-way fan-outs and same-register
# fan-outs (one Social Housing England "United Charities" record would otherwise
# fuse 53 distinct CCEW charities) must NOT merge.
# ---------------------------------------------------------------------------

def write_spine_and_read_all(main_orgs):
    with tempfile.TemporaryDirectory() as temp_dir:
        main_orgs.write_out(f"{temp_dir}/main.csv", f"{temp_dir}/extra.csv", f"{temp_dir}/match.csv")
        with open(f"{temp_dir}/main.csv") as f: main_csv = f.read()
        with open(f"{temp_dir}/extra.csv") as f: extra_csv = f.read()
        with open(f"{temp_dir}/match.csv") as f: match_csv = f.read()
    return main_csv, extra_csv, match_csv


def _rows(csv_text):
    return list(csv.DictReader(csv_text.splitlines()))


def test_bridge_merge_match_type_is_ranked_last():
    # 'merge via bridge' is not a candidate rule, so its rank must never compete with a
    # real rule: it sits last in MATCHTYPE_ORDER purely to keep match_info_sort_key total.
    assert MATCHTYPE_ORDER[-1] == BRIDGE_MERGE_MATCH_TYPE == 'merge via bridge'
    assert MATCHTYPE_RANK['companyid - companyid'] < MATCHTYPE_RANK[BRIDGE_MERGE_MATCH_TYPE]


def test_bridge_merge_clyde_valley_shape():
    # OSCR charity + Mutuals society with the same name, bridged by a Scottish Housing
    # Regulator record matching both by 'name - housing': one spine organisation results.
    oscr_row = sub_spine_entry_creator({
        "uid" : "GB-SC-SC037244",
        "organisationname" : "Clyde Valley Housing Association Limited",
        "normalisedname" : "CLYDE VALLEY HOUSING ASSOCIATION LIMITED",
        "source" : "OSCR",
        "source_register" : "Scottish Charity Register",
        "id_in_source" : "SC037244",})
    mutual_row = sub_spine_entry_creator({
        "uid" : "GB-MPR-2489RS",
        "organisationname" : "Clyde Valley Housing Association Limited",
        "normalisedname" : "CLYDE VALLEY HOUSING ASSOCIATION LIMITED",
        "source" : "mutuals",
        "source_register" : "Mutuals Public Register",
        "id_in_source" : "2489RS",})
    shr_row = sub_spine_entry_creator({
        "uid" : "GB-SHR-291",
        "organisationname" : "Clyde Valley Housing Association Limited",
        "normalisedname" : "CLYDE VALLEY HOUSING ASSOCIATION LIMITED",
        "source" : "scottishhousingregulator",
        "source_register" : "Scottish Housing Regulator",
        "id_in_source" : "291",})

    oscr_file = write_input_data_to_tmp_file([oscr_row],[],SUB_SPINE_CSV_FIELDS)
    mutuals_file = write_input_data_to_tmp_file([mutual_row],[],SUB_SPINE_CSV_FIELDS)
    shr_file = write_input_data_to_tmp_file([shr_row],[],SUB_SPINE_CSV_FIELDS)

    main_orgs = build_spine_for_test([oscr_file, mutuals_file, shr_file])

    # OSCR is loaded before mutuals, so the OSCR organisation survives
    assert sorted(main_orgs._store) == ['GB-SC-SC037244']
    assert set(main_orgs.merged_uid_aliases) == {'GB-MPR-2489RS'}

    survivor = main_orgs._store['GB-SC-SC037244']
    assert sorted((m.uid, mt) for m, mt in survivor.matched_orgs) == [
        ('GB-MPR-2489RS', 'merge via bridge'),
        ('GB-SHR-291', 'name - housing'),
    ]

    main_csv, _, match_csv = write_spine_and_read_all(main_orgs)
    assert [r['uid'] for r in _rows(main_csv)] == ['GB-SC-SC037244']
    match_rows = _rows(match_csv)
    assert {(r['uid'], r['orgA_uid'], r['orgB_uid'], r['match_type']) for r in match_rows} == {
        ('GB-SC-SC037244', 'GB-SC-SC037244', 'GB-MPR-2489RS', 'merge via bridge'),
        ('GB-SC-SC037244', 'GB-SC-SC037244', 'GB-SHR-291', 'name - housing'),
    }
    # nothing was written as an association-only (blank uid) link
    assert not [r for r in match_rows if r['uid'] == '']


def test_bridge_merge_blocked_by_same_register_fan_out():
    # Two CCEW charities that happen to share a name plus one Social Housing England
    # record: the two charities are NOT the same body, so the existing behaviour must
    # stand - one absorption plus one blank-uid association row.
    ccew_a = sub_spine_entry_creator({
        "uid" : "GB-CHC-2001",
        "organisationname" : "United Charities",
        "normalisedname" : "UNITED CHARITIES",
        "source" : "ccew",
        "id_in_source" : "2001",})
    ccew_b = sub_spine_entry_creator({
        "uid" : "GB-CHC-2002",
        "organisationname" : "United Charities",
        "normalisedname" : "UNITED CHARITIES",
        "source" : "ccew",
        "id_in_source" : "2002",})
    she_row = sub_spine_entry_creator({
        "uid" : "GB-SHPE-2003",
        "organisationname" : "United Charities",
        "normalisedname" : "UNITED CHARITIES",
        "source" : "socialhousingengland",
        "id_in_source" : "2003",})

    ccew_file = write_input_data_to_tmp_file([ccew_a, ccew_b],[],SUB_SPINE_CSV_FIELDS)
    she_file = write_input_data_to_tmp_file([she_row],[],SUB_SPINE_CSV_FIELDS)

    main_orgs = build_spine_for_test([ccew_file, she_file])

    assert sorted(main_orgs._store) == ['GB-CHC-2001', 'GB-CHC-2002']
    assert set(main_orgs.merged_uid_aliases) == set()
    # the housing record is absorbed into the lowest-uid candidate only
    assert [(m.uid, mt) for m, mt in main_orgs._store['GB-CHC-2001'].matched_orgs] == [
        ('GB-SHPE-2003', 'name - housing')]
    assert main_orgs._store['GB-CHC-2002'].matched_orgs == []

    main_csv, _, match_csv = write_spine_and_read_all(main_orgs)
    assert sorted(r['uid'] for r in _rows(main_csv)) == ['GB-CHC-2001', 'GB-CHC-2002']
    match_rows = _rows(match_csv)
    # the runner-up keeps an association-only (blank uid) row, as before
    assert [(r['orgA_uid'], r['orgB_uid'], r['match_type'])
            for r in match_rows if r['uid'] == ''] == [
        ('GB-CHC-2002', 'GB-SHPE-2003', 'name - housing')]
    assert not [r for r in match_rows if r['match_type'] == 'merge via bridge']


def test_bridge_merge_blocked_by_three_way_fan_out():
    # A bridge that fans out to THREE organisations proves nothing (the real failure
    # case was five unrelated OSCR "Ladybird Playgroup" charities reached by a single
    # Care Inspectorate record). NOTE: no single rule can reach ccew, oscr and mutuals
    # at once, so the three-way case is staged here as one OSCR charity and two mutuals
    # societies sharing a name, reached by one Scottish Housing Regulator record.
    oscr_row = sub_spine_entry_creator({
        "uid" : "GB-SC-SC3001",
        "organisationname" : "Ladybird Playgroup",
        "normalisedname" : "LADYBIRD PLAYGROUP",
        "source" : "OSCR",
        "id_in_source" : "SC3001",})
    mutual_a = sub_spine_entry_creator({
        "uid" : "GB-MPR-3002",
        "organisationname" : "Ladybird Playgroup",
        "normalisedname" : "LADYBIRD PLAYGROUP",
        "source" : "mutuals",
        "id_in_source" : "3002",})
    mutual_b = sub_spine_entry_creator({
        "uid" : "GB-MPR-3003",
        "organisationname" : "Ladybird Playgroup",
        "normalisedname" : "LADYBIRD PLAYGROUP",
        "source" : "mutuals",
        "id_in_source" : "3003",})
    shr_row = sub_spine_entry_creator({
        "uid" : "GB-SHR-3004",
        "organisationname" : "Ladybird Playgroup",
        "normalisedname" : "LADYBIRD PLAYGROUP",
        "source" : "scottishhousingregulator",
        "id_in_source" : "3004",})

    oscr_file = write_input_data_to_tmp_file([oscr_row],[],SUB_SPINE_CSV_FIELDS)
    mutuals_file = write_input_data_to_tmp_file([mutual_a, mutual_b],[],SUB_SPINE_CSV_FIELDS)
    shr_file = write_input_data_to_tmp_file([shr_row],[],SUB_SPINE_CSV_FIELDS)

    main_orgs = build_spine_for_test([oscr_file, mutuals_file, shr_file])

    assert sorted(main_orgs._store) == ['GB-MPR-3002', 'GB-MPR-3003', 'GB-SC-SC3001']
    assert set(main_orgs.merged_uid_aliases) == set()
    _, _, match_csv = write_spine_and_read_all(main_orgs)
    match_rows = _rows(match_csv)
    assert not [r for r in match_rows if r['match_type'] == 'merge via bridge']
    # two runners-up, two association-only rows
    assert sorted(r['orgA_uid'] for r in match_rows if r['uid'] == '') == [
        'GB-MPR-3003', 'GB-SC-SC3001']


def test_bridge_merge_blocked_by_association_only_evidence():
    # A record sharing a company number with two organisations is association-only
    # evidence ('companyid - companyid'): it never absorbs and never bridges.
    ccew_row = sub_spine_entry_creator({
        "uid" : "GB-CHC-6001",
        "organisationname" : "Alpha Relief",
        "normalisedname" : "ALPHA RELIEF",
        "companyid" : "06000001",
        "source" : "ccew",
        "id_in_source" : "6001",})
    oscr_row = sub_spine_entry_creator({
        "uid" : "GB-SC-SC6002",
        "organisationname" : "Beta Relief",
        "normalisedname" : "BETA RELIEF",
        "companyid" : "06000001",
        "source" : "OSCR",
        "id_in_source" : "SC6002",})
    mutual_row = sub_spine_entry_creator({
        "uid" : "GB-MPR-6003",
        "organisationname" : "Gamma Relief Society Limited",
        "normalisedname" : "GAMMA RELIEF SOCIETY LIMITED",
        "companyid" : "06000001",
        "source" : "mutuals",
        "id_in_source" : "6003",})

    ccew_file = write_input_data_to_tmp_file([ccew_row],[],SUB_SPINE_CSV_FIELDS)
    oscr_file = write_input_data_to_tmp_file([oscr_row],[],SUB_SPINE_CSV_FIELDS)
    mutuals_file = write_input_data_to_tmp_file([mutual_row],[],SUB_SPINE_CSV_FIELDS)

    main_orgs = build_spine_for_test([ccew_file, oscr_file, mutuals_file])

    assert sorted(main_orgs._store) == ['GB-CHC-6001', 'GB-MPR-6003', 'GB-SC-SC6002']
    assert set(main_orgs.merged_uid_aliases) == set()
    _, _, match_csv = write_spine_and_read_all(main_orgs)
    assert not [r for r in _rows(match_csv) if r['match_type'] == 'merge via bridge']


def test_bridge_merge_blocked_when_names_differ_and_evidence_is_name_only():
    # Two differently named organisations reached by one name-rule bridge are not
    # proven to be the same body. Here the CCEW charity is reachable under the housing
    # name only because it earlier absorbed a same-named Companies House company.
    ccew_row = sub_spine_entry_creator({
        "uid" : "GB-CHC-8002",
        "organisationname" : "Alpha Trust",
        "normalisedname" : "ALPHA TRUST",
        "companyid" : "08002000",
        "source" : "ccew",
        "id_in_source" : "8002",})
    mutual_row = sub_spine_entry_creator({
        "uid" : "GB-MPR-8001",
        "organisationname" : "Riverside Housing Society Limited",
        "normalisedname" : "RIVERSIDE HOUSING SOCIETY LIMITED",
        "source" : "mutuals",
        "id_in_source" : "8001",})
    ch_row = sub_spine_entry_creator({
        "uid" : "GB-COH-08002000",
        "organisationname" : "Riverside Housing Society Limited",
        "normalisedname" : "RIVERSIDE HOUSING SOCIETY LIMITED",
        "source" : "CH",
        "id_in_source" : "08002000",})
    she_row = sub_spine_entry_creator({
        "uid" : "GB-SHPE-8003",
        "organisationname" : "Riverside Housing Society Limited",
        "normalisedname" : "RIVERSIDE HOUSING SOCIETY LIMITED",
        "source" : "socialhousingengland",
        "id_in_source" : "8003",})

    ccew_file = write_input_data_to_tmp_file([ccew_row],[],SUB_SPINE_CSV_FIELDS)
    mutuals_file = write_input_data_to_tmp_file([mutual_row],[],SUB_SPINE_CSV_FIELDS)
    ch_file = write_input_data_to_tmp_file([ch_row],[],SUB_SPINE_CSV_FIELDS)
    she_file = write_input_data_to_tmp_file([she_row],[],SUB_SPINE_CSV_FIELDS)

    main_orgs = build_spine_for_test([ccew_file, mutuals_file, ch_file, she_file])

    # the company was absorbed into the charity, so the charity is now findable under
    # the company's name as well as its own - two candidates with different names
    assert sorted(main_orgs._store) == ['GB-CHC-8002', 'GB-MPR-8001']
    assert set(main_orgs.merged_uid_aliases) == set()
    _, _, match_csv = write_spine_and_read_all(main_orgs)
    match_rows = _rows(match_csv)
    assert not [r for r in match_rows if r['match_type'] == 'merge via bridge']
    assert [(r['orgA_uid'], r['orgB_uid'], r['match_type'])
            for r in match_rows if r['uid'] == ''] == [
        ('GB-MPR-8001', 'GB-SHPE-8003', 'name - housing')]


def test_bridge_merge_on_identifier_evidence_when_names_differ():
    # Different names are acceptable when BOTH links are identifier-based. A
    # co-operatives record carrying a registration number held by both a Mutuals
    # society and a Companies House company links to each by 'companyid - coop mutual'.
    # Mutuals is loaded before Companies House, so the mutual survives.
    mutual_row = sub_spine_entry_creator({
        "uid" : "GB-MPR-30014R",
        "organisationname" : "Greenway Workers Society Limited",
        "normalisedname" : "GREENWAY WORKERS SOCIETY LIMITED",
        "source" : "mutuals",
        "id_in_source" : "30014R",})
    ch_row = sub_spine_entry_creator({
        "uid" : "GB-COH-30014R",
        "organisationname" : "Greenway Trading Limited",
        "normalisedname" : "GREENWAY TRADING LIMITED",
        "source" : "CH",
        "id_in_source" : "30014R",})
    coop_row = sub_spine_entry_creator({
        "uid" : "GB-COOP-7788",
        "organisationname" : "Greenway Co-operative",
        "normalisedname" : "GREENWAY CO OPERATIVE",
        "companyid" : "30014R",
        "source" : "CoOps",
        "id_in_source" : "7788",})

    mutuals_file = write_input_data_to_tmp_file([mutual_row],[],SUB_SPINE_CSV_FIELDS)
    ch_file = write_input_data_to_tmp_file([ch_row],[],SUB_SPINE_CSV_FIELDS)
    coops_file = write_input_data_to_tmp_file([coop_row],[],SUB_SPINE_CSV_FIELDS)

    main_orgs = build_spine_for_test([mutuals_file, ch_file, coops_file])

    assert sorted(main_orgs._store) == ['GB-MPR-30014R']
    assert set(main_orgs.merged_uid_aliases) == {'GB-COH-30014R'}
    survivor = main_orgs._store['GB-MPR-30014R']
    assert sorted((m.uid, mt) for m, mt in survivor.matched_orgs) == [
        ('GB-COH-30014R', 'merge via bridge'),
        ('GB-COOP-7788', 'companyid - coop mutual'),
    ]
    _, _, match_csv = write_spine_and_read_all(main_orgs)
    assert ('GB-MPR-30014R', 'GB-COH-30014R', 'merge via bridge') in {
        (r['uid'], r['orgB_uid'], r['match_type']) for r in _rows(match_csv)}


def test_bridge_merge_survivor_precedence_ccew_over_oscr():
    # A CQC provider carrying both a company number (whose company was absorbed into a
    # CCEW charity) and a Scottish charity number bridges a CCEW and an OSCR
    # organisation. CCEW is loaded first, so CCEW survives. The two charities share a
    # name: CQC-cited identifiers alone are not enough for differently named pairs
    # (see bridge_evidence_is_strong_enough).
    ccew_row = sub_spine_entry_creator({
        "uid" : "GB-CHC-4001",
        "organisationname" : "Northern Care Trust",
        "normalisedname" : "NORTHERN CARE TRUST",
        "companyid" : "04001000",
        "source" : "ccew",
        "id_in_source" : "4001",})
    oscr_row = sub_spine_entry_creator({
        "uid" : "GB-SC-SC040011",
        "organisationname" : "Northern Care Trust",
        "normalisedname" : "NORTHERN CARE TRUST",
        "source" : "OSCR",
        "id_in_source" : "SC040011",})
    ch_row = sub_spine_entry_creator({
        "uid" : "GB-COH-04001000",
        "organisationname" : "Northern Care Trust Limited",
        "normalisedname" : "NORTHERN CARE TRUST LIMITED",
        "source" : "CH",
        "id_in_source" : "04001000",})
    cqc_row = make_cqc_row(companyid='04001000', charitynumber='SC040011')

    ccew_file = write_input_data_to_tmp_file([ccew_row],[],SUB_SPINE_CSV_FIELDS)
    oscr_file = write_input_data_to_tmp_file([oscr_row],[],SUB_SPINE_CSV_FIELDS)
    ch_file = write_input_data_to_tmp_file([ch_row],[],SUB_SPINE_CSV_FIELDS)
    cqc_file = write_input_data_to_tmp_file([cqc_row],[],SUB_SPINE_CSV_FIELDS+['charitynumber'])

    main_orgs = build_spine_for_test([ccew_file, oscr_file, ch_file, cqc_file])

    assert sorted(main_orgs._store) == ['GB-CHC-4001']
    assert set(main_orgs.merged_uid_aliases) == {'GB-SC-SC040011'}
    survivor = main_orgs._store['GB-CHC-4001']
    links = sorted((m.uid, mt) for m, mt in survivor.matched_orgs)
    assert ('GB-SC-SC040011', 'merge via bridge') in links
    assert ('GB-COH-04001000', 'companyid - id_in_source') in links
    # the bridging CQC record is absorbed with its ORIGINAL match types
    assert ('GB-CQC-1-101601999', 'companyid - cqc') in links
    assert ('GB-CQC-1-101601999', 'charityno - cqc') in links

    main_csv, _, match_csv = write_spine_and_read_all(main_orgs)
    assert [r['uid'] for r in _rows(main_csv)] == ['GB-CHC-4001']
    assert 'GB-CQC' not in main_csv
    # no runner-up association row was written for the bridging record: the only
    # blank-uid row here is the unrelated, pre-existing 'companyid - companyid' link
    # (the CQC record's company number is also the charity's company number)
    assert {r['match_type'] for r in _rows(match_csv) if r['uid'] == ''} == {
        'companyid - companyid'}


def test_bridge_merge_does_not_chain():
    # After a CCEW charity absorbs a mutual by bridge merge, the charity is still live
    # and can be a party to a later bridge merge; the organisation already merged away
    # can never be one again. (The later records are staged as extra input files.)
    ccew_row = sub_spine_entry_creator({
        "uid" : "GB-CHC-7001",
        "organisationname" : "Greenfield Housing",
        "normalisedname" : "GREENFIELD HOUSING",
        "source" : "ccew",
        "id_in_source" : "7001",})
    mutual_b = sub_spine_entry_creator({
        "uid" : "GB-MPR-7002",
        "organisationname" : "Greenfield Housing",
        "normalisedname" : "GREENFIELD HOUSING",
        "source" : "mutuals",
        "id_in_source" : "7002",})
    she_first = sub_spine_entry_creator({
        "uid" : "GB-SHPE-7003",
        "organisationname" : "Greenfield Housing",
        "normalisedname" : "GREENFIELD HOUSING",
        "source" : "socialhousingengland",
        "id_in_source" : "7003",})
    mutual_c = sub_spine_entry_creator({
        "uid" : "GB-MPR-7004",
        "organisationname" : "Greenfield Housing",
        "normalisedname" : "GREENFIELD HOUSING",
        "source" : "mutuals",
        "id_in_source" : "7004",})
    she_second = sub_spine_entry_creator({
        "uid" : "GB-SHPE-7005",
        "organisationname" : "Greenfield Housing",
        "normalisedname" : "GREENFIELD HOUSING",
        "source" : "socialhousingengland",
        "id_in_source" : "7005",})

    files = [
        write_input_data_to_tmp_file([ccew_row],[],SUB_SPINE_CSV_FIELDS),
        write_input_data_to_tmp_file([mutual_b],[],SUB_SPINE_CSV_FIELDS),
        write_input_data_to_tmp_file([she_first],[],SUB_SPINE_CSV_FIELDS),
        write_input_data_to_tmp_file([mutual_c],[],SUB_SPINE_CSV_FIELDS),
        write_input_data_to_tmp_file([she_second],[],SUB_SPINE_CSV_FIELDS),
    ]
    main_orgs = build_spine_for_test(files)

    assert sorted(main_orgs._store) == ['GB-CHC-7001']
    assert set(main_orgs.merged_uid_aliases) == {'GB-MPR-7002', 'GB-MPR-7004'}
    survivor = main_orgs._store['GB-CHC-7001']
    links = sorted((m.uid, mt) for m, mt in survivor.matched_orgs)
    assert links == [
        ('GB-MPR-7002', 'merge via bridge'),
        ('GB-MPR-7004', 'merge via bridge'),
        ('GB-SHPE-7003', 'name - housing'),
        ('GB-SHPE-7005', 'name - housing'),
    ]
    # the first loser appears exactly once, and never as a merge party a second time
    assert sum(1 for m, mt in survivor.matched_orgs
               if m.uid == 'GB-MPR-7002' and mt == BRIDGE_MERGE_MATCH_TYPE) == 1
    _, _, match_csv = write_spine_and_read_all(main_orgs)
    assert not [r for r in _rows(match_csv) if r['uid'] == '']


def test_bridge_merge_consolidates_status_and_cic_flag(tmp_path):
    # A merged-in organisation is an absorbed record like any other: if it is active,
    # the survivor must be active too (its own removal date moves to supplementary),
    # and its is_cic flag must reach the survivor.
    mutual_row = sub_spine_entry_creator({
        "uid" : "GB-MPR-30015R",
        "organisationname" : "Greenway Workers Society Limited",
        "normalisedname" : "GREENWAY WORKERS SOCIETY LIMITED",
        "source" : "mutuals",
        "source_register" : "Mutuals Public Register",
        "id_in_source" : "30015R",
        "removeddate" : "01/01/2020",})
    ch_row = sub_spine_entry_creator({
        "uid" : "GB-COH-30015R",
        "organisationname" : "Greenway Trading Limited",
        "normalisedname" : "GREENWAY TRADING LIMITED",
        "source" : "CH",
        "source_register" : "Companies House",
        "id_in_source" : "30015R",
        "is_cic" : "True",})
    coop_row = sub_spine_entry_creator({
        "uid" : "GB-COOP-7799",
        "organisationname" : "Greenway Co-operative",
        "normalisedname" : "GREENWAY CO OPERATIVE",
        "companyid" : "30015R",
        "source" : "CoOps",
        "id_in_source" : "7799",})

    files = [
        write_input_data_to_tmp_file([mutual_row],[],SUB_SPINE_CSV_FIELDS),
        write_input_data_to_tmp_file([ch_row],[],SUB_SPINE_CSV_FIELDS),
        write_input_data_to_tmp_file([coop_row],[],SUB_SPINE_CSV_FIELDS),
    ]
    main_orgs = build_spine_for_test(files)

    assert sorted(main_orgs._store) == ['GB-MPR-30015R']
    main_csv, extra_csv, _ = write_release_output_and_validate(main_orgs, tmp_path)
    spine_rows = _rows(main_csv)
    assert len(spine_rows) == 1
    assert spine_rows[0]['uid'] == 'GB-MPR-30015R'
    # the active merged-in company keeps the survivor active ...
    assert spine_rows[0]['removeddate'] == ''
    assert spine_rows[0]['is_cic'] == 'True'
    # ... and the survivor's own removal date is preserved in supplementary
    supplementary = _rows(extra_csv)
    assert any(r['uid'] == 'GB-MPR-30015R' and r['removeddate'] == '01/01/2020'
               for r in supplementary)
    # re-parenting the merged-in organisation's details must not duplicate rows:
    # one supplementary row per organisation involved, and no repeats
    assert sorted(r['uid'] for r in supplementary) == [
        'GB-COH-30015R', 'GB-COOP-7799', 'GB-MPR-30015R']
    fingerprints = [tuple(sorted(row.items())) for row in supplementary]
    assert len(fingerprints) == len(set(fingerprints))
# ---------------------------------------------------------------------------
# Bridge merge: re-parenting the loser's own match rows. A merged-away uid is no
# longer a spine row, so every match row it owned has to be re-pointed at the
# survivor, and re-parenting must not leave the same link recorded twice. These
# tests run the real release validator over the written output.
# ---------------------------------------------------------------------------

def write_release_output_and_validate(main_orgs, tmp_path):
    """Write the build's three CSVs under their release filenames, add what the later
    pipeline steps supply (cso_type/cso_subtype on the spine, and a SIC file), run the
    real release validator over the result, and hand back the written CSVs.

    write_out() is not idempotent - it appends to each organisation's match rows - so a
    test must write the output exactly once and read everything from that one write.
    """
    from spine import release as release_mod

    out_dir = tmp_path / 'release'
    out_dir.mkdir()
    staged_spine = out_dir / 'staged-spine.tmp'
    main_orgs.write_out(str(staged_spine),
                        str(out_dir / release_mod.SUPPLEMENTARY_FILENAME),
                        str(out_dir / release_mod.MATCHES_FILENAME))

    with open(staged_spine, newline='', encoding='utf-8') as f:
        spine_rows = list(csv.DictReader(f))
    os.remove(staged_spine)
    with open(out_dir / release_mod.SPINE_FILENAME, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(
            f, fieldnames=release_mod.CSV_HEADERS[release_mod.SPINE_FILENAME])
        writer.writeheader()
        for row in spine_rows:
            is_cic = row['is_cic'] == 'True'
            row['cso_type'] = 'CIC' if is_cic else 'Other'
            row['cso_subtype'] = ('CIC' if is_cic
                                  else 'Other Company Limited By Guarantee')
            writer.writerow(row)
    with open(out_dir / release_mod.SIC_FILENAME, 'w', newline='', encoding='utf-8') as f:
        sic_writer = csv.writer(f)
        sic_writer.writerow(['uid', 'SIC'])
        for row in spine_rows:
            sic_writer.writerow([row['uid'], '99999'])

    release_mod.validate_release(out_dir)

    texts = []
    for name in (release_mod.SPINE_FILENAME, release_mod.SUPPLEMENTARY_FILENAME,
                 release_mod.MATCHES_FILENAME):
        with open(out_dir / name, encoding='utf-8') as f:
            texts.append(f.read())
    return tuple(texts)


def _assert_match_table_is_sane(match_csv, main_csv):
    """The two release-contract properties this change can break."""
    spine_uids = {r['uid'] for r in _rows(main_csv)}
    rows = _rows(match_csv)
    for row in rows:
        assert row['orgA_uid'] in spine_uids, row
        assert row['orgA_uid'] != row['orgB_uid'], row
    keys = [(tuple(sorted((r['orgA_uid'], r['orgB_uid']))), r['match_type'])
            for r in rows]
    assert len(keys) == len(set(keys)), 'repeated endpoint pair + match type'


def test_bridge_merge_repoints_the_losers_association_rows(tmp_path):
    # The loser had been the runner-up for a housing record, so it owned a blank-uid
    # association row naming ITSELF as orgA. After the merge that uid is not a spine
    # row, so the row must be re-pointed at the survivor or release validation fails.
    # the charity shares its name with the two OSCR charities, because a CQC-cited
    # company number and charity number alone cannot fuse differently named bodies
    ccew_row = sub_spine_entry_creator({
        "uid" : "GB-CHC-4001",
        "organisationname" : "Braeside Housing Association",
        "normalisedname" : "BRAESIDE HOUSING ASSOCIATION",
        "companyid" : "04001000",
        "source" : "ccew",
        "source_register" : "Charity Commission for England and Wales",
        "id_in_source" : "4001",})
    oscr_keeper = sub_spine_entry_creator({
        "uid" : "GB-SC-SC040010",
        "organisationname" : "Braeside Housing Association",
        "normalisedname" : "BRAESIDE HOUSING ASSOCIATION",
        "source" : "OSCR",
        "source_register" : "Scottish Charity Register",
        "id_in_source" : "SC040010",})
    oscr_loser = sub_spine_entry_creator({
        "uid" : "GB-SC-SC040011",
        "organisationname" : "Braeside Housing Association",
        "normalisedname" : "BRAESIDE HOUSING ASSOCIATION",
        "source" : "OSCR",
        "source_register" : "Scottish Charity Register",
        "id_in_source" : "SC040011",})
    ch_row = sub_spine_entry_creator({
        "uid" : "GB-COH-04001000",
        "organisationname" : "Braeside Trading Limited",
        "normalisedname" : "BRAESIDE TRADING LIMITED",
        "source" : "CH",
        "source_register" : "Companies House",
        "id_in_source" : "04001000",})
    shr_row = sub_spine_entry_creator({
        "uid" : "GB-SHR-5000",
        "organisationname" : "Braeside Housing Association",
        "normalisedname" : "BRAESIDE HOUSING ASSOCIATION",
        "source" : "scottishhousingregulator",
        "source_register" : "Scottish Housing Regulator",
        "id_in_source" : "5000",})
    cqc_row = make_cqc_row(companyid='04001000', charitynumber='SC040011')

    files = [
        write_input_data_to_tmp_file([ccew_row],[],SUB_SPINE_CSV_FIELDS),
        write_input_data_to_tmp_file([oscr_keeper, oscr_loser],[],SUB_SPINE_CSV_FIELDS),
        write_input_data_to_tmp_file([ch_row],[],SUB_SPINE_CSV_FIELDS),
        write_input_data_to_tmp_file([shr_row],[],SUB_SPINE_CSV_FIELDS),
        write_input_data_to_tmp_file([cqc_row],[],SUB_SPINE_CSV_FIELDS+['charitynumber']),
    ]
    main_orgs = build_spine_for_test(files)

    assert set(main_orgs.merged_uid_aliases) == {'GB-SC-SC040011'}
    assert main_orgs.merged_uid_aliases['GB-SC-SC040011'] == 'GB-CHC-4001'

    main_csv, _, match_csv = write_release_output_and_validate(main_orgs, tmp_path)
    _assert_match_table_is_sane(match_csv, main_csv)
    # the runner-up row now belongs to the survivor, with the survivor's own source
    # and id_in_source on the orgA side
    assert [(r['orgA_uid'], r['orgA_source'], r['orgA_id_in_source'],
             r['orgB_uid'], r['match_type'])
            for r in _rows(match_csv)
            if r['uid'] == '' and r['orgB_uid'] == 'GB-SHR-5000'] == [
        ('GB-CHC-4001', 'ccew', '4001', 'GB-SHR-5000', 'name - housing')]


def test_bridge_merge_does_not_duplicate_a_link_it_now_absorbs(tmp_path):
    # Before the merge the survivor held a blank-uid runner-up row for a housing record
    # that the LOSER had absorbed. Re-parenting brings the absorption across, so the
    # old association row would repeat the same endpoint pair and match type.
    oscr_row = sub_spine_entry_creator({
        "uid" : "GB-SC-SC1",
        "organisationname" : "Highland Housing Association",
        "normalisedname" : "HIGHLAND HOUSING ASSOCIATION",
        "companyid" : "1R",
        "source" : "OSCR",
        "source_register" : "Scottish Charity Register",
        "id_in_source" : "SC1",})
    mutual_absorber = sub_spine_entry_creator({
        "uid" : "GB-MPR-1",
        "organisationname" : "Highland Housing Association",
        "normalisedname" : "HIGHLAND HOUSING ASSOCIATION",
        "source" : "mutuals",
        "source_register" : "Mutuals Public Register",
        "id_in_source" : "1R",})
    mutual_other = sub_spine_entry_creator({
        "uid" : "GB-MPR-2",
        "organisationname" : "Highland Housing Association",
        "normalisedname" : "HIGHLAND HOUSING ASSOCIATION",
        "source" : "mutuals",
        "source_register" : "Mutuals Public Register",
        "id_in_source" : "2R",})
    ch_row = sub_spine_entry_creator({
        "uid" : "GB-COH-1R",
        "organisationname" : "Highland Trading Limited",
        "normalisedname" : "HIGHLAND TRADING LIMITED",
        "source" : "CH",
        "source_register" : "Companies House",
        "id_in_source" : "1R",})
    shr_row = sub_spine_entry_creator({
        "uid" : "GB-SHR-9",
        "organisationname" : "Highland Housing Association",
        "normalisedname" : "HIGHLAND HOUSING ASSOCIATION",
        "source" : "scottishhousingregulator",
        "source_register" : "Scottish Housing Regulator",
        "id_in_source" : "9",})
    coop_row = sub_spine_entry_creator({
        "uid" : "GB-COOP-55",
        "organisationname" : "Highland Co-operative",
        "normalisedname" : "HIGHLAND CO OPERATIVE",
        "companyid" : "1R",
        "source" : "CoOps",
        "source_register" : "Co-operatives",
        "id_in_source" : "55",})

    files = [
        write_input_data_to_tmp_file([oscr_row],[],SUB_SPINE_CSV_FIELDS),
        write_input_data_to_tmp_file([mutual_absorber, mutual_other],[],SUB_SPINE_CSV_FIELDS),
        write_input_data_to_tmp_file([ch_row],[],SUB_SPINE_CSV_FIELDS),
        write_input_data_to_tmp_file([shr_row],[],SUB_SPINE_CSV_FIELDS),
        write_input_data_to_tmp_file([coop_row],[],SUB_SPINE_CSV_FIELDS),
    ]
    main_orgs = build_spine_for_test(files)

    assert main_orgs.merged_uid_aliases == {'GB-MPR-1': 'GB-SC-SC1'}
    main_csv, _, match_csv = write_release_output_and_validate(main_orgs, tmp_path)
    _assert_match_table_is_sane(match_csv, main_csv)
    # the housing record is now absorbed by the survivor, exactly once, and the stale
    # association row for the same link has gone
    housing_rows = [r for r in _rows(match_csv)
                    if r['orgB_uid'] == 'GB-SHR-9' and r['orgA_uid'] == 'GB-SC-SC1']
    assert [(r['uid'], r['match_type']) for r in housing_rows] == [
        ('GB-SC-SC1', 'name - housing')]


def test_bridge_merge_reparents_a_losers_child_and_its_runner_up_row(tmp_path):
    # The loser arrives at the merge with BOTH an absorbed sub-organisation of its own
    # and a blank-uid runner-up row. The child must move to the survivor exactly once,
    # and the runner-up row must move with its orgA side rewritten.
    oscr_row = sub_spine_entry_creator({
        "uid" : "GB-SC-SC1",
        "organisationname" : "Highland Housing Association",
        "normalisedname" : "HIGHLAND HOUSING ASSOCIATION",
        "companyid" : "1R",
        "source" : "OSCR",
        "source_register" : "Scottish Charity Register",
        "id_in_source" : "SC1",})
    mutual_ben_nevis = sub_spine_entry_creator({
        "uid" : "GB-MPR-0",
        "organisationname" : "Ben Nevis Co-operative",
        "normalisedname" : "BEN NEVIS CO OPERATIVE",
        "source" : "mutuals",
        "source_register" : "Mutuals Public Register",
        "id_in_source" : "0R",})
    mutual_loser = sub_spine_entry_creator({
        "uid" : "GB-MPR-1",
        "organisationname" : "Highland Housing Association",
        "normalisedname" : "HIGHLAND HOUSING ASSOCIATION",
        "source" : "mutuals",
        "source_register" : "Mutuals Public Register",
        "id_in_source" : "1R",})
    ch_row = sub_spine_entry_creator({
        "uid" : "GB-COH-1R",
        "organisationname" : "Highland Trading Limited",
        "normalisedname" : "HIGHLAND TRADING LIMITED",
        "source" : "CH",
        "source_register" : "Companies House",
        "id_in_source" : "1R",})
    # absorbed by the loser on the loser's own registration number, and giving it a
    # second indexed name (loaded before the Companies House record, so that at this
    # point the number identifies the mutual alone)
    coop_child = sub_spine_entry_creator({
        "uid" : "GB-COOP-7",
        "organisationname" : "Ben Nevis Co-operative",
        "normalisedname" : "BEN NEVIS CO OPERATIVE",
        "companyid" : "1R",
        "source" : "CoOps",
        "source_register" : "Co-operatives",
        "id_in_source" : "7",})
    shr_row = sub_spine_entry_creator({
        "uid" : "GB-SHR-9",
        "organisationname" : "Ben Nevis Co-operative",
        "normalisedname" : "BEN NEVIS CO OPERATIVE",
        "source" : "scottishhousingregulator",
        "source_register" : "Scottish Housing Regulator",
        "id_in_source" : "9",})
    coop_bridge = sub_spine_entry_creator({
        "uid" : "GB-COOP-8",
        "organisationname" : "Highland Co-operative",
        "normalisedname" : "HIGHLAND CO OPERATIVE",
        "companyid" : "1R",
        "source" : "CoOps",
        "source_register" : "Co-operatives",
        "id_in_source" : "8",})

    files = [
        write_input_data_to_tmp_file([oscr_row],[],SUB_SPINE_CSV_FIELDS),
        write_input_data_to_tmp_file([mutual_ben_nevis, mutual_loser],[],SUB_SPINE_CSV_FIELDS),
        write_input_data_to_tmp_file([coop_child],[],SUB_SPINE_CSV_FIELDS),
        write_input_data_to_tmp_file([ch_row],[],SUB_SPINE_CSV_FIELDS),
        write_input_data_to_tmp_file([shr_row],[],SUB_SPINE_CSV_FIELDS),
        write_input_data_to_tmp_file([coop_bridge],[],SUB_SPINE_CSV_FIELDS),
    ]
    main_orgs = build_spine_for_test(files)

    assert main_orgs.merged_uid_aliases == {'GB-MPR-1': 'GB-SC-SC1'}
    main_csv, _, match_csv = write_release_output_and_validate(main_orgs, tmp_path)
    _assert_match_table_is_sane(match_csv, main_csv)

    rows = _rows(match_csv)
    # the loser's absorbed child is now the survivor's, recorded once (the co-op also
    # shares the survivor's company number, which keeps its own association-only row)
    child_rows = [r for r in rows if r['orgB_uid'] == 'GB-COOP-7' and r['uid']]
    assert [(r['uid'], r['orgA_uid'], r['match_type']) for r in child_rows] == [
        ('GB-SC-SC1', 'GB-SC-SC1', 'companyid - coop mutual')]
    # the loser's runner-up row moved across, re-pointed at the survivor
    assert [(r['orgA_uid'], r['orgA_source'], r['orgB_uid'], r['match_type'])
            for r in rows if r['uid'] == '' and r['orgB_uid'] == 'GB-SHR-9'] == [
        ('GB-SC-SC1', 'OSCR', 'GB-SHR-9', 'name - housing')]


def test_ftc_link_to_a_merged_away_uid_resolves_to_the_survivor(tmp_path):
    # The Find that Charity same-as table names organisations by uid. After a bridge
    # merge the loser's uid is gone from the spine, so a later same-as row pointing at
    # it must be redirected to the survivor instead of matching nothing.
    ccew_row = sub_spine_entry_creator({
        "uid" : "GB-CHC-9100",
        "organisationname" : "Carol Housing Trust",
        "normalisedname" : "CAROL HOUSING TRUST",
        "source" : "ccew",
        "source_register" : "Charity Commission for England and Wales",
        "id_in_source" : "9100",})
    mutual_row = sub_spine_entry_creator({
        "uid" : "GB-MPR-9101",
        "organisationname" : "Carol Housing Trust",
        "normalisedname" : "CAROL HOUSING TRUST",
        "source" : "mutuals",
        "source_register" : "Mutuals Public Register",
        "id_in_source" : "9101",})
    she_row = sub_spine_entry_creator({
        "uid" : "GB-SHPE-9102",
        "organisationname" : "Carol Housing Trust",
        "normalisedname" : "CAROL HOUSING TRUST",
        "source" : "socialhousingengland",
        "source_register" : "Social Housing England",
        "id_in_source" : "9102",})
    ch_row = sub_spine_entry_creator({
        "uid" : "GB-COH-9103",
        "organisationname" : "Carol Trading Limited",
        "normalisedname" : "CAROL TRADING LIMITED",
        "source" : "CH",
        "source_register" : "Companies House",
        "id_in_source" : "9103",})

    files = [
        write_input_data_to_tmp_file([ccew_row],[],SUB_SPINE_CSV_FIELDS),
        write_input_data_to_tmp_file([mutual_row],[],SUB_SPINE_CSV_FIELDS),
        write_input_data_to_tmp_file([she_row],[],SUB_SPINE_CSV_FIELDS),
        write_input_data_to_tmp_file([ch_row],[],SUB_SPINE_CSV_FIELDS),
    ]
    sameas = write_csv(str(tmp_path / 'sameas.csv'),
                       [{"org_id_a" : "GB-COH-9103",
                         "org_id_b" : "GB-MPR-9101",
                         "source" : "manual"}],
                       ["org_id_a", "org_id_b", "source"])
    oscr_links = write_csv(str(tmp_path / 'oscr-links.csv'), [],
                           ["org_id_a", "org_id_b", "source"])

    main_orgs = process_csvs_to_build_spine(files, sameas_file=sameas,
                                            oscr_links_file=oscr_links)

    assert main_orgs.merged_uid_aliases == {'GB-MPR-9101': 'GB-CHC-9100'}
    assert sorted(main_orgs._store) == ['GB-CHC-9100']
    # the same-as row named the merged-away mutual; the company is absorbed into the
    # organisation that now holds it
    assert ('GB-COH-9103', 'ftc') in [
        (m.uid, mt) for m, mt in main_orgs._store['GB-CHC-9100'].matched_orgs]

    main_csv, _, match_csv = write_release_output_and_validate(main_orgs, tmp_path)
    _assert_match_table_is_sane(match_csv, main_csv)
# ---------------------------------------------------------------------------
# Identifier collisions across registers, and how much identifier evidence a
# bridge merge needs when the two organisations are not named the same.
# ---------------------------------------------------------------------------

def test_coop_company_number_does_not_match_a_scottish_charity_number():
    # A Scottish charity number and a Scottish company number share the SCnnnnnn format,
    # so an index keyed on the raw value returns both. The co-op rule must pick the
    # Companies House company and leave the charity alone. Real case: co-op
    # GB-COOP-R009306 linked both CITY CABS (EDINBURGH) LIMITED (GB-COH-SC033518) and
    # the unrelated charity '2nd Inchinnan Brownie Unit' (GB-SC-SC033518); in the v1.2
    # release that showed up as a blank-uid row, and a bridge merge would act on it.
    oscr_row = sub_spine_entry_creator({
        "uid" : "GB-SC-SC033518",
        "organisationname" : "2nd Inchinnan Brownie Unit",
        "normalisedname" : "2ND INCHINNAN BROWNIE UNIT",
        "source" : "OSCR",
        "source_register" : "Scottish Charity Register",
        "id_in_source" : "SC033518",})
    ch_row = sub_spine_entry_creator({
        "uid" : "GB-COH-SC033518",
        "organisationname" : "City Cabs (Edinburgh) Limited",
        "normalisedname" : "CITY CABS EDINBURGH LIMITED",
        "source" : "CH",
        "source_register" : "Companies House",
        "id_in_source" : "SC033518",})
    coop_row = sub_spine_entry_creator({
        "uid" : "GB-COOP-R009306",
        "organisationname" : "City Cabs (Edinburgh)",
        "normalisedname" : "CITY CABS EDINBURGH",
        "companyid" : "SC033518",
        "source" : "CoOps",
        "source_register" : "Co-operatives",
        "id_in_source" : "R009306",})

    files = [
        write_input_data_to_tmp_file([oscr_row],[],SUB_SPINE_CSV_FIELDS),
        write_input_data_to_tmp_file([ch_row],[],SUB_SPINE_CSV_FIELDS),
        write_input_data_to_tmp_file([coop_row],[],SUB_SPINE_CSV_FIELDS),
    ]
    main_orgs = build_spine_for_test(files)

    # the co-op joined the company only
    assert [(m.uid, mt) for m, mt in main_orgs._store['GB-COH-SC033518'].matched_orgs] == [
        ('GB-COOP-R009306', 'companyid - coop mutual')]
    # the charity is untouched, and nothing was merged
    assert main_orgs._store['GB-SC-SC033518'].matched_orgs == []
    assert main_orgs.merged_uid_aliases == {}
    assert sorted(main_orgs._store) == ['GB-COH-SC033518', 'GB-SC-SC033518']

    _, match_csv = write_spine_and_read(main_orgs)
    assert not [r for r in _rows(match_csv)
                if 'GB-SC-SC033518' in (r['orgA_uid'], r['orgB_uid'])]


def _cqc_bridge_build(charity_name, charity_normalised, company_name, company_normalised):
    """A CCEW charity and a separate Companies House company, bridged by one CQC
    provider record that cites the charity number and the company number."""
    ccew_row = sub_spine_entry_creator({
        "uid" : "GB-CHC-290874",
        "organisationname" : charity_name,
        "normalisedname" : charity_normalised,
        "source" : "ccew",
        "source_register" : "Charity Commission for England and Wales",
        "id_in_source" : "290874",})
    ch_row = sub_spine_entry_creator({
        "uid" : "GB-COH-08516620",
        "organisationname" : company_name,
        "normalisedname" : company_normalised,
        "source" : "CH",
        "source_register" : "Companies House",
        "id_in_source" : "08516620",})
    cqc_row = make_cqc_row(companyid='08516620', charitynumber='290874')
    return [
        write_input_data_to_tmp_file([ccew_row],[],SUB_SPINE_CSV_FIELDS),
        write_input_data_to_tmp_file([ch_row],[],SUB_SPINE_CSV_FIELDS),
        write_input_data_to_tmp_file([cqc_row],[],SUB_SPINE_CSV_FIELDS+['charitynumber']),
    ]


def test_cqc_identifiers_alone_do_not_merge_differently_named_organisations():
    # A CQC provider return routinely cites a charity number and the company number of
    # that charity's corporate trustee or trading subsidiary. Those are related bodies,
    # not the same body, so this evidence must not fuse them: the old behaviour (one
    # absorption plus a blank-uid row) stands.
    main_orgs = build_spine_for_test(_cqc_bridge_build(
        "Age Concern Hampshire", "AGE CONCERN HAMPSHIRE",
        "Age Concern Hampshire Corporate Trustee Limited",
        "AGE CONCERN HAMPSHIRE CORPORATE TRUSTEE LIMITED"))

    assert main_orgs.merged_uid_aliases == {}
    assert sorted(main_orgs._store) == ['GB-CHC-290874', 'GB-COH-08516620']
    _, match_csv = write_spine_and_read(main_orgs)
    rows = _rows(match_csv)
    assert not [r for r in rows if r['match_type'] == 'merge via bridge']
    # the provider record is absorbed by the stronger-ranked link only; the charity
    # keeps an association-only row
    assert [(r['orgA_uid'], r['match_type']) for r in rows if r['uid'] == ''] == [
        ('GB-CHC-290874', 'charityno - cqc')]
    assert [(r['uid'], r['orgB_uid'], r['match_type']) for r in rows if r['uid']] == [
        ('GB-COH-08516620', 'GB-CQC-1-101601999', 'companyid - cqc')]


def test_cqc_identifiers_merge_when_the_names_match():
    # Same evidence, same names: the pair is the same body and is merged, CCEW surviving.
    main_orgs = build_spine_for_test(_cqc_bridge_build(
        "Age Concern Hampshire", "AGE CONCERN HAMPSHIRE",
        "Age Concern Hampshire", "AGE CONCERN HAMPSHIRE"))

    assert main_orgs.merged_uid_aliases == {'GB-COH-08516620': 'GB-CHC-290874'}
    assert sorted(main_orgs._store) == ['GB-CHC-290874']


def test_cqc_identifiers_merge_when_names_differ_only_by_the_or_limited():
    # core_name() sets aside THE / LTD / LIMITED and punctuation, so these count as the
    # same name. Everything else in the name still has to agree.
    assert core_name('THE DISABILITIES TRUST') == core_name('Disabilities Trust Ltd.')
    assert core_name('AGE CONCERN HAMPSHIRE') != core_name(
        'AGE CONCERN HAMPSHIRE CORPORATE TRUSTEE LIMITED')

    main_orgs = build_spine_for_test(_cqc_bridge_build(
        "The Disabilities Trust", "THE DISABILITIES TRUST",
        "Disabilities Trust Limited", "DISABILITIES TRUST LIMITED"))

    assert main_orgs.merged_uid_aliases == {'GB-COH-08516620': 'GB-CHC-290874'}
    assert sorted(main_orgs._store) == ['GB-CHC-290874']


def test_differently_named_pair_merges_when_a_register_declares_the_identifier(tmp_path):
    # Differently named organisations may still be merged when at least one side is
    # identified by the registers themselves rather than by the provider's return: here
    # the same-as table links the provider record to the charity.
    files = _cqc_bridge_build(
        "Tageero", "TAGEERO",
        "Thames Homecare Ltd", "THAMES HOMECARE LTD")
    sameas = write_csv(str(tmp_path / 'sameas.csv'),
                       [{"org_id_a" : "GB-CQC-1-101601999",
                         "org_id_b" : "GB-CHC-290874",
                         "source" : "manual"}],
                       ["org_id_a", "org_id_b", "source"])
    oscr_links = write_csv(str(tmp_path / 'oscr-links.csv'), [],
                           ["org_id_a", "org_id_b", "source"])

    main_orgs = process_csvs_to_build_spine(files, sameas_file=sameas,
                                            oscr_links_file=oscr_links)

    assert main_orgs.merged_uid_aliases == {'GB-COH-08516620': 'GB-CHC-290874'}
    assert sorted(main_orgs._store) == ['GB-CHC-290874']
    links = sorted((m.uid, mt) for m, mt
                   in main_orgs._store['GB-CHC-290874'].matched_orgs)
    assert ('GB-COH-08516620', 'merge via bridge') in links
    assert ('GB-CQC-1-101601999', 'ftc') in links
def test_coop_number_reaches_a_company_already_absorbed_into_a_charity():
    # Behaviour change introduced with the co-op rule narrowing, pinned here. A co-op's
    # registered number can equal the number of a Companies House company that a CCEW
    # charity has already absorbed ('companyid - id_in_source'). The co-op is reached
    # through the charity and is now absorbed into it, so the charity is the only spine
    # organisation. In the v1.2 release the co-op stayed a spine row of its own with
    # nothing but the association-only company-number link (about 42 real cases, e.g.
    # the co-operative learning trusts).
    ccew_row = sub_spine_entry_creator({
        "uid" : "GB-CHC-1145678",
        "organisationname" : "Meadow Co-operative Learning Trust",
        "normalisedname" : "MEADOW CO OPERATIVE LEARNING TRUST",
        "companyid" : "07654321",
        "source" : "ccew",
        "source_register" : "Charity Commission for England and Wales",
        "id_in_source" : "1145678",})
    ch_row = sub_spine_entry_creator({
        "uid" : "GB-COH-07654321",
        "organisationname" : "Meadow Co-operative Learning Trust",
        "normalisedname" : "MEADOW CO OPERATIVE LEARNING TRUST",
        "source" : "CH",
        "source_register" : "Companies House",
        "id_in_source" : "07654321",})
    coop_row = sub_spine_entry_creator({
        "uid" : "GB-COOP-R123456",
        "organisationname" : "Meadow Co-operative Learning Trust",
        "normalisedname" : "MEADOW CO OPERATIVE LEARNING TRUST",
        "companyid" : "07654321",
        "source" : "CoOps",
        "source_register" : "Co-operatives",
        "id_in_source" : "R123456",})

    files = [
        write_input_data_to_tmp_file([ccew_row],[],SUB_SPINE_CSV_FIELDS),
        write_input_data_to_tmp_file([ch_row],[],SUB_SPINE_CSV_FIELDS),
        write_input_data_to_tmp_file([coop_row],[],SUB_SPINE_CSV_FIELDS),
    ]
    main_orgs = build_spine_for_test(files)

    # one spine organisation: the co-op no longer stands alone
    assert sorted(main_orgs._store) == ['GB-CHC-1145678']
    assert main_orgs.merged_uid_aliases == {}

    main_csv, match_csv = write_spine_and_read(main_orgs)
    assert [r['uid'] for r in _rows(main_csv)] == ['GB-CHC-1145678']
    assert sorted((r['uid'], r['orgA_uid'], r['orgB_uid'], r['match_type'])
                  for r in _rows(match_csv)) == [
        # the association-only company-number row the co-op already had
        ('', 'GB-CHC-1145678', 'GB-COOP-R123456', 'companyid - companyid'),
        # the company the charity absorbed
        ('GB-CHC-1145678', 'GB-CHC-1145678', 'GB-COH-07654321',
         'companyid - id_in_source'),
        # and the co-op, now absorbed through that company's number
        ('GB-CHC-1145678', 'GB-CHC-1145678', 'GB-COOP-R123456',
         'companyid - coop mutual'),
    ]


def test_holds_record_from_ignores_association_only_partners():
    # An absorbed record identifies the organisation that holds it; an association-only
    # 'companyid - companyid' partner keeps its own identity and must not, exactly as in
    # add_to_stores() / remove_from_stores().
    charity = SubSpineOrg(**sub_spine_entry_creator({
        "uid" : "GB-CHC-2200",
        "organisationname" : "Sample Charity",
        "normalisedname" : "SAMPLE CHARITY",
        "source" : "ccew",
        "id_in_source" : "2200",})).to_core_org()
    company = SubSpineOrg(**sub_spine_entry_creator({
        "uid" : "GB-COH-09990001",
        "organisationname" : "Sample Charity Trading Limited",
        "normalisedname" : "SAMPLE CHARITY TRADING LIMITED",
        "source" : "CH",
        "id_in_source" : "09990001",}))

    charity.matched_orgs.append((company, 'companyid - id_in_source'))
    assert holds_record_from(charity, ('mutuals', 'ch'), id_in_source='09990001')

    charity.matched_orgs[:] = [(company, 'companyid - companyid')]
    assert not holds_record_from(charity, ('mutuals', 'ch'), id_in_source='09990001')
