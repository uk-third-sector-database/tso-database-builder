
from datetime import datetime

from .base import DataHandler
from .base_definitions import extra_csv_entry_creator,sub_spine_entry_creator

exclude_filters = {
    "": []
}


class CoOpsDataHandler(DataHandler):
    fileencoding='UTF8'
    tmp_fields = ['iteration']

    def all_filters(self, row: dict) -> bool:

        for fieldname, exclude_values in exclude_filters.items():
            if row.get(fieldname) in exclude_values:
                return False
        return True
    
    def map_date(self, datestr):
        if not datestr:
            return ''
        try:
            d = datetime.strptime(datestr,'%d/%m/%Y')
        except:
            try:
                d = datetime.strptime(datestr,'%Y-%m-%d')
            except:
                print('error with date',datestr)
                return
        return d.strftime('%d/%m/%Y')
    

    def find_names(self, fieldnames) -> list:
        ''' returns name keys which have non-null values'''
        v = ['Registered Name','Trading Name']
        return [i for i in v if i in fieldnames]
    

    def format_row(self,namefield,row) -> dict:
        '''format a row into Spine format, for given namefield'''
        #orgid = 'Registered Number'
        orgid = 'CUK Organisation ID'

        #if not row['Registered Number']:
        #    print(f'{row[orgid]},{row[namefield]},{row["Registered Postcode"]}')

        new_row={}
        for field in row:
            row[field] = row[field].strip()
        if not row[orgid]: print(f'In co_ops.format_row. Issue: no id for row {row}')

        new_row["uid"] = 'GB-COOP-'+ row[orgid]   
        new_row["organisationname"] = row[namefield]
        new_row["normalisedname"] = ''
        new_row["fulladdress"] = row['Registered Street']
        new_row["city"] = row['Registered City']
        new_row["postcode"] = row['Registered Postcode']
        new_row["source"] = 'CoOps'
        new_row["id_in_source"] = row[orgid]   
        new_row["registerdate"] = self.map_date(row['Incorporation Date'])
        new_row["removeddate"] = self.map_date(row['Dissolved Date'])
        new_row['companyid'] = row['Registered Number']
        if namefield == 'Trading Name': 
            new_row['iteration'] = '2000' # force trading names into extra details by giving an early iteration year.
        else: 
            new_row['iteration'] = row['Iteration']

        
        super().sort_address_fields(new_row)
        return new_row
    

   
    def find_primary_info(self, details_list):
        return super().find_primary_info(details_list)
    
    

    def combine_org_details_per_source(self, rows: list):
        return super().combine_org_details_per_source(rows)
        

'''
CUK Organisation ID
Registered Number
Registrar
Registered Name
Trading Name
Legal Form
Registered Street
Registered City
Registered State/Province
Registered Postcode
UK Nation
FCA Reporting Classification
Ownership Classification
Registered Status
Incorporation Date
Dissolved Date
'''