import csv
import string
from datetime import datetime
import re
import pandas as pd
import os

from .base_definitions import SUB_SPINE_CSV_FIELDS,EXTRA_DETAILS_CSV_FIELDS,ORG_ID_MAPPING,sub_spine_entry_creator,extra_csv_entry_creator

    
def dict_indexed_by_field(csv_in,fieldname):
    field_dict={}
    with open(csv_in,'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if not fieldname in row.keys():
                print(f'Error: no field "{fieldname}" in row keys ({row.keys()})')
            
            if not row[fieldname] in field_dict.keys():
                field_dict[row[fieldname]]=[row]
            else:
                field_dict[row[fieldname]].append(row)
    return field_dict

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
            #if row[name]:
            # Must allow for null names due to formatting of charity data - extra info on rows with no name
            new_row = self.format_row(name,row)
            if not new_row in spine_rows:
                spine_rows.append(new_row)
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
        
        if "fulladdress" in row:
            row["fulladdress"] = row["fulladdress"].upper()
            
        else:
            row['fulladdress'] = fulladdress_str.upper()

        try: row['fulladdress'] = row['fulladdress'].split(row['postcode'].strip())[0]
        except ValueError: pass
        
        row['city']=row['city'].upper()
        
        [row.pop(f, None) for f in address_fields] #remove old address fields

        row['normalisedname'] = normalizer(row['organisationname'])

        if not row['uid']: row['uid'] = 'GB-%s-%s'%(ORG_ID_MAPPING[row['source']],row['charitynumber'])

        try: row['fulladdress'] = row['fulladdress'].split(row['city'])[0].strip().rstrip(',')
        except ValueError: pass

        row['fulladdress'] = row['fulladdress'].replace(' ,',',').strip(', ').strip('.')



    def find_primary_info(self,details_list):
        '''details_list is list of tuples (fulladdress,city,postcode,iteration) | (name,normname,iteration)
        and primary details are that found in most recent iteration'''
        details_list = list(details_list) 
        primary = tuple('' for _ in range(len(details_list[0])-1))
        date = datetime.strptime('01/01/1900','%d/%m/%Y')
        extra_details = set()
        #print(f'\n\n in find_primary_info. input = {details_list}')
        for item in details_list:
            data_tuple = item[:-1]
            if len([i for i in data_tuple if i]) == 0:
                continue
            iteration = item[-1]
            
            if iteration:
                #print(f'iteration = {iteration}, date = {date}')
                if len(iteration) == 4:
                    iteration = datetime.strptime(iteration,'%Y')
                else:
                    iteration = datetime.strptime(iteration,'%m/%Y')
                #print(f'iteration > date = {iteration > date}')
                if iteration > date:
                    
                    date = iteration
                    primary = data_tuple
            extra_details.add(data_tuple)
        extra_details = [i for i in extra_details if i != primary and i != ('','','')]
        #print(f'primary = {primary}')
        #print(f'extra = {extra_details}')
        return primary, extra_details



    def combine_org_details_per_source(self, rows: list):
        ''' use data iteration to find primary address and primary name. 
        Uses earliest date for registration and 
        latest for dissolution (though could change this to use the dates in 
        the most recent iteration instead) '''

    
        def fix_dates_set(datesset, order):
            ret = list(datesset)
            ret = [i for i in ret if i !='']
            ret.sort()
            if ret:
                primary = ret[order]
                extra_dates = [i for i in ret if i != primary]
            else:
                return '',''
            return primary,extra_dates

        names = set()
        addresses = set()
        regdates = set()
        remdates = set()
        for r in rows:
            for field in self.tmp_fields:
                if not field in r.keys(): r[field] = ''
            try:
                n = (r['organisationname'],r['normalisedname'],r['iteration'])
                a = (r['fulladdress'],r['city'],r['postcode'],r['iteration'])
                reg = r['registerdate']
                dis = r['removeddate']
            except KeyError as e:
                print(f'KeyError searching for names, addresses and/or dates in row {r} : {e}\n')
                return []


            for var in [(n,names),(a,addresses),(reg,regdates),(dis,remdates)]:
                var[1].add(var[0])

        primary_name, extra_names = self.find_primary_info(names)
        primary_address, extra_addresses = self.find_primary_info(addresses)
        primary_regdate, extra_regdates = fix_dates_set(regdates,0) # use earliest registration date
        primary_remdate, extra_remdates = fix_dates_set(remdates,-1) # use latest removal date

        new_sub_spine_row = sub_spine_entry_creator(
            {'uid' : r['uid'],
            "id_in_source" : r['id_in_source'],
            "companyid" : r['companyid'],
            "source" : r['source'],})

        if primary_name:
            new_sub_spine_row["organisationname"] =  primary_name[0]
            new_sub_spine_row["normalisedname"] =  primary_name[1]
        if primary_address:
            new_sub_spine_row["fulladdress"] =  primary_address[0]
            new_sub_spine_row["city"] =  primary_address[1]
            new_sub_spine_row["postcode"] =  primary_address[2]
        if primary_regdate:
            new_sub_spine_row["registerdate"] =  primary_regdate 
        if primary_remdate:
            new_sub_spine_row["removeddate"] =  primary_remdate 
        new_extras_rows = []
        for name in extra_names:
            new_extras_rows.append(
                extra_csv_entry_creator({
                "uid" : r['uid'],
                "organisationname" : name[0],
                "normalisedname" : name[1],
                }))
        for address in extra_addresses:
            new_extras_rows.append(
                extra_csv_entry_creator({
                "uid" : r['uid'],
                "fulladdress" : address[0],
                "city" : address[1],
                "postcode" : address[2]
                }))
        for date in extra_regdates:
            new_extras_rows.append(
                extra_csv_entry_creator({
                "uid" : r['uid'],
                "registerdate" : date,
            }))
        for date in extra_remdates:
            new_extras_rows.append(
                extra_csv_entry_creator({
                "uid" : r['uid'],
                "removeddate" : date
            }))

        for entry in new_extras_rows:
            entry['source'] = r['source']
            
        return new_sub_spine_row, new_extras_rows



def sort_encoding_issue(st):
    while not st.isascii():
        try:
            st = st.encode('latin-1').decode('utf-8')
            print(st)
        except (UnicodeEncodeError, UnicodeDecodeError) as e:
            break
    return st
    


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
        name = name.replace(r"\(.*\)", " ")  # remove brackets
        name = name.replace(r"&", "AND")  
        name = name.replace(r"\+", "AND")  
        name = re.sub(r"(?<=\w)'(?=\w)", '', name)
        name = re.sub(r"(?<=\w)\.(?=\w)", '', name)
        for punct in string.punctuation:
            name = name.replace(punct, ' ')

        # Replace apostrophe with an empty string
        

        #name = "".join(l for l in name if l not in string.punctuation) # keep text other than punctuation
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
    
    '''run as part of initial processing of an input;
    required as some sources have details across multiple lines, which need to be processed
    on a per-source basis.
    Outputs the two csvs - spine and supplementary - for this source (DataHandler)
    '''
    details_csv_out = spine_csv_out.split('.csv')[0] + '.supplementary.csv'

       # create dictionary key'd by uid
    print(f'Running handler.base.compress_org_details with file {csv_in}\n')
    uid_dict = dict_indexed_by_field(csv_in,'uid')
    
    

    # for each uid, if more than one record, find unique names and addresses
    # and write line to csv_out, with additional data to details_csv_out
    with open(spine_csv_out,'w+',newline='') as spine_csvfile,  open(details_csv_out, 'w+', newline='') as details_csvfile:
        tmp_fields = data_handler.tmp_fields
        if 'iteration' in tmp_fields: tmp_fields.remove('iteration')
        spine_writer = csv.DictWriter(spine_csvfile, fieldnames=SUB_SPINE_CSV_FIELDS+tmp_fields, extrasaction='ignore')
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


def sort_csv_by_field(filename,date_field):
    '''sorts a csv file by a date field, with null values first, new values stored in same filename, old in filename.replace('.csv','.notsorted.csv')'''
    
    backupfilename = filename.replace(".csv",".notsorted.csv")
    try:
        os.rename(filename,backupfilename)
        print(f'Original file renamed to {backupfilename}')
    except FileNotFoundError:
        print(f'Error renaming file {filename} to {backupfilename}: file not found')
        return

    print(f'Sorting file {backupfilename} by field {date_field}\n')
    df = pd.read_csv(backupfilename)
    df[date_field] = pd.to_datetime(df[date_field], errors='coerce', dayfirst=True)

    # Sort the dataframe by the date column (null values first, then most recent)
    df_sorted = df.sort_values(by=date_field, na_position='first', ascending=False)

    # Save the sorted dataframe to a new CSV file, with input filename
    ofile = filename#.replace('.csv', '.sorted.csv')
    df_sorted.to_csv(ofile, index=False, date_format='%d/%m/%Y', encoding='UTF8')
    print(f'Sorted file written to {ofile}\n')