#verify_build.py

import pandas as pd


def verify_representation(infiles,ofile_basename):

    infile_uids = set()
    for csvfile in infiles:
        # find all uids in infiles, excepting CIS and CQC
        df = pd.read_csv(csvfile, usecols=['uid','source'])
        df = df[~df['source'].isin(['CareInspectorateScot','CareQualityCommission'])]
        uids = list(df['uid'])
        infile_uids.update(uids)
        print(f'\tinfile {csvfile} has {len(uids)} (ignoring any CIS and CQC)')
        
    print(f'\n\nTotal unique uids in all infiles = {len(infile_uids)} \n\n')

    spine_uids = set()
    for csv,fields in [(ofile_basename+'.spine.csv',['uid']),
                        (ofile_basename+'.matches.csv',['orgA_uid','orgB_uid'])]:
        # find all uids in spine
        df = pd.read_csv(csv,usecols=fields)
        for f in fields:
            spine_uids.update(df[f])

    print(f'\n\nUnique uids in spine and matches files = {len(spine_uids)}\n\n')

    # use set comprehension to find any expected from infiles which aren't in ofiles.
    print('All infile uids are expected in ofiles. Any missing?')
    diff = infile_uids.difference(spine_uids)
    print(f'Difference between infile and spine uid sets = {len(diff)}')
    print(diff)


def create_tex_table(spine_files_basename):

    
    def get_value_counts(s):
        def find_source(n):
            return n.split('-')[1]
        
        df = pd.DataFrame(s,columns=['uid'])
        df['source'] = df['uid'].apply(find_source)
        vc = df['source'].value_counts().reset_index()
        vc.columns=['source','count']
        vc['count'] = vc['count'].fillna(0).astype(int)
        return vc


    # uids in spine
    spine_uids = set()
    # uids in matches
    matches_uids = set()
    # table per source type
    for csv_,fields,set_ in [(spine_files_basename+'.spine.csv',['uid'],spine_uids),
                    (spine_files_basename+'.matches.csv',['orgA_uid','orgB_uid'],matches_uids)]:
        df = pd.read_csv(csv_,usecols=fields)
        for f in fields:
            set_.update(df[f])


    matches_not_spine_uids = matches_uids.difference(spine_uids)

    spine_vc = get_value_counts(spine_uids)
    matches_vc = get_value_counts(matches_uids)
    matches_not_spine_vc = get_value_counts(matches_not_spine_uids)

    spine_vc = spine_vc.rename(columns={'count': 'count_spine'})
    matches_vc = matches_vc.rename(columns={'count': 'count_matches'})
    matches_not_spine_vc = matches_not_spine_vc.rename(columns={'count': 'count_matches_not_spine'})

    merged_df = pd.merge(spine_vc, matches_vc, on='source', how='outer')
    merged_df = pd.merge(merged_df,matches_not_spine_vc, on='source', how='outer')
    #merged_df = merged_df.sort_values(by='count_spine', ascending=False)
    source_order = ['CHC','SC','NIC','COH','COOP','MPR','SHR','SHPE','CIS','CQC']

    merged_df['source'] = pd.Categorical(merged_df['source'], categories=source_order, ordered=True)

    merged_df = merged_df.sort_values('source')


    merged_df = merged_df.reset_index(drop=True)

    merged_df['count_spine'] = merged_df['count_spine'].fillna(0).astype(int)
    merged_df['count_matches'] = merged_df['count_matches'].fillna(0).astype(int)
    merged_df['count_matches_not_spine'] = merged_df['count_matches_not_spine'].fillna(0).astype(int)

                
    print(merged_df)
    
    print(merged_df.to_latex(index=False))
    
    









