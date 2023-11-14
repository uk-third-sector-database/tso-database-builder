import io

import pytest
import pandas

from .matching import deduplicate, find_direct_matches, find_close_matches, update_uids_for_matches, compare_org_matching, find_linked_names, df_comparing_match_lists


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

def test_charity_company_match():
    for_file = '''uid,organisationname,normalisedname,companyid,charitynumber,fulladdress,postcode,source
GB-CHC-200000,HOMEBOUND CRAFTSMEN TRUST,HOMEBOUND CRAFTSMEN TRUST,1234,200000,"25A HOLLAND STREET, LONDON",W8 4NA,CCEW
GB-XX-1234,HOMEBOUND,HOMEBOUND,1234,,"25A HOLLAND STREET, LONDON",W8 4NA,XX
GB-XX-3456,Something,SOMETHING,,3456,"2 HOLL STREET, LONDON",5AS 6FF,XX'''
    f1 = io.StringIO(for_file)


    
    expected1 = [{'uid': 'GB-CHC-200000_GB-XX-1234', 'organisationname': 'HOMEBOUND CRAFTSMEN TRUST', 'normalisedname': 'HOMEBOUND CRAFTSMEN TRUST', 'companyid': '1234', 
                'charitynumber': '200000', 'fulladdress': '25A HOLLAND STREET, LONDON', 'postcode': 'W8 4NA', 'source': 'CCEW'},
                {'uid': 'GB-CHC-200000_GB-XX-1234', 'organisationname': 'HOMEBOUND', 'normalisedname': 'HOMEBOUND', 'companyid': '1234', 
                 'charitynumber': '', 'fulladdress': '25A HOLLAND STREET, LONDON', 'postcode': 'W8 4NA', 'source': 'XX'},
                 {'charitynumber': '3456','companyid': '','fulladdress': '2 HOLL STREET, LONDON','normalisedname': 'SOMETHING',
                  'organisationname': 'Something','postcode': '5AS 6FF','source': 'XX','uid': 'GB-XX-3456'}]
    expected2 = [{'uid': 'GB-XX-1234_GB-CHC-200000', 'organisationname': 'HOMEBOUND CRAFTSMEN TRUST', 'normalisedname': 'HOMEBOUND CRAFTSMEN TRUST', 'companyid': '1234', 
                'charitynumber': '200000', 'fulladdress': '25A HOLLAND STREET, LONDON', 'postcode': 'W8 4NA', 'source': 'CCEW'},
                {'uid': 'GB-XX-1234_GB-CHC-200000', 'organisationname': 'HOMEBOUND', 'normalisedname': 'HOMEBOUND', 'companyid': '1234', 
                 'charitynumber': '', 'fulladdress': '25A HOLLAND STREET, LONDON', 'postcode': 'W8 4NA', 'source': 'XX'},
                 {'charitynumber': '3456','companyid': '','fulladdress': '2 HOLL STREET, LONDON','normalisedname': 'SOMETHING',
                  'organisationname': 'Something','postcode': '5AS 6FF','source': 'XX','uid': 'GB-XX-3456'}]
    
        #'GB-CHC-200000_GB-XX-1234'
    
    assert find_direct_matches(f1,'companyid',3) == expected1



def test_company_id_match():
    for_file = '''uid,organisationname,normalisedname,companyid,charitynumber,fulladdress,postcode,source
GB-CHC-200000,HOMEBOUND CRAFTSMEN TRUST,HOMEBOUND CRAFTSMEN TRUST,1234,200000,"25A HOLLAND STREET, LONDON",W8 4NA,CCEW
GB-XX-1234,HOMEBOUND,HOMEBOUND,.,,"25A HOLLAND STREET, LONDON",W8 4NA,XX
GB-XX-3456,Something,SOMETHING,.,3456,"2 HOLL STREET, LONDON",5AS 6FF,XX'''
    f1 = io.StringIO(for_file)


    
    expected1 = [{'uid': 'GB-CHC-200000', 'organisationname': 'HOMEBOUND CRAFTSMEN TRUST', 'normalisedname': 'HOMEBOUND CRAFTSMEN TRUST', 'companyid': '1234', 
                'charitynumber': '200000', 'fulladdress': '25A HOLLAND STREET, LONDON', 'postcode': 'W8 4NA', 'source': 'CCEW'},
                {'uid': 'GB-XX-1234', 'organisationname': 'HOMEBOUND', 'normalisedname': 'HOMEBOUND', 'companyid': '.', 
                 'charitynumber': '', 'fulladdress': '25A HOLLAND STREET, LONDON', 'postcode': 'W8 4NA', 'source': 'XX'},
                 {'charitynumber': '3456','companyid': '.','fulladdress': '2 HOLL STREET, LONDON','normalisedname': 'SOMETHING',
                  'organisationname': 'Something','postcode': '5AS 6FF','source': 'XX','uid': 'GB-XX-3456'}]

    
        #'GB-CHC-200000_GB-XX-1234'
    
    assert find_direct_matches(f1,'companyid',3) == expected1



def test_norm_name_match():
    for_file = '''uid,organisationname,normalisedname,companyid,charitynumber,fulladdress,postcode,source
GB-CHC-200000,HOMEBOUND CRAFTSMEN TRUST,HOMEBOUND CRAFTSMEN TRUST,1234,200000,"25A HOLLAND STREET, LONDON",W8 4NA,CCEW
GB-CHC-1234,HOMEBOUND,HOMEBOUND,1234,,"25A HOLLAND STREET, LONDON",W8 4NA,CHC
GB-CHC-3456,Something,HOMEBOUND,,3456,"2 HOLL STREET, LONDON",5AS 6FF,CHC'''
    f1 = io.StringIO(for_file)
    
    expected1 = [{'uid': 'GB-CHC-200000', 'organisationname': 'HOMEBOUND CRAFTSMEN TRUST', 'normalisedname': 'HOMEBOUND CRAFTSMEN TRUST', 'companyid': '1234', 
                'charitynumber': '200000', 'fulladdress': '25A HOLLAND STREET, LONDON', 'postcode': 'W8 4NA', 'source': 'CCEW'},
                {'uid': 'GB-CHC-1234_GB-CHC-3456', 'organisationname': 'HOMEBOUND', 'normalisedname': 'HOMEBOUND', 'companyid': '1234', 
                 'charitynumber': '', 'fulladdress': '25A HOLLAND STREET, LONDON', 'postcode': 'W8 4NA', 'source': 'CHC'},
                 {'charitynumber': '3456','companyid': '','fulladdress': '2 HOLL STREET, LONDON','normalisedname': 'HOMEBOUND',
                  'organisationname': 'Something','postcode': '5AS 6FF','source': 'CHC','uid': 'GB-CHC-1234_GB-CHC-3456'}]

    assert find_direct_matches(f1,'normalisedname',3) == expected1
    


@pytest.mark.xfail()
def test_deduplicate():
    for_file = '''uid,organisationname,normalisedname,companyid,charitynumber,fulladdress,postcode,source
    a1,name,NAME,1234,,"address, city",AS12 2DF,XX
    a2,name,NAME,222,,"address a2,city2",DF1 3ER,XX
    a3,new name,NEWNAME_CHAR,2002,1222,"char address,city",RR3 3RR,XX
    a4,new name,NEWNAME_CO,2002,,"co address,city",RR3 3RR,XX'''
    f1 = io.StringIO(for_file)
    expected = [{'uid':'a1_a2',
                'charitynumber': '',
                'companyid': '1234',
                'fulladdress': 'address, city',
                'normalisedname': 'NAME',
                'organisationname': 'name',
                'postcode': 'AS12 2DF',
                'source': 'XX'},
                {'uid':'a1_a2',
                'charitynumber': '',
                'companyid': '222',
                'fulladdress': 'address a2, city2',
                'normalisedname': 'NAME',
                'organisationname': 'name',
                'postcode': 'DF1 3ER',
                'source': 'XX'},
                {'uid':'a3_a4',
                'charitynumber': '1222',
                'companyid': '2002',
                'fulladdress': 'char address, city',
                'normalisedname': 'NEWNAME',
                'organisationname': 'new name',
                'postcode': 'RR3 3RR',
                'source': 'XX'},
                {'uid':'a3_a4',
                'charitynumber': '',
                'companyid': '2002',
                'fulladdress': 'co address, city',
                'normalisedname': 'NEWNAME',
                'organisationname': 'new name',
                'postcode': 'RR3 3RR',
                'source': 'XX'},]
    

    #f3 = io.StringIO() #need test to write to disk due to current state of deduplicate function requiring interim files written to disk
    f3 = open('test_dedupe.tmp','w')
    deduplicate(f1,f3)

    #f3.seek(0)
    #f3_data = f3.read()
    f3_data = open('test_dedupe.tmp','r')

    #assert_files_basically_same(f3.read(), expected)
    assert f3_data == expected



def test_close_matches_name():
    for_file = '''uid,organisationname,normalisedname,companyid,charitynumber,fulladdress,postcode,source
    a1,name,NAME,1234,,"address, city",AS12 2DF,XX
    a2,name,NAME,222,,"address a2,city2",DF1 3ER,XX
    a3,new name,NEWNAME_CHAR,2002,1222,"char address,city",RR3 3RR,XX
    a4,new name,NEWNAME_CO,2002,,"co address,city",RR3 3RR,XX'''
    f1 = io.StringIO(for_file)
    
    assert find_close_matches(f1,['normalisedname'],5,'tmp.test_matching.out.csv') == None


def test_close_matches_name():
    for_file = '''uid,organisationname,normalisedname,companyid,charitynumber,fulladdress,postcode,source
    a1,name,NAME,1234,,"address, city",AS12 2DF,XX
    a2,name,NAME,222,,"address a2,city2",DF1 3ER,XX
    a3,new name,NEWNAME_CHAR,2002,1222,"char address,city",RR3 3RR,XX
    a4,new name,NEWNAME_CO,2002,,"co address,city",RR3 3RR,XX'''
    f1 = io.StringIO(for_file)
    
    assert find_close_matches(f1,['normalisedname','postcode'],3,'tmp.test_matching.2fields.out.csv') == None

@pytest.mark.xfail()
def test_update_uids_for_matches():
    df = pandas.DataFrame({'uid':[1,2,3,4,5,6,7],
                           'asd_uid':['',6,7,'','','',''],
                           'bbb_uid':['','',1,'',4,'','']})
    expected = pandas.DataFrame({'uid':[1_3_7,2_6,1_3_7,4_5,4_5,2_6,7],
                           'asd_uid':['',6,7,'','','',''],
                           'bbb_uid':['','',1,'',4,'','']})

    result = expected.compare(update_uids_for_matches(df))
    print(f'output of df.compare: {result}')
    assert result.shape[0]==0 # if dataframes are identical, resulting df from df.compare has 0 rows



def test_compare_match_lists():
    list1 = ['a_b','c_d','e_f_g']
    list2 = ['a_b','c','d','f_g']
    uuids = ['a','b','c','d','e','f','g']
    data = {'list1_match':['a_b','a_b','c_d','c_d','e_f_g','e_f_g','e_f_g'],
            'list2_match':['a_b','a_b','c','d',float('nan'),'f_g','f_g']}

    expected_df = pandas.DataFrame(data, index=uuids)
    print(expected_df)



    df = df_comparing_match_lists(list1,list2)

    pandas.testing.assert_frame_equal(df,expected_df,check_like=True)

def test_find_names():
    lookup = {'uid':['44','55','66'],
              'organisationname':['four','five','six']}
    df = pandas.DataFrame(lookup)

    assert find_linked_names('44_55',df)=='four, five'


def test_compare_matching():
    for_f1 = '''uid
    '44_55'
    '66'
    '''

    for_f2='''uid
    '44'
    '55_66'
    '''

    lookup='''uid,organisationname
    44, four
    55, five
    66, six
    '''
    

    f1 = io.StringIO(for_f1)
    f2 = io.StringIO(for_f2)
    lookup_file = io.StringIO(lookup)

    compare_org_matching(f1,f2,lookup_file,'tmp.out')
    acutal_output = open('tmp.out','r').read()
    expected_output = ''
    