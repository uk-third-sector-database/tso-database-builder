

import pandas
from matplotlib import pyplot
import upsetplot
import re
import os

sources=[
"CCEW",  
"CCNI",
"CareInspectorateScot",
"CareQualityCommission",
"CoOps",
"Mutuals Public Register",
"OSCR",
"ScottishHousingRegulator",
"2014",
"2023",
"adv_api"]

source_codes = [
'CHC',
'CIS',
'COH',
'COOP',
'CQC',
'MPR',
'NI',
'SC',
'SHR','SHPE']



def plot_upset_by_code(infile,ofile,source_list=source_codes):
    
    print(f'processing csv for UpSet plotting of sets [{source_list}]')
    source_list=list(source_list)
    #print(type(source_list))
    df = pandas.read_csv(infile,usecols=['uid']).drop_duplicates()
    print(df)

    for s in source_list:
        print(s)
        df[s] = df['uid'].str.contains(s, case=False) #case insensitive match for 's' in df.uid
        # now df has a column for each source type, indicating whether uid is from source or not
    #print(df.columns)

    df = df.drop(labels='uid',axis=1)

    df_up = df.groupby(source_list).size()

    upsetplot.plot(df_up, orientation='horizontal', sort_by="cardinality")

    #pyplot.yscale('log')
    pyplot.title(os.path.basename(infile.name))
    pyplot.savefig(ofile)
    pyplot.show()


def match_type_counts(infile):
    df = pandas.read_csv(infile,usecols=['uid']).drop_duplicates()

    match_dict={}

    for m in list(df.uid):
        try:
            s = re.findall('GB-(.+?)-',m)
        except TypeError:
            print('type error in re, uid = ',m)
            continue
        s1='-'.join(s)
        if not s1 in match_dict.keys(): match_dict[s1]=1
        else: match_dict[s1]+=1

    k = list(match_dict.keys())
    k.sort()

    for id in k:
        print(f'{id} : {match_dict[id]}')
    

if __name__=='__main__':
    #for var in ['ccni','ccew','oscr']:
     #   print(var)
      #  infile = '../processed_data/ch.%s.concat.match-companyid.match-normname.permutate.csv'%var
       # match_type_counts(infile)

    infile = '../processed_data/all.matched_companyid.matched_normname.permutate.csv'
    #infile = '../processed_data/FindThatCharity_matches_processed.csv'
    match_type_counts(infile)
