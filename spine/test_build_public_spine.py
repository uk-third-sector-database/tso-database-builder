from .build_public_spine import *
import pytest
from copy import deepcopy
from handler.base_definitions import public_spine_entry_creator, sub_spine_entry_creator, extra_csv_entry_creator, match_csv_entry_creator, MATCHES_CSV_FIELDS, SUB_SPINE_CSV_FIELDS, SPINE_CSV_FIELDS, EXTRA_DETAILS_CSV_FIELDS
import tempfile

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
    
    main_orgs = process_csvs_to_build_spine([ccew_file,oscr_file])
    

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
    public_spine_entry_creator({
        "uid" : "GB-CHC-1001",
        "organisationname" : "101 Trust Fund",
        "normalisedname" : "101 TRUST FUND",
        "fulladdress" : "1 Trust Fund Lane",
        "city" : "Dundee",
        "postcode" : "LL1 1LL",
        "registerdate" : "23/06/1961",
        "removeddate" : "23/06/2019",}),
    public_spine_entry_creator({
        "uid" : "GB-CHC-1002",
        "organisationname" : "The Charity group",
        "normalisedname" : "THE CHARITY GROUP",
        "fulladdress" : "High Street House",
        "city" : "Edinburgh",
        "postcode" : "EH1 1EH",
        "registerdate" : "01/06/1998",
        }),
    public_spine_entry_creator({
        "uid" : "GB-CHC-1003",
        "organisationname" : "The 51st Charity group",
        "normalisedname" : "THE 51ST CHARITY GROUP",
        "fulladdress" : "High Street House",
        "city" : "Glasgow",
        "postcode" : "G1 1EH",
        "registerdate" : "01/12/1990",
        }),
    public_spine_entry_creator({"uid" : "GB-SC-102",
        "organisationname" : "The Charity group",
        "normalisedname" : "THE CHARITY GROUP",
        "fulladdress" : "High Street House",
        "city" : "Edinburgh",
        "postcode" : "EH1 1EH",
        "companyid" : "",
        "registerdate" : "01/06/1998",
        "removeddate" : "",
        }),
    public_spine_entry_creator({
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

    main_orgs = process_csvs_to_build_spine([ccew_file,oscr_file])
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
    public_spine_entry_creator({
        "uid" : "GB-CHC-1001",
        "organisationname" : "101 Trust Fund",
        "normalisedname" : "101 TRUST FUND",
        "fulladdress" : "1 Trust Fund Lane",
        "city" : "Dundee",
        "postcode" : "LL1 1LL",
        "registerdate" : "23/06/1961",
        "removeddate" : "23/06/2019",
        }),
    public_spine_entry_creator({
        "uid" : "GB-CHC-1002",
        "organisationname" : "The Charity group",
        "normalisedname" : "THE CHARITY GROUP",
        "fulladdress" : "High Street House",
        "city" : "Edinburgh",
        "postcode" : "EH1 1EH",
        "registerdate" : "01/06/1998",
        }),
    public_spine_entry_creator({
        "uid" : "GB-CHC-1003",
        "organisationname" : "The 51st Charity group",
        "normalisedname" : "THE 51ST CHARITY GROUP",
        "fulladdress" : "High Street House",
        "city" : "Glasgow",
        "postcode" : "G1 1EH",
        "registerdate" : "01/12/1990",
        }),
    public_spine_entry_creator({"uid" : "GB-SC-102",
        "organisationname" : "The Charity group",
        "normalisedname" : "THE CHARITY GROUP",
        "fulladdress" : "High Street House",
        "city" : "Edinburgh",
        "postcode" : "EH1 1EH",
        "companyid" : "",
        "registerdate" : "01/06/1998",
        "removeddate" : "",
        }),
    public_spine_entry_creator({
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

    expected_main = public_spine_entry_creator({
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

    
    main_orgs = process_csvs_to_build_spine([base_file,new_file])
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
    
    expected_main = public_spine_entry_creator({
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

        
    main_orgs = process_csvs_to_build_spine([base_file,new_file])
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

    main_orgs = process_csvs_to_build_spine([base_file])
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
    expected_spine = public_spine_entry_creator({**ccew_row})
    print(expected_spine)
    # expected supplementary file:
    expected_supp = extra_csv_entry_creator({"uid" : "GB-CHC-1001",
                                            "organisationname" : "1001 Trust Fund",
                                            "fulladdress" : "An old address",
                                            "city" : "Dundee",
                                            "postcode" : "LL1 1LLJ",
                                            "registerdate" : "23/07/1961",
                                            "removeddate" : "01/01/2019"})
    
    # write input data to files:
    ccew_file = write_input_data_to_tmp_file([ccew_row],ccew_extras,SUB_SPINE_CSV_FIELDS)
    supp_file = ccew_file.replace('.csv','.supplementary.csv')

    # process:
    main_orgs = process_csvs_to_build_spine([ccew_file])
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


    expected_main = public_spine_entry_creator({
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

    
    main_orgs = process_csvs_to_build_spine([base_file,new_file])
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
    
    main_orgs = process_csvs_to_build_spine([ccew_file,oscr_file])
    

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
    public_spine_entry_creator({
        "uid" : "GB-CHC-1001",
        "organisationname" : "101 Trust Fund",
        "normalisedname" : "101 TRUST FUND",
        "fulladdress" : "1 Trust Fund Lane",
        "city" : "Dundee",
        "postcode" : "LL1 1LL",
        "registerdate" : "23/06/1961",
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