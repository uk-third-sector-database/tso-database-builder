import csv
import string

from .base_definitions import NEW_SPINE_CSV_FORMAT,ORG_ID_MAPPING

GEO_LOOKUP_FILES = {
    'geo_data/NSPL21_AUG_2023_UK/Data/NSPL21_AUG_2023_UK.csv' : ['pcd','lat','long','imd','country']
}

class DataHandler:
    fileencoding = None
    names = None
        
    def all_filters(self, row: dict) -> bool:
        raise NotImplementedError()

    def transform_row(self, row: dict) -> list[dict]:
        #name_keys = self.find_names(row)
        
        spine_rows = []
        for name in self.names:
            spine_rows.append(self.format_row(name,row))
        #print(f'----- in transform_row. spine rows = {spine_rows}')
        return spine_rows
        #raise NotImplementedError()
    
    def map_date(self,datestr):
        raise NotImplementedError()
    
    def sort_address_fields(self,row:dict):
        address_fields = ["housenumber","addressline1",
        "addressline2","addressline3","addressline4","addressline5"]
        
        fulladdress = []

        fulladdress.extend(row[line].strip() for line in address_fields if line in row and row[line])

        fulladdress_str = ', '.join(fulladdress)
        try: fulladdress_str = fulladdress_str.split(row['postcode'].strip())[0]
        except ValueError: pass
        row['fulladdress'] = fulladdress_str.upper()
        row['city']=row['city'].upper()
        
        [row.pop(f, None) for f in address_fields] #remove old address fields

        row['normalisedname'] = normalizer(row['organisationname'])

        if not row['uid']: row['uid'] = 'GB-%s-%s'%(ORG_ID_MAPPING[row['source']],row['charitynumber'])

        try: row['fulladdress'] = row['fulladdress'].split(row['city'])[0].strip().rstrip(',')
        except ValueError: pass

        row['fulladdress'] = row['fulladdress'].replace(' ,',',')
        


def iter_csv_rows(filename,DataHandler):
    encoding=DataHandler.fileencoding
    with open(filename, newline="", encoding=encoding) as csvfile:
        reader = csv.DictReader(csvfile)
        DataHandler.names = DataHandler.find_names(reader.fieldnames)
        print('names: ',DataHandler.names)
        for row in reader:
            #print(row)
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


def do_csv_processing(
    input_csv_filename, output_csv_filename, data_handler: DataHandler):
    
    processed_rows = 0
    print('Processing file %s .......\n'%input_csv_filename)
    with open(output_csv_filename, "w+", encoding='UTF8', newline="") as csvfile:
        writer = csv.DictWriter(
            csvfile, fieldnames=NEW_SPINE_CSV_FORMAT, extrasaction="ignore"
        )
        writer.writeheader()
        for new_row in filter(
            data_handler.all_filters, iter_csv_rows(input_csv_filename,data_handler)
        ):
            #print(new_row)
            processed_rows += 1
            writer.writerows(data_handler.transform_row(new_row))

    print(".......... processed, %d lines written to %s\n"%(processed_rows,output_csv_filename))