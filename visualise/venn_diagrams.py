

import pandas
import re
import matplotlib.pyplot as plt
import matplotlib_venn
from tqdm import tqdm
import time

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
'CoOps':'COOP', # not in org_id - might need to update mapping
'Mutuals Public Register': 'MPR',
'SocialHousingEngland':'SHPE'
}


def venn_diagram_of_CH_sources(infile, ofile):
    ''' for given input csv, draw venn diagram of how the companies house data has overlapped in the matching process
    '''
 
    venn_groups={'[2014]':'A','[2023]':'B','[gap]':'C'}

    df = pandas.read_csv(infile,usecols=['uid','source'])

    uids=list(set(df.uid))

    print('%d unique uids'%len(uids))

    sources=[]

    progress_bar = tqdm(total = len(uids),desc='progress through uids',unit='uid')
    start_time = time.time()

    for uid in uids:
        s = list(df[df.uid==uid].source)[0] # only look at each uid once
        g = re.findall('\[.*?\]',s) # find companies house identifiers in source field, and create string
        g.sort()

        g = ''.join(g)
        #print(g)

        for i in venn_groups.keys():
            g=g.replace(i,venn_groups[i]) # replace identifiers with A|B|C for venn diagram
        if len(g)==3: g='ABC'
        sources.append(g)
        progress_bar.update(1)
        #print(g)
    progress_bar.close()
    end_time = time.time()
    print('building data for venn diagram took %f seconds'%(end_time - start_time))

    for_venn = {'A':0,'B':0,'AB':0,'C':0,'AC':0,'BC':0,'ABC':0}
    for s in sources:
        try: 
            for_venn[s] += 1
        except KeyError:
            print('%s in sources list, not in venn dict keys'%s)

    print(for_venn)
    
    subset_list = ['A','B','AB','C','AC','BC','ABC']

    lookup_func = lambda x: for_venn.get(x, x)
    result = list(map(lookup_func, subset_list))

    matplotlib_venn.venn3(subsets=result,set_labels=['COH 2014','COH 2023','COH gap'])

    plt.savefig(ofile)



def venn_diagram_info_using_pandas(infile,ofile):

    venn_groups={'[2014]':'A',
                 '[2023]':'B',
                 '[gap]':'C'}

    df = pandas.read_csv(infile,usecols=['uid','source'])
    print(df.shape)

    df_copy = df.copy()
    df = df_copy.drop_duplicates()
    print(df.shape)


    uids=list(set(df.uid))

    print('%d unique uids'%len(uids))

   
    start_time = time.time()

    # add columns according to required subsets:

    df['ch_2014'] = df['source'].str.contains('2014_prior').astype(int)  
    df['ch_2023'] = df['source'].str.contains('2023_download').astype(int)  
    df['ch_gap'] = df['source'].str.contains('adv_api').astype(int)  
    
    # combinations:
    df['ch_14_23'] = (df['ch_2014'] + df['ch_2023'] == 2) & (df['ch_gap'] == 0)
    df['ch_14_gap'] = (df['ch_2014'] + df['ch_gap'] == 2) & (df['ch_2023'] == 0)
    df['ch_23_gap'] = (df['ch_gap'] + df['ch_2023'] == 2) & (df['ch_2014'] == 0)
    df['ch_14_23_gap'] = (df['ch_gap'] + df['ch_2023'] + df['ch_2014'] == 3)
   
    df['ch_14_23'] = df['ch_14_23'].astype(int)
    df['ch_14_gap'] = df['ch_14_gap'].astype(int)
    df['ch_23_gap'] = df['ch_23_gap'].astype(int)
    df['ch_14_23_gap'] = df['ch_14_23_gap'].astype(int)

    df['ch_14_only'] = (df['ch_2014'] == 1) & (df['ch_2023'] + df['ch_gap'] == 0)
    df['ch_23_only'] = (df['ch_2023'] == 1) & (df['ch_2014'] + df['ch_gap'] == 0)
    df['ch_gap_only'] = (df['ch_gap'] == 1) & (df['ch_2023'] + df['ch_2014'] == 0)

    df['ch_14_only'] = df['ch_14_only'].astype(int)
    df['ch_23_only'] = df['ch_23_only'].astype(int)
    df['ch_gap_only'] = df['ch_gap_only'].astype(int)

    print(df)


    end_time = time.time()
    print('building data for venn diagram took %f seconds'%(end_time - start_time))

    df.to_csv(ofile+'.data.csv')


    subset_list = ['ch_14_only','ch_23_only','ch_14_23','ch_gap_only','ch_14_gap','ch_23_gap','ch_14_23_gap']

    lookup_func = lambda x: df[x].sum()
    result = list(map(lookup_func, subset_list))


    matplotlib_venn.venn3(subsets=result,set_labels=['COH 2014','COH 2023','COH gap'])

    plt.savefig(ofile)
    plt.show()


def venn3_by_source_list(infile,ofile,sources):


    df = pandas.read_csv(infile,usecols=['uid','source']).drop_duplicates()

    start_time = time.time()
    for s in sources:
        print(s)
        df[s] = df['source'].str.contains(s)
        #    #df[str(sources[s])] = df['source'].str.contains(s)
        # now df has a column for each source type, indicating whether uid is from source or not
    print(df.columns)

    set_list=[]
    for s in sources:
        s_set = set(df[df[s]].uid)
        set_list.append(s_set)

    end_time = time.time()
    print('building data for venn diagram took %f seconds'%(end_time - start_time))

    matplotlib_venn.venn3(set_list,set_labels=sources)
    plt.savefig(ofile)
    plt.show()



if __name__=='__main__':

    infile= '../processed_data/CH.concat.match_companyid.permutate.csv'
    venn_diagram_info_using_pandas(infile,'ch_sources_venn.pandas.png')
   
