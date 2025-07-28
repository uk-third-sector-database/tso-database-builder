## preprocess companies house data from the various sources, adding an iteration tag for later sorting.
## then use companies_house.py for datahandler and base constructs to sort into primary and secondary for the subspine contributions from CH.

from .base_definitions import sub_spine_entry_creator,SUB_SPINE_CSV_FIELDS
import os
import csv
import glob
from .companies_house import CompaniesHouseDataHandler
from .companies_house_API_scrape import CH_APIScrape_DataHandler
#from .companies_house_2014 import CompaniesHouse2014DataHandler
import pandas as pd


from .base import iter_csv_rows

def process_api_scrape(file,ofile):
    print(file)
    data_handler = CH_APIScrape_DataHandler()
    for new_row in filter(
        data_handler.all_filters, iter_csv_rows(file,data_handler)):
        ofile.writerows(data_handler.transform_row(new_row))


#def process_2014_data(file,ofile):
#    print(file)
#    data_handler = CompaniesHouse2014DataHandler()
#    for new_row in filter(
#        data_handler.all_filters, iter_csv_rows(file,data_handler)):
#        ofile.writerows(data_handler.transform_row(new_row))

def process_bulk_download(file,ofile,datahandler):
    # extract date from filename, eg. BasicCompanyDataAsOneFile-2023-06-01.csv
    print(file)
    year,month = os.path.basename(file).split('-')[1:3]
    date = '%s/%s'%(month,year)
    data_handler = datahandler()
    print('data_handler = ',data_handler)
    for new_row in filter(
        data_handler.all_filters, iter_csv_rows(file,data_handler)):
        rows =  data_handler.transform_row(new_row)
        for r in rows:
            if r['extraname'] == 1:
                r['iteration'] = '2000'
            else:
                r['iteration'] = date
            r.pop('extraname')

        filtered_rows = [{key: row[key] for key in ofile.fieldnames if key in row} for row in rows]
    
        ofile.writerows(filtered_rows)

def find_CIC_uids(file,companytype_field,cic_search,encode):
    print(f'Opening {file} to find CICs, using encoding {encode}')
    with open(file, 'r', newline='', encoding=encode) as infile:
        reader = csv.DictReader(infile)
        CIC_uids = []
        for row in reader:
            if row[companytype_field] == cic_search:
                if companytype_field == 'companycategory':
                    CIC_uids.append('GB-COH-'+ row['companynumber'])
                elif companytype_field == 'company_subtype':
                    CIC_uids.append('GB-COH-'+ row['company_number'])
                else:
                    try:
                        CIC_uids.append('GB-COH-'+ row['CompanyNumber'])
                    except:
                        CIC_uids.append('GB-COH-'+ row[' CompanyNumber'])

    return CIC_uids

def main_process(ofilename):
    api_scrape_file = '../raw_data/CompaniesHouse/ch_adv_scrape.csv'
    #historic_data = '../raw_data/CompaniesHouse/soton14reduced.csv'
    bulk_downloads = glob.glob('../raw_data/CompaniesHouse/BasicCompanyDataAsOneFile*csv')

    with open(ofilename, 'w+', newline='', encoding='UTF8') as outfile:
        datahandler =  CompaniesHouseDataHandler
        fields = SUB_SPINE_CSV_FIELDS + ['iteration'] + ['companytype'] + ['SIC']

        csv_writer = csv.DictWriter(outfile, fieldnames=fields)  # possibly change field list to a CH specific one?
        csv_writer.writeheader()  
        process_api_scrape(api_scrape_file,csv_writer)
        #process_2014_data(historic_data,csv_writer)
        for file in bulk_downloads:
            process_bulk_download(file,csv_writer,datahandler)

    all_CICs = set()
    for file, type_field, cic_search, encode in [#(historic_data,'companycategory','Community Interest Company','Latin-1'),
                                         (api_scrape_file,'company_subtype','community-interest-company','Latin-1')] + \
                                        [(i,'CompanyCategory','Community Interest Company','utf8') for i in bulk_downloads]:
        CIC_uids = find_CIC_uids(file,type_field,cic_search,encode)
        all_CICs.update(CIC_uids)
        print(f'found {len(CIC_uids)} CICs in {file}')
        #print(CIC_uids[:5])

    with open('all_CICs.txt','w') as f:
        f.write(f"# CICs found in files {','.join([api_scrape_file] + bulk_downloads)}\n\n") #{','.join([api_scrape_file,historic_data] + bulk_downloads)}\n\n")
        f.write('\n'.join(all_CICs))


def sic_codes_lookup(ch_file,matches_file,ofile):
    """Create a lookup file of uid:sic_codes. Map uids to spine using matches.csv """
    try:
        matches_df = pd.read_csv(matches_file,usecols=['uid','orgB_uid'])
    except ValueError as e:
        print(f'Error loading matches data from {matches_file} : {e}')
    match_dict = matches_df.groupby('orgB_uid')['uid'].first().to_dict()

    try:
        ch_data = pd.read_csv(ch_file,usecols=['uid','SIC'])
    except ValueError as e:
        print(f'Error loading companies house data from {ch_file} : {e}')
        return
    ch_data['matched_uid'] = ch_data['uid'].map(match_dict)

    ch_data['uid'] = ch_data.apply(lambda x: x['matched_uid'] if pd.notnull(x['matched_uid']) else x['uid'], axis=1)

    ch_data[['uid','SIC']].drop_duplicates().to_csv(ofile,index=False)