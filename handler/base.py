import csv
import string

from .base_definitions import SUB_SPINE_CSV_FIELDS,EXTRA_DETAILS_CSV_FIELDS,ORG_ID_MAPPING
from spine.wrangling import dict_indexed_by_field


class DataHandler:
    fileencoding = None
    names = None
    tmp_fields = None
    ftc_code = None
        
    def all_filters(self, row: dict) -> bool:
        raise NotImplementedError()

    def transform_row(self, row: dict) -> list[dict]:
        spine_rows = []
        for name in self.names:
            spine_rows.append(self.format_row(name,row))
        return spine_rows

    
    def map_date(self,datestr):
        raise NotImplementedError()
    
    def sort_address_fields(self,row:dict):
        address_fields = ["housenumber","addressline1",
        "addressline2","addressline3","addressline4","addressline5",
        "addressline6","addressline7","addressline8"]

        
        fulladdress = []

        fulladdress.extend(row[field].strip() 
                           for field in address_fields 
                           if (field in row) and (row[field] != '') 
                           and (row[field] not in fulladdress))

        #try:
        #    print(f'"{fulladdress[-2]}","{fulladdress[-1]}",')
        #except:
        #    pass

        fulladdress_str = ', '.join(fulladdress)
        try: fulladdress_str = fulladdress_str.split(row['postcode'].strip())[0]
        except ValueError: pass
        if "fulladdress" in row:
            row["fulladdress"] = row["fulladdress"].upper()
            
        else:
            row['fulladdress'] = fulladdress_str.upper()
        row['city']=row['city'].upper()
        
        [row.pop(f, None) for f in address_fields] #remove old address fields

        row['normalisedname'] = normalizer(row['organisationname'])

        if not row['uid']: row['uid'] = 'GB-%s-%s'%(ORG_ID_MAPPING[row['source']],row['charitynumber'])

        try: row['fulladdress'] = row['fulladdress'].split(row['city'])[0].strip().rstrip(',')
        except ValueError: pass

        row['fulladdress'] = row['fulladdress'].replace(' ,',',').strip(', ').strip('.')

    def combine_org_details_per_source(self,rows:list):
        '''
        Called by compress_org_details. Takes rows of data with
        the same uid and returns a row for the primary data table in sub-spine format, 
        and rows for supplementary table.
        '''
        raise NotImplementedError()



def iter_csv_rows(filename,DataHandler):
    encoding=DataHandler.fileencoding
    with open(filename, newline="", encoding=encoding) as csvfile:
        reader = csv.DictReader(csvfile)
        DataHandler.names = DataHandler.find_names(reader.fieldnames)
        for row in reader:
            yield row


def normalizer(name, norm_dict=None):
    ''' normalise entity names with manually curated dict'''
    norm_dict={}
    if isinstance(name, str):
        name = name.upper()
        for key, value in norm_dict.items():
            name = name.replace(key, value)
        name = name.replace(r"\(.*\)", "")  # remove brackets
        name = "".join(l for l in name if l not in string.punctuation) # keep text other than punctuation
        name = ' '.join(name.split()).strip()
        return name
    return None


def do_csv_processing(input_csv_filename, 
                      output_csv_filename, 
                      data_handler: DataHandler):
    '''Called by cli.py process-source. Creates two csv files per source, organising
    the data as primary and supplementary. Calls datahandler-specific functions
     transform_row (per row) to create a temporary intermediate file by processing input data
     row by row, and compress_org_details which performs the sorting algorithm on the input data
      and sends the output to two final files '''
    
    intermediate_ofile = output_csv_filename.split('.csv')[0] + '.tmp.csv'
    
    processed_rows = 0
    print(f'Processing file {input_csv_filename}')
    
    with open(intermediate_ofile, "w+", encoding='UTF8', newline="") as csvfile:
        writer = csv.DictWriter(
            csvfile, fieldnames=SUB_SPINE_CSV_FIELDS+data_handler.tmp_fields, extrasaction="ignore"
        )
        writer.writeheader()
        for new_row in filter(
            data_handler.all_filters, iter_csv_rows(input_csv_filename,data_handler)):
            processed_rows += 1
            writer.writerows(data_handler.transform_row(new_row))
    
    print(f"Intermediate process complete, {processed_rows} lines written to {intermediate_ofile}\n")
    
    compress_org_details(intermediate_ofile,output_csv_filename,data_handler)
    



def compress_org_details(csv_in, 
                         spine_csv_out, 
                         data_handler: DataHandler):
    
    '''run as part of initial processing of an input
    required as some sources have details across multiple lines, which need to be processed
    on a per-source basis.
    Outputs the two csvs - spine and supplementary - for this source (DataHandler)
    '''
    details_csv_out = spine_csv_out.split('.csv')[0] + '.supplementary.csv'

    print('datahandler: ',data_handler)

    # create dictionary key'd by uid
    print(f'Running handler.base.compress_org_details with file {csv_in}')
    uid_dict = dict_indexed_by_field(csv_in,'uid')
    
    

    # for each uid, if more than one record, find unique names and addresses
    # and write line to csv_out, with additional data to details_csv_out
    with open(spine_csv_out,'w+',newline='') as spine_csvfile,  open(details_csv_out, 'w+', newline='') as details_csvfile:
        spine_writer = csv.DictWriter(spine_csvfile, fieldnames=SUB_SPINE_CSV_FIELDS+data_handler.tmp_fields, extrasaction='ignore')
        extras_writer = csv.DictWriter(details_csvfile, fieldnames=EXTRA_DETAILS_CSV_FIELDS, extrasaction='ignore')
        
        spine_writer.writeheader()
        extras_writer.writeheader()  

        for uid in uid_dict.keys():

            if not uid.split('-')[-1]:
                # uid doesn't have id attached
                for line in uid_dict[uid]:
                    print(f'in handler.base.compress_org_details. Line has truncated uid: {line}')
                    spine_writer.writerow(line)
            elif len(uid_dict[uid]) > 1: # more than one record with this uid - sort primary and secondary data
                try:
                    sub_spine_data,extra_data = data_handler.combine_org_details_per_source(uid_dict[uid])
                    spine_writer.writerow(sub_spine_data)
                    extras_writer.writerows(extra_data)
                except ValueError as e:
                    print(f'Error with combining org details for uid {uid}: {e}')
            else: # only one record with this uid - write directly
                spine_writer.writerow(uid_dict[uid][0])

    print(f'Completed handler.base.compress_org_details - output in {spine_csv_out} and {details_csv_out}')