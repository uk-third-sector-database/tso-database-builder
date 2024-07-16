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