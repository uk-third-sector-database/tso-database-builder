import glob
import csv
from datetime import datetime
import os
import pandas as pd
import re
from datetime import datetime

from .base import sort_encoding_issue

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

ccni_fields = [
    'uid',
    'charitynumber',
    'organisationname',
    'normalisedname',
    'companyid',
    'housenumber',
    'address',
    'city',
    'localauthority',
    'postcode',
    'registerdate',
    'source',
    'iteration'
]

def find_postcode(address_string:str,name_str:str):
    #remove name from address string:
    address_string = address_string.replace(name_str,'')
    '''find postcode in address string'''
    postcode  = address_string.split(',')[-1].strip()

    # check if these are of the form 'XX?99? 9XX'
    postcode_regex = re.compile(r"^(GIR 0AA|[A-Z]{1,2}[0-9][0-9A-Z]? ?[0-9][A-Z]{2})$", re.IGNORECASE)

    if not postcode_regex.match(postcode):
        postcode = ''       
    else:
        postcode = postcode.strip()
        address_string = address_string.replace(postcode,'')

    address_string = ', '.join([a.strip() for a in address_string.strip(', ').split(',') if a])
    return address_string,postcode




def process_ccni():
    raw_files = glob.glob('../raw_data/ccni/ccni-charitydetails_*.csv')
    base_file = '../raw_data/ccni/ccni_spine.csv'
    output_file = '../raw_data/ccni.all.csv'


    with open(output_file, 'w+', newline='', encoding='UTF8') as outfile:
        csv_writer = csv.DictWriter(outfile, fieldnames=ccni_fields)
        csv_writer.writeheader()
# file date format: 2025_01_29_14_23_47
        
        with open(base_file, 'r', newline='', encoding='utf-8-sig') as basefile:
            csv_reader = csv.DictReader(basefile)

            lc = 0
            for row in csv_reader:
                new_row = {key:row[key] for key in ccni_fields if key in row}
                address,postcode = find_postcode(row['address'],row['organisationname'])
                new_row['address'] = address
                new_row['postcode'] = postcode
                new_row['iteration'] = '2024'
                csv_writer.writerow(new_row)
                lc +=1
                
            print(f'copied {lc} lines from {base_file} to {output_file}')

        for file in raw_files:
            lc = 0
            date = os.path.basename(file).split('-charitydetails_')[1].strip('.csv')
            date_obj = datetime.strptime(date, '%Y_%m_%d_%H_%M_%S')
            iteration_date = date_obj.strftime('%m/%Y')

            with open(file, 'r', newline='', encoding='Latin-1') as infile:
                csv_reader = csv.DictReader(infile)
                for row in csv_reader:
                    row = {sort_encoding_issue(k):sort_encoding_issue(v) for k,v in row.items()}
                    address,postcode = find_postcode(row['Public address'],row['Charity name'])
                    new_row = {key:'' for key in ccni_fields}
                    new_row['iteration'] = iteration_date
                    new_row['charitynumber'] = row['Reg charity number']
                    new_row['organisationname'] = row['Charity name']
                    new_row['address'] = address
                    new_row['postcode'] = postcode
                    new_row['registerdate'] = row['Date registered']
                    new_row['iteration'] = iteration_date
                    new_row['source'] = 'CCNI'
                    csv_writer.writerow(new_row)
                    lc +=1


                print(f'copied {lc} lines from {file} to {output_file}')


ccew_fields = ['uid', 'charitynumber', 'organisationname', 'normalisedname',
       'companyid', 'housenumber', 'addressline1', 'addressline2',
       'addressline3', 'addressline4', 'addressline5', 'city',
       'localauthority', 'postcode', 'registerdate', 'removeddate',
       'name_origin', 'primary_name', 'address_origin', 'primary_address',
       'regdate_origin', 'remdate_origin', 'iteration', 'source', 'cqc_reg',
       ]#'dummy', 'dummy2']

def process_ccew():
    
    def formatdate(datestr):
        try:
            d = datetime.strptime(datestr,'%Y-%m-%dT%H:%M:%S')
            return d.strftime('%d%b%Y')
        except ValueError:
            return ''


    raw_files = glob.glob('../raw_data/ccew/ccew-publicextract.*.csv')
    base_file = '../raw_data/ccew/ccew_spine_public.csv'
    output_file = '../raw_data/ccew.all.csv'

    with open(output_file,'w+', newline='', encoding='UTF8') as outfile:
        csv_writer = csv.DictWriter(outfile, fieldnames=ccew_fields)
        csv_writer.writeheader()

        with open(base_file, 'r', newline='', encoding='utf-8-sig') as basefile:
            csv_reader = csv.DictReader(basefile)
            lc=0
            for row in csv_reader:
                new_row = {key:row[key] for key in ccew_fields}
                csv_writer.writerow(new_row)
                lc +=1
            print(f'copied {lc} lines from {base_file} to {output_file}')
        
        for file in raw_files:
            lc=0
            date = os.path.basename(file).split('ccew-publicextract.')[1].strip('.csv')
            date_obj = datetime.strptime(date, '%b%Y')
            iteration_date = date_obj.strftime('%m/%Y')

            with open(file,'r', newline='', encoding='UTF8') as infile:
                csv_reader = csv.DictReader(infile)
                for row in csv_reader:
                    new_row = {key:'' for key in ccew_fields}
                    new_row['iteration'] = iteration_date
                    new_row['charitynumber'] = row['registered_charity_number']
                    new_row['organisationname'] = row['charity_name']
                    new_row['companyid'] = row['charity_company_registration_number']
                    new_row['addressline1'] = row['charity_contact_address1']
                    new_row['addressline2'] = row['charity_contact_address2']
                    new_row['addressline3'] = row['charity_contact_address3']
                    new_row['addressline4'] = row['charity_contact_address4']
                    new_row['addressline5'] = row['charity_contact_address5']
                    new_row['city'] = ''
                    new_row['postcode'] = row['charity_contact_postcode']
                    new_row['registerdate'] = formatdate(row['date_of_registration'])
                    new_row['removeddate'] = formatdate(row['date_of_removal'])
                    new_row['source'] = 'CCEW'
                    new_row['regdate_origin'] = iteration_date
                    new_row['remdate_origin'] = iteration_date

                    csv_writer.writerow(new_row)
                    lc +=1
                print(f'copied {lc} lines from {file} to {output_file}, iteration date = {iteration_date}')

if __name__ == '__main__':
#    process_oscr()
   # process_ccni()
   process_ccew()

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

'''
CCNI download fields:
Reg charity number
Charity name
Date registered
Status
Date for financial year ending
Total income
Total spending
Charitable spending
Income generation and governance
Public address
Website
Email
Telephone
Company number
What the charity does
Who the charity helps
How the charity works
Charitable purposes
Other name
Type of governing document
Financial period start
Financial period end
Total income. Previous financial period.
Employed staff
UK and Ireland volunteers
Income from donations and legacies
Income from charitable activities
Income from other trading activities
Income from investments
Income from other
Total income and endowments
Expenditure on Raising funds
Expenditure on Charitable activities
Expenditure on Governance
Expenditure on Other
Total expenditure
Assets and liabilities - Total fixed assets
Total net assets and liabilities
'''

'''
CCEW download fields:
['date_of_extract', 'organisation_number', 'registered_charity_number',
'linked_charity_number', 'charity_name', 'charity_type',
'charity_registration_status', 'date_of_registration',
'date_of_removal', 'charity_reporting_status',
'latest_acc_fin_period_start_date', 'latest_acc_fin_period_end_date',
'latest_income', 'latest_expenditure', 'charity_contact_address1',
'charity_contact_address2', 'charity_contact_address3',
'charity_contact_address4', 'charity_contact_address5',
'charity_contact_postcode', 'charity_contact_phone',
'charity_contact_email', 'charity_contact_web',
'charity_company_registration_number', 'charity_insolvent',
'charity_in_administration', 'charity_previously_excepted',
'charity_is_cdf_or_cif', 'charity_is_cio', 'cio_is_dissolved',
'date_cio_dissolution_notice', 'charity_activities', 'charity_gift_aid',
'charity_has_land']
'''
'''
NOTE: code used to convert json files to csv:
for file in ['../../raw_data/ccew/ccew-publicextract.aug2024.json','../../raw_data/ccew/ccew-publicextract.feb2025.json','../../raw_data/ccew/ccew-publicextract.jan2025.json']:
    with open(file, 'r', encoding='utf-8-sig') as f:
        data = json.load(f)  # Load the JSON data
        df = pd.DataFrame(data)  # Convert to DataFrame

    df.to_csv(file.replace('.json','.csv'), index=False)
'''