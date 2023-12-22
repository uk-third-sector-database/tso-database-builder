
from datetime import datetime

from .base import DataHandler

exclude_filters = {
    "": []
}


class CoOpsDataHandler(DataHandler):
    fileencoding='UTF8'
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
            print('error with date',datestr)
        return d.strftime('%d/%m/%Y')
    

    def find_names(self, fieldnames) -> list:
        ''' returns name keys which have non-null values'''
        # 
        name_keys=[]
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

        new_row["uid"] =  'GB-COOP-'+ row[orgid]   
        new_row["organisationname"] = row[namefield]
        new_row["normalisedname"] = ''
        new_row["companyid"] = row[orgid]   
        new_row["charitynumber"] = ''
        new_row["housenumber"] = ''
        
        new_row["addressline1"] = row['Registered Street']
        new_row["addressline2"] = ''
        new_row["addressline3"] = ''

        new_row["addressline4"] = ''
        new_row["addressline5"] = ''
        new_row["city"] = row['Registered City']
        new_row["localauthority"] = row['Registered State/Province']
        new_row["postcode"] = row['Registered Postcode']
        new_row["source"] = 'CoOps'

        new_row["registrationdate"] = self.map_date(row['Incorporation Date'])
        new_row["dissolutiondate"] = self.map_date(row['Dissolved Date'])
        
        super().sort_address_fields(new_row)
        return new_row
        


'''
ccew data fields
uid
charitynumber
organisationname
normalisedname
companyid
housenumber
addressline1
addressline2
addressline3
addressline4
addressline5
city
localauthority
postcode
source
'''