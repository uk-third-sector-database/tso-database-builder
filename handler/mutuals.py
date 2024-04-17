
from .base import DataHandler

exclude_filters = {
    "": []
}


class MutualsDataHandler(DataHandler):
    fileencoding='Latin-1'
    tmp_fields = ['iteration']
    
    def all_filters(self,row: dict) -> bool:
      
        return True

    def find_names(self,row):
        return ['Society Name']

    def map_date(self, datestr):
        return super().map_date(datestr)
    
    def format_row(self,namefield,row) -> dict:
        '''format a row into Spine format, for given namefield'''
        new_row={}
        for field in row:
            row[field] = row[field].strip()

        fulladdress = row['Society Address']

        fulladdress = ', '.join(fulladdress.split(', ')) 

        # try to get postcode from full address 
        addr_words = str(fulladdress).split(' ')[-2:]  # Convert to string and split by 
        postcode = ' '.join([word for word in addr_words if len(word) < 5])

        new_row["uid"] = 'GB-MPR-'+ row['Full Registration Number']   
        new_row["organisationname"] = row[namefield]
        new_row["normalisedname"] = ''
        new_row["fulladdress"] = fulladdress
        new_row["postcode"] = postcode
        new_row["source"] = 'mutuals'
        new_row["id_in_source"] = row['Full Registration Number'] 
        new_row["registerdate"] = row['Registration Date']
        new_row["removeddate"] = row['Deregistration Date'] 
        new_row['companyid'] = ''
        new_row['city'] = ''
        new_row['iteration'] = row['Iteration']

        super().sort_address_fields(new_row)
        return new_row
    

    def find_primary_info(self, details_list):
        return super().find_primary_info(details_list)

    def combine_org_details_per_source(self, rows: list):
        return super().combine_org_details_per_source(rows)




'''
mutuals data fields:

Society Number,
Society Suffix,
Full Registation Number,
Society Name,
Registered As,
Society Address,
Registration Date,
Deregistration Date,
Registration Act,
Standard Industrial Classification Code (SIC),
Reporting Classification,
Society Status
'''