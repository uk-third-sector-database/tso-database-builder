# create lookup table for uid:rowid mapping for the version of the spine shared with the ONS Nov23

# use this lookup to create versions of spine and payload data with original rowid in place of uid

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
    print(f'{len(pc_without_la)} postcodes with no LA_code: {pc_without_la}')
    reduced_spine_df.to_csv(output_file, index=False)
    print(f"Reduced SPINE file saved to {output_file}")

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

    cli()


