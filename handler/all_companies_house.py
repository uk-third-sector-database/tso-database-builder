## preprocess companies house data from the various sources, adding an iteration tag for later sorting.
## then use companies_house.py for datahandler and base constructs to sort into primary and secondary for the subspine contributions from CH.

from .base_definitions import sub_spine_entry_creator,SUB_SPINE_CSV_FIELDS
import os
import csv
import glob
from .companies_house import CompaniesHouseDataHandler
from .companies_house_gap_decade import CompaniesHouseGapDataHandler
from .companies_house_2014 import CompaniesHouse2014DataHandler


from .base import iter_csv_rows

def process_api_scrape(file,ofile):
    print(file)
    data_handler = CompaniesHouseGapDataHandler()
    for new_row in filter(
        data_handler.all_filters, iter_csv_rows(file,data_handler)):
        ofile.writerows(data_handler.transform_row(new_row))


def process_2014_data(file,ofile):
    print(file)
    data_handler = CompaniesHouse2014DataHandler()
    for new_row in filter(
        data_handler.all_filters, iter_csv_rows(file,data_handler)):
        ofile.writerows(data_handler.transform_row(new_row))

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




def main_process(ofilename):
    # open outputfile 'w+ as csvwriter
    with open(ofilename, 'w+', newline='', encoding='UTF8') as outfile:


        datahandler =  CompaniesHouseDataHandler
        fields = SUB_SPINE_CSV_FIELDS + ['iteration'] + ['companytype']
        
        csv_writer = csv.DictWriter(outfile, fieldnames=fields)  # possibly change field list to a CH specific one?
        csv_writer.writeheader()  

        api_scrape_file = '../raw_data/ch_adv_scrape.csv'
        historic_data = '../raw_data/soton14reduced.csv'
        bulk_downloads = glob.glob('../raw_data/BasicCompanyDataAsOneFile*csv')

        process_api_scrape(api_scrape_file,csv_writer)
        process_2014_data(historic_data,csv_writer)


        for file in bulk_downloads:
            process_bulk_download(file,csv_writer,datahandler)


