# create lookup table for uid:rowid mapping for the version of the spine shared with the ONS Nov23

# use this lookup to create versions of spine and payload data with original rowid in place of uid

import os
import sys
import csv

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



if __name__ == '__main__':
    print('Running as script')
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

    cli()