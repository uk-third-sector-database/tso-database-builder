import glob
import csv
from datetime import datetime
import os
import pandas as pd

# create sub-spine level input files for charity regulators. Include iteration',
#  created from filename for new data.

oscr_fields = [
    'uid',
    'charitynumber',
    'organisationname',
    'normalisedname',
    'companyid',
    'address',
    'housenumber',
    'addressline1',
    'addressline2',
    'addressline3',
    'addressline4',
    'addressline5',
    'addressline6',
    'addressline7',
    'addressline8',
    'city',
    'localauthority',
    'postcode',
    'registerdate',
    'removeddate',
    'name_origin',
    'iteration',
    'charitynumber_2012',
    'companyid1_2012',
    'companyid2_2012',
    'companyid3_2012',
    'source',
    'crossborder'
]

def process_oscr():
    raw_files = glob.glob('../raw_data/oscr/CharityExport-*.csv')
    base_file = '../raw_data/oscr/oscr_spine_public.csv'
    output_file = '../raw_data/oscr.all.csv'
    linkage_ofile = '../raw_data/oscr.linkage.csv'

    with open(output_file, 'w+', newline='', encoding='UTF8') as outfile, \
        open(linkage_ofile, 'w+', newline='', encoding='UTF8') as linkagefile:
        csv_writer = csv.DictWriter(outfile, fieldnames=oscr_fields)
        csv_writer.writeheader()

        linkage_csv_writer = csv.DictWriter(linkagefile, 
                                            fieldnames=['org_id_a','org_id_b'])
        linkage_csv_writer.writeheader()
        
        with open(base_file, 'r', newline='', encoding='utf-8-sig') as basefile:
            csv_reader = csv.DictReader(basefile)

            lc = 0
            for row in csv_reader:
                new_row = {key:row[key] for key in oscr_fields}
                csv_writer.writerow(new_row)
                lc +=1
                link_row = {key:'' for key in ['org_id_a','org_id_b']}
                # Create linked_char only if charitynumber_2012 exists
                linked_char = f"GB-SC-{row.get('charitynumber_2012', '')}" if row.get('charitynumber_2012', '') else ''
                linked_ch = [row[i] for i in ['companyid1_2012', 'companyid2_2012', 'companyid3_2012'] if row.get(i)]
                linked_orgs = [f'GB-COH-{i}' for i in linked_ch if i] + ([linked_char] if linked_char else [])

                for org in linked_orgs:
                    link_row['org_id_a'] = f"GB-SC-{row['charitynumber']}"
                    link_row['org_id_b'] = org
                    linkage_csv_writer.writerow(link_row)
                
            print(f'copied {lc} lines from {base_file} to {output_file}')

        # deduplicate linkage_csv
        df = pd.read_csv(linkage_ofile)
        df_deduplicated = df.drop_duplicates(subset=['org_id_a', 'org_id_b'])
        print(f"A total of {len(df_deduplicated)} linkages found for {len(df_deduplicated['org_id_a'].unique())} orgs")
        df_deduplicated.to_csv(linkage_ofile, index=False)

        for file in raw_files:
            lc = 0
            date = os.path.basename(file).split('CharityExport-')[1].strip('.csv')

            date_obj = datetime.strptime(date.strip('Removed-'), '%d-%b-%Y')
            iteration_date = date_obj.strftime('%m/%Y')
            
            with open(file, 'r', newline='', encoding='UTF8') as infile:
                csv_reader = csv.DictReader(infile)
                for row in csv_reader:
                    new_row = {key:'' for key in oscr_fields}
                    new_row['iteration'] = iteration_date
                    new_row['charitynumber'] = row['Charity Number']
                    new_row['organisationname'] = row['Charity Name']
                    new_row['address'] = row['Principal Office/Trustees Address']
                    new_row['postcode'] = row['Postcode']
                    new_row['registerdate'] = row['Registered Date']
                    new_row['name_origin'] = f'{iteration_date} Name'
                    new_row['iteration'] = iteration_date
                    new_row['source'] = 'OSCR'
                    new_row['crossborder'] = 1 if row['Regulatory Type']=='Cross Border' else 0
                    if 'Ceased Date' in row:
                        new_row['removeddate'] = row['Ceased Date']
                    csv_writer.writerow(new_row)
                    lc +=1

                    # also add new_row if there is a 'Known As' name:
                    if row['Known As']:
                        new_row = {key:'' for key in oscr_fields}
                        new_row['iteration'] = iteration_date
                        new_row['charitynumber'] = row['Charity Number']
                        new_row['organisationname'] = row['Known As']
                        new_row['name_origin'] = f'{iteration_date} Known As'
                        csv_writer.writerow(new_row)
                        lc +=1
                print(f'copied {lc} lines from {file} to {output_file}')

            print(f"iteration {iteration_date} added to file {output_file}")


if __name__ == '__main__':
    process_oscr()


'''
OSCR download fields:

'Charity Number',
'Charity Name',
'Registered Date',
'Known As',
'Charity Status',
'Notes',
'Postcode',
'Constitutional Form',
'Previous Constitutional Form 1',
'Geographical Spread',
'Main Operating Location',
'Purposes',
'Beneficiaries',
'Activities',
'Objectives',
'Principal Office/Trustees Address',
'Website',
'Most recent year income',
'Most recent year expenditure',
'Mailing cycle',
'Year End',
'Date annual return received',
' Next year end date',
' Donations and legacies income',
'Charitable activities income',
'Other trading activities income',
'Investments income',
'Other income',
'Raising funds spending',
'Charitable activities spending',
'Other spending',
'Parent charity name',
'Parent charity number',
'Parent charity country of registration',
'Designated religious body',
'Regulatory Type'
'''