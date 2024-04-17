#---- used to add the iteration month/year (mm/yyyy) to the source data, from file name, and create one datafile. ----#

import csv
import glob
import os
from datetime import datetime

CIS_fields = ["CSNumber",
        "ServiceName",
        "ServiceType",
        "Combined_Service_",
        "CaseNumber_Combined",
        "CareService",
        "Subtype",
        "Service",
        "Address_line_1",
        "Address_line_2",
        "Address_line_3",
        "Address_line_4",
        "Service_town",
        "Service_Postcode",
        "ManagerName",
        "Council_Area_Name",
        "Health_Board_Name",
        "DateReg",
        "Iteration"]

def fix_care_inspectorate_files():
    # Pre-process the raw files to include the source date (found in filename) as a field
    raw_files = glob.glob('../raw_data/CareInspectScot/MDSF_data*.csv')
    print(raw_files)
    output_file = '../raw_data/CareInspectScot.all.csv'
    
    with open(output_file, 'w+', newline='', encoding='Latin-1') as outfile:
        
        csv_writer = csv.DictWriter(outfile, fieldnames=CIS_fields)  
        csv_writer.writeheader()  
        
        for file in raw_files:
            date = os.path.basename(file).split('MDSF_data_')[-1].strip('.csv')
            with open(file, 'r', newline='', encoding='Latin-1') as infile:
                csv_reader = csv.DictReader(infile)
                v = ['CSNumber', 'CaseNumber','ï»¿CSNumber']
                for i in v:
                    if i in csv_reader.fieldnames:
                        id_field = i
                
                v = ['ServiceType','Service Type']
                for i in v:
                    if i in csv_reader.fieldnames:
                        servicetype = i

                for row in csv_reader:
                    
                    row['CSNumber'] = row[id_field]
                    row['ServiceType'] = row[servicetype]
                    row['Iteration'] = date
                    for key in CIS_fields:
                        row.setdefault(key, '') 
                    row = {key: row[key] for key in CIS_fields}
                    
                    csv_writer.writerow(row)
                        
            print(f"iteration {date} added to file {output_file}")



co_op_fields = [
'CUK Organisation ID',
'Registered Number',
'Registrar',
'Registered Name',
'Trading Name',
'Legal Form',
'Registered Street',
'Registered City',
'Registered State/Province',
'Registered Postcode',
'Incorporation Date',
'Dissolved Date',
'Iteration'
]

def fix_coops_files():
    # Pre-process the raw files to include the source date (found in filename) as a field
    raw_files = glob.glob('../raw_data/co_ops/*.csv')
    print(raw_files)
    output_file = '../raw_data/co_ops.all.csv'
    
    with open(output_file, 'w+', newline='', encoding='UTF8') as outfile:
        
        csv_writer = csv.DictWriter(outfile, fieldnames=co_op_fields)  # Create DictWriter object
        csv_writer.writeheader()  # Write header to output file
        
        # Iterate over each raw file
        for file in raw_files:
            year,month = os.path.basename(file).strip('.csv').split('_')[-2:]
            date = '%s/%s'%(month,year)
            with open(file, 'r', newline='', encoding='UTF8') as infile:
                csv_reader = csv.DictReader(infile)

                for row in csv_reader:
                    
                    row['Iteration'] = date
                    for key in co_op_fields:
                        row.setdefault(key, '') 
                    row = {key: row[key].replace('\n', ',').replace('\r\n', ',').replace('\r', ',').replace('^M', ',').replace(',,',',') for key in co_op_fields}
                        
                    csv_writer.writerow(row)
                        
            print(f"iteration {date} added to file {output_file}")


mutuals_fields_1 = [
'societynumber',
'organisationname',
'address',
'source',
'uid',
'normalisedname',
'companyid',
'housenumber',
'city',
'localauthority',
'postcode'],

mutuals_fields_2 = [
'Full Registration Number',
'Society Name',
'Society Address',
'Registration Date',
'Deregistration Date',
'Iteration'
]

def fix_mutuals_files():
    # Pre-process the raw files to include the source date (found in filename) as a field, 
    raw_files = glob.glob('../raw_data/mutuals/*.csv')
    print(raw_files)
    output_file = '../raw_data/mutuals.all.csv'
    encoding = 'Latin-1'
    
    with open(output_file, 'w+', newline='', encoding=encoding) as outfile:
        
        csv_writer = csv.DictWriter(outfile, fieldnames=mutuals_fields_2)  # Create DictWriter object
        csv_writer.writeheader()  # Write header to output file
        
        # Iterate over each raw file
        for file in raw_files:
            print(file)
            year,month = os.path.basename(file).strip('.csv').split('-')[-2:]
            date = '%s/%s'%(month,year)
            with open(file, 'r', newline='', encoding=encoding) as infile:
                csv_reader = csv.DictReader(infile)

                for row in csv_reader:
                    new_row = {}
                    row['Iteration'] = date
                    if 'societynumber' in csv_reader.fieldnames:
                        # map from mutuals_fields_1 to mutuals_fields_2
                        new_row['Full Registration Number'] = row['societynumber']
                        new_row['Society Name'] = row['organisationname']
                        new_row['Society Address'] = row['address']
                        new_row['Registration Date'] = ''
                        new_row['Deregistration Date'] = ''
                        new_row['Iteration'] = date

                    else:
                        row['Full Registration Number'] = row['Full Registation Number']
                        for key in mutuals_fields_2:
                            new_row.setdefault(key, '') 
                        new_row = {key: row[key] for key in mutuals_fields_2}
                    
                    csv_writer.writerow(new_row)
                        
            print(f"iteration {date} added to file {output_file}")


ScHR_fields = [
'Financial Year',
'Reg No',
'Social Landlord',
'Constitution',
'Clients',
'Landlord type',
'Settlement',
'National Operator',
'Iteration'
]

def fix_ScotHousingReg_files():
    # Pre-process the raw files to include the source date (found in filename) as a field
    raw_files = glob.glob('../raw_data/ScotHousingReg/*.csv')
    print(raw_files)
    output_file = '../raw_data/ScotHousingReg.all.csv'
    
    with open(output_file, 'w+', newline='', encoding='Latin-1') as outfile:
        
        csv_writer = csv.DictWriter(outfile, fieldnames=ScHR_fields)  
        csv_writer.writeheader()  
        for file in raw_files:
            print(file)
            date = os.path.basename(file).split('-')[-1].strip('.csv')
            
            with open(file, 'r', newline='', encoding='Latin-1') as infile:
                csv_reader = csv.DictReader(infile)

                for row in csv_reader:
                    
                    row['Iteration'] = date
                    for key in ScHR_fields:
                        row.setdefault(key, '') 
                    row = {key: row[key]for key in ScHR_fields}
                        
                    csv_writer.writerow(row)
                        
            print(f"iteration {date} added to file {output_file}")

CQC_fields = [
'Name',
'Also known as',
'Address',
'Postcode',
'Provider name',
'Local authority',
'CQC Provider ID (for office use only)',
'Iteration'
]
def fix_CQC_files():
    # Pre-process the raw files to include the source date (found in filename) as a field
    raw_files = glob.glob('../raw_data/CareQualityCommission/*__.csv')
    print(raw_files)
    output_file = '../raw_data/CareQualityCommission.all.csv'
    
    with open(output_file, 'w+', newline='', encoding='UTF8') as outfile:
        
        csv_writer = csv.DictWriter(outfile, fieldnames=CQC_fields)  
        csv_writer.writeheader()  
        for file in raw_files:
            print(file)
            d,m,y = os.path.basename(file).split('_')[:3]
            date_object = datetime.strptime('%s %s %s'%(d,m,y), "%d %B %Y")
            date = date_object.strftime("%m/%Y")

            with open(file, 'r', newline='', encoding='UTF8',) as infile:
                csv_reader = csv.DictReader(infile)

                for row in csv_reader:
                    
                    row['Iteration'] = date
                    for key in CQC_fields:
                        row.setdefault(key, '') 
                    row = {key: row[key]for key in CQC_fields}
                        
                    csv_writer.writerow(row)
                        
            print(f"iteration {date} added to file {output_file}")



if __name__ == '__main__':
    #fix_coops_files()
    #fix_care_inspectorate_files()
    #fix_mutuals_files()
    #fix_ScotHousingReg_files()
    fix_CQC_files()

