
import pandas
import csv
import itertools
import re

from spine.wrangling import dict_indexed_by_field


from handler.base import NEW_SPINE_CSV_FORMAT



def deduplicate(csv_in,csv_out,matchfield,threshold):
    writer = csv.DictWriter(csv_out, fieldnames=NEW_SPINE_CSV_FORMAT, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(find_direct_matches(csv_in,matchfield,threshold))

def matched_uid(matched_list):
    '''
    Creates a new uid, as a concatenation of the uids of matched records
    If different uid is required, change code here
    '''
    uid = []
    matched_sources={}
    for record in matched_list:
        # perhaps uid is already a concatenation:
        #print(f'matched_uid_debug: {type(record)}')
        if type(record)==str:
            uid_list = record.split('_')
        else:
            uid_list = record['uid'].split('_')
        for u in uid_list:
            uid.append(u.strip())

    new_uid = '_'.join(sorted(set(uid)))

    codes = re.findall('GB-(.+?)-',new_uid)
    for i in codes:
        if not i in matched_sources.keys():
            matched_sources[i]=1
        else: matched_sources[i]+=1

    return (new_uid, len(set(uid)), matched_sources)


def find_direct_matches(csv_in,field,threshold):
    '''Searches entire csv file for exact matches in 'field'. New uid created for matches.
    Threshold the max number uids in a match: above this is leads to a message about bumper matching'''

    d = dict_indexed_by_field(csv_in,field)
    #print('field %s has %d unique values in %s\n'%(field,len(d.keys()),csv_in))
    new_rows=[]
    for unique_field in d.keys():
        #print(unique_field)
        #print(d[unique_field])
        uid, num_matches, match_sources= matched_uid(d[unique_field])
        # sources other than charity regulators must not be matched more than once:
        allow = True
        #print(match_sources)
        for source in match_sources.keys():
            if match_sources[source] >1 and source not in ['CHC','SC','NIC']:
                allow = True#False
        if num_matches < threshold and unique_field not in ['','.','0'] and allow:
            if not uid: continue
            for line in d[unique_field]:
                line['uid'] = uid
                new_rows.append(line)
        else:
            print(f'ignoring entry "{unique_field}" ({num_matches} matches), datasource(s): {list(match_sources.keys())}, concat uid: {uid} )')
            for line in d[unique_field]:
                new_rows.append(line)
    return new_rows



def find_close_matches(csv_in,field_list, threshold, ofile):
    '''Searches through csv_in and finds close matches in fields in 'field_list'.
    Threshold for matches to consider given by 'threshold'. Currently = number of edits between strings.
    Returns list of rows, with matches above threshold given matching (concatenated) uids.
    New field showing probability of match added to output for tuning.
    '''
    
    df= pandas.read_csv(csv_in,usecols=field_list+['uid'], dtype=str)
    df=df.drop_duplicates()
    print(df)
    uids = list(df['uid'])
    print('uids: ',uids)

    for i in range(len(uids)):
        # find close matches for all subsequent uids
        for i2 in range(i+1, len(uids)):
            orig_uid = uids[i]
            try_match_uid = uids[i2]


            # append df with uids of matches above threshold
            for f in field_list:

                f1= []
                # find all instances of 'field f' (e.g. normalisedname) assoicated with orig_uid
                for field_i in range(len(df[df.uid==orig_uid][f])):
                    f1.append(df[df.uid==orig_uid][f].iloc[field_i])


                f2=[]
                # find all instances of 'field f' (e.g. normalisedname) assoicated with try_match_uid
                for field_i2 in range(len(df[df.uid==try_match_uid][f])):
                    f2.append(df[df.uid==try_match_uid][f].iloc[field_i2])
                
                # if levenshtein < threshold for any pairing between f1 and f2, mark as match
                for f1_field in f1:
                    for f2_field in f2:
                    
                    
                        dist = levenshteinDistance(f1_field,f2_field)

                        if dist < threshold:
                            df.loc[df.uid==uids[i],'%s_match_uid'%f] = uids[i2]
                            df.loc[df.uid==uids[i],'%s_match_dist'%f] = dist
                            

    df.to_csv('%s.scores'%ofile)

    #df = update_uids_for_matches(df)


def update_uids_for_matches(df:pandas.DataFrame):
    '''takes a df with matched fields (e.g. created in find_close_matches)
    and creates matched uids ('_'.join(matched_uids)) for matched records.
    This can then be used for checking, and then permutating around addresses'''
    
    all_uid_fields = list(filter(lambda x: 'uid' in x, df.columns))
        
    print('fieldnames containing uid: ',all_uid_fields)
    for index,row in df.iterrows():
        print('\n\n',row)

        matched_uids=[]
        for f in all_uid_fields:
            # if this row has a uid in field f, add it to the list
            if row[f]: matched_uids.append(row[f])

        print('matched uids = ',matched_uids)
        try:
            flat_uid_list = list(itertools.chain.from_iterable([x.split('_') for x in matched_uids]))
        except AttributeError:
            flat_uid_list = matched_uids

        new_uid = '_'.join(sorted(set(str(item) for item in matched_uids))) #'_'.join(sorted(set(flat_uid_list)))
        print('new_uid: ',new_uid)

        for matched_uid in matched_uids:
            print(f'assigning {matched_uid}')
            #update df to reflect new uid for each uid field found - should be updating 'uid' field and not x_match_uid fields
            df.loc[df['uid'] == matched_uid, 'uid'] = new_uid
            # not quite working - see pytest.
        print(df)
    return df



def levenshteinDistance(s1, s2):
    print('levenshtein between %s and %s'%(s1,s2))
    if len(s1) > len(s2):
        s1, s2 = s2, s1

    distances = range(len(s1) + 1)
    for i2, c2 in enumerate(s2):
        distances_ = [i2+1]
        for i1, c1 in enumerate(s1):
            if c1 == c2:
                distances_.append(distances[i1])
            else:
                distances_.append(1 + min((distances[i1], distances[i1 + 1], distances_[-1])))
        distances = distances_
    return distances[-1] 


def df_comparing_match_lists(list1,list2):
    '''Takes two lists of UIDs (in form uid1_uid2 for matched orgs uid1 and uid2), creates 
    df indexed by all original orgs, with values equal to the matchings in each of the input lists.
    e.g. CHC1_CHC2 in list1, CHC1_CHC3 in list2
    df = {uid:[CHC1,CHC2,CHC3],
    list1_match:[CHC1_CHC2,CHC1_CHC2,''],
    list2_match:[CHC1_CHC3,'',CHC1_CHC3]}
    '''
    all_uids = []
    for i in list1 + list2:
        all_uids += i.split('_')

    uuids = list(set(all_uids))
    print(uuids)

    columns = ['list1_match', 'list2_match']
    df = pandas.DataFrame(index=uuids, columns=columns)
    
    print(df)
    for i in list1:
        print(i)
        # split i into component parts, for each part, add i to column_list1 in the df
        for part in i.split('_'):
            print(part)
            df.loc[part,'list1_match'] = i

    for i in list2:
        for part in i.split('_'):
            df.loc[part,'list2_match'] = i

    print(df)
    return df


def find_linked_names(linked_uid,lookup_df):
    '''called by compare_org_matching; generates list of all the orgnames in the linked uid (in form uid1_uid2).
    returns comma separated string, for use by single cell of resultant df'''

    result_list =[]
    for u in str(linked_uid).split('_'):
        print(u)
        ret = lookup_df.loc[lookup_df['uid'] == u, 'organisationname'].tolist()
        print(ret)
        result_list.extend(ret)

    return ', '.join(result_list)


def compare_org_matching(file1,file2,lookup,ofile):
    '''takes two files, compares the linkages of organisations within each,
    outputs a file with the uid and name of each original org (using the lookup input file)'''

    f1_df = pandas.read_csv(file1,usecols=['uid'])
    f2_df = pandas.read_csv(file2,usecols=['uid'])
    lookup_df = pandas.read_csv(lookup,usecols=['uid','organisationname'])  # this should be a file with each uid pre-matching, e.g. spine.concat.csv

    df = df_comparing_match_lists(list(f1_df['uid']),list(f2_df['uid']))
    df.reset_index(inplace=True)
    df.rename(columns={'index': 'uuids'}, inplace=True)
    print(df)
    # df has columns 'uuids','list1_match','list2_match'
    # we want to add orgname for each uid, and for each matched uid


    for u in df.uuids:
        # Find the organisationname of each uid using lookup file
        #orgname_results = lookup_df.loc[df['uid'] == u, 'organisationname']
        #df.loc[df['uuids'] == u, 'organisationname'] = ', '.join(orgname_results.tolist())
        
        df.loc[df['uuids'] == u, 'organisationname'] = find_linked_names(u,lookup_df)
        df.loc[df['uuids'] == u, 'list_1_organisationnames'] = find_linked_names(df.loc[df['uuids']==u,'list1_match'],lookup_df)
        df.loc[df['uuids'] == u, 'list_2_organisationnames'] = find_linked_names(df.loc[df['uuids']==u,'list2_match'],lookup_df)

    df.to_csv(ofile)


if __name__=='__main__':
    f = '../processed_data/ccni_CH2023.concat.permutate.csv'

    o = '../processed_data/ccni_CH2023.concat.permutate.SPLINK_OUTPUT.csv'

    #splink_matching(f,o)

    charity_file = '../processed_data/charity_only.match-companyid.match_normname.permutate.csv'
    FTC_file = '../raw_data/FindThatCharity.CHC.SC.NIC.only.csv'


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
