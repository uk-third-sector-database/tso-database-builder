# create lookup table for uid:rowid mapping for the version of the spine shared with the ONS Nov23
# create spine version with just uids, dates and Local Authority IDS for use in SRS
# create financial history file from multiple files, mapping uids to spine and summing financial data for matched orgs
# create procurement data file


import os
import sys
import csv
import pandas as pd
from datetime import datetime

POSTCODE_TO_LA_FILE = '../tso-analysis/postcode_to_la_lookup.csv'

def create_lookup(input_file, output_file):
    # check if the input file exists
    if not os.path.isfile(input_file):
        print(f"Error: The file {input_file} does not exist.")
        sys.exit(1)

    lookup = []
    # read the input file as csv, line by line
    with open(input_file, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            rowid = row['rowid']
            uid = row['uid']
            if '_' in uid:
                uids = uid.split('_')
            else:
                uids = [uid]
            for uid in uids:
                lookup.append((uid, rowid))

    lookup.sort(key=lambda x: x[0])  # sort the lookup by uid

    # write the lookup to the output file
    with open(output_file, 'w') as file:
        writer = csv.writer(file)
        writer.writerow(['uid', 'rowid'])
        for uid, rowid in lookup:
            writer.writerow([uid,rowid])

    print(f"Lookup table created successfully and saved to {output_file}")

def map_row_id_from_lookup(input_file, lookup_file, output_file):
    # check if the input file and lookup file exist
    if not os.path.isfile(input_file):
        print(f"Error: The file {input_file} does not exist.")
        sys.exit(1)
    if not os.path.isfile(lookup_file):
        print(f"Error: The file {lookup_file} does not exist.")
        sys.exit(1)

    # read the lookup file into a dictionary
    lookup = {}
    with open(lookup_file, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            lookup[row['uid']] = row['rowid']

    # read the input file and replace uid with rowid
    with open(input_file, 'r') as infile, open(output_file, 'w', newline='') as outfile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames + ['rowid']
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in reader:
            if row['uid'] in lookup:
                row['rowid'] = lookup[row['uid']]
            writer.writerow(row)

    print(f"Mapped uid to rowid successfully and saved to {output_file}")



def gen_reduced_spine(input_file, output_file):
    """Generate a reduced version of the SPINE file with only uid, LA_code, regyear, remyear."""
    pc_to_la = pd.read_csv(POSTCODE_TO_LA_FILE,usecols=['postcode','LA_code'])
    pc_to_la['postcode'] = pc_to_la['postcode'].str.replace(' ', '').str.upper()
    pc_to_la['postcode'] = pc_to_la['postcode'].str.replace('-', '')
    pc_to_la = dict(zip(pc_to_la['postcode'], pc_to_la['LA_code']))

    spine_df = pd.read_csv(input_file)
    spine_df['postcode'] = spine_df['postcode'].str.replace(' ', '').str.upper()

    spine_df['registeryear'] = pd.to_datetime(spine_df['registerdate'], errors='coerce').dt.year
    spine_df['removedyear'] = pd.to_datetime(spine_df['removeddate'], errors='coerce').dt.year
    spine_df['LA_code'] = spine_df['postcode'].apply(lambda x: pc_to_la.get(x, None))

    # reduced_spine stats
    reduced_spine_df = spine_df[['uid', 'LA_code', 'registeryear', 'removedyear']]
    reduced_spine_df = reduced_spine_df.drop_duplicates()
    print(reduced_spine_df.describe())
    print(reduced_spine_df.info())
    print(reduced_spine_df.head(10))
    print(f"Reduced SPINE file created with {len(reduced_spine_df)} unique rows. {len(reduced_spine_df[reduced_spine_df['LA_code'].isna()]['uid'])} have no LA_code")
    print(f"Spine has {len(spine_df[spine_df['postcode'].isna()])} rows with no postcode")

    pc_without_la = list(spine_df[spine_df["LA_code"].isna()]["postcode"].unique())
    print(f'{len(pc_without_la)} postcodes with no LA_code')#: {pc_without_la}')
    reduced_spine_df.to_csv(output_file, index=False)
    print(f"Reduced SPINE file saved to {output_file}")

def gen_reduced_procurement_data(input_file, matches_file, output_file):
    """Generate a reduced version of the procurement data with only uid (from field 'verifmatch')
    year, paytot, paycount, orgflag"""
    procurement_df = pd.read_csv(input_file)
    matches_df = pd.read_csv(matches_file)


    procurement_df['uid'] = procurement_df['verifmatch']

    # map uids to spine via matches.csv
    match_dict = matches_df.groupby('orgB_uid')['uid'].first().to_dict()


    procurement_df['matched_uid'] = procurement_df['uid'].map(match_dict)
    # if matched_uid is not null, replace procurement_df['uid'] with procurement_df['matched_uid']
    procurement_df['uid'] = procurement_df.apply(lambda x: x['matched_uid'] if pd.notnull(x['matched_uid']) else x['uid'], axis=1)
    # drop matched_uid column
    procurement_df.drop(columns=['matched_uid'], inplace=True)
    procurement_df.to_csv(output_file.split('.csv')[0] + '.all.csv', index=False)
    # drop rows with no uid starting 'GB-'
    procurement_df.dropna(subset=['uid'], inplace=True)
    procurement_df = procurement_df[procurement_df['uid'].str.startswith('GB-')]

    # reduced_procurement stats
    reduced_procurement_df = procurement_df[['uid', 'date', 'paytot', 'paycount', 'orgflag']]
    reduced_procurement_df = reduced_procurement_df.drop_duplicates()
    print(reduced_procurement_df.describe())
    print(reduced_procurement_df.info())
    print(reduced_procurement_df.head(10))
    print(f"Reduced Procurement file created with {len(reduced_procurement_df)} unique rows.")

    reduced_procurement_df.to_csv(output_file, index=False)
    print(f"Reduced Procurement file saved to {output_file}")

def gen_finhist_data(inputfilelist, matches_file, output_file):
    # Create a dictionary mapping orgB_uid to uid (first match only)
    matches_df = pd.read_csv(matches_file,usecols=['uid','orgA_uid','orgB_uid'])
    match_dict = matches_df.groupby('orgB_uid')['uid'].first().to_dict()

    source_lookup = {'ccew':'CHC','ccni':'NIC','oscr':'SC'}
    # read in financial data:
    # make one finhist file
    findata = pd.DataFrame()
    for f in inputfilelist:
        print(f)
        try:
            df = pd.read_csv(f,dtype={'regno':str,'fy':int,'fye':str,'inc':float,'exp':float})
            c=source_lookup[os.path.basename(f).split('-')[0]]
        except IOError as e:
            print(f'Error processing {f}: {e}')
            return
        
        df = df[~df['regno'].isna()]
        df['uid'] = df['regno'].apply(lambda x: f"GB-{c}-{x}" )

        findata = pd.concat([findata,df],axis=0)
        print(f'Concatenated files dataframe columns: {findata.columns}, and shape: {findata.shape}')

    findata.drop(columns=['regno','fye'],inplace=True)
    findata['matched_uid'] = findata['uid'].map(match_dict)
    findata.to_csv(output_file.strip('.csv')+'.nomapping.csv')
    # if matched_uid is not null, replace findata['uid'] with findata['matched_uid']
    findata['uid'] = findata.apply(lambda x: x['matched_uid'] if pd.notnull(x['matched_uid']) else x['uid'], axis=1)
    # drop matched_uid column
    findata.drop(columns=['matched_uid'], inplace=True)
    # for each uid, if there are multiple rows per year, sum the income and expenditure columns per year
    findata = findata.groupby(['uid','fy']).agg({'inc':'sum','exp':'sum'}).reset_index()
    #findata.to_csv('finhist.mapped.csv',index=False)

    findata.rename(columns={'fy':'year'}, inplace=True)

    source = {'NIC':'ccni',
              'CHC':'ccew',
              'SC':'oscr'}
    # add source column 
    findata['Regulator'] = findata['uid'].apply(lambda x: source[x.split('-')[1]])
    findata[['uid','year','inc','exp','Regulator']].to_csv(output_file,index=False)


if __name__ == '__main__':
    print('Running as script')
    print(os.getcwd())
    import click
    @click.group()
    def cli():
        ...

    @cli.command()
    @click.argument("infile")
    @click.argument("outfile")
    def create_lookup(infile, outfile):
        """
        Generate a lookup file for uid:rowid mapping, save to outfile
        """
        create_lookup(infile,outfile)

    @cli.command()
    @click.argument("infile")
    @click.argument("lookupfile")
    @click.argument("outfile")
    def map_row_id(infile, lookupfile, outfile):
        """
        Map uid to rowid for rows of infile, using the lookup file, save to outfile
        """
        map_row_id_from_lookup(infile,lookupfile,outfile)


    @cli.command()
    @click.argument("infile")
    @click.argument("outfile")
    def reduce_spine(infile, outfile):
        """
        Generate a reduced version of the SPINE file with only uid, LA_code, regyear, remyear.
        """
        gen_reduced_spine(infile,outfile)

    @cli.command()
    @click.argument("infile")
    @click.argument("matchesfile")
    @click.argument("outfile")
    def reduce_procurement(infile, matchesfile, outfile):
        """
        Generate a reduced version of the procurement data with only uid (from field 'verifmatch')
        year, paytot, paycount, orgflag
        """
        gen_reduced_procurement_data(infile, matchesfile, outfile)

    @cli.command()
    @click.argument('matches_file')
    @click.argument('output_file')
    @click.option('--inputfilelist','-i',multiple=True,help='list of input files')

    def create_financial_history(matches_file,output_file,inputfilelist):
        """
        Generate a concatenated version of the input financial history data (expects basefilenames with regulator at the start).
        Output to output_file the data with uids mapped to the spine, and totals summed for any linked orgs.
        Also output to output_file.nomapping.csv the data with original uids.
        """
        gen_finhist_data(inputfilelist, matches_file, output_file)


    cli()

"""
e.g.
 python3 spine/create_SRS_resources.py create-financial-history ../public_spine_data/public_spine.matches.csv public_spine.finhist.csv 
 -i ../raw_data/payload_data/ccew-finhist-1995-2024.csv -i ../raw_data/payload_data/oscr-finhist-2007-2024.csv -i ../raw_data/payload_data/ccni-finhist-2018-2024.csv
 
 """
