
import time
from datetime import datetime

from .base import DataHandler

exclude_filters = {
    "": []
}


class CoOpsDataHandler(DataHandler):
    fileencoding='UTF8'
    def all_filters(self, row: dict) -> bool:
        # filter out orgs dissolved prior to 1997 
        if row.get("Dissolved Date"):
            d_date = time.strptime(row.get("Dissolved Date"),'%d/%m/%Y')
            bsd_date = time.strptime('1/1/1997','%d/%m/%Y')
            if d_date < bsd_date:
                return False  
        # other filters?
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
    

    def find_names(self, row:dict) -> list:
        ''' returns name keys which have non-null values'''
        # 
        name_keys=[]
        v = ['Registered Name','Trading Name']

        for i in v:
            if row[i]: name_keys.append(i)
        return name_keys


    def format_row(self,namefield,row) -> dict:
        '''format a row into Spine format, for given namefield'''
        new_row={}
        for field in row:
            row[field] = row[field].strip()

        new_row["uid"] =  'GB-COOP-'+ row['CUK Organisation ID']   
        new_row["organisationname"] = row[namefield]
        new_row["normalisedname"] = ''
        new_row["companyid"] = row['CUK Organisation ID']   
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
        
        return new_row
        
    def transform_row(self, row: dict) -> list[dict]:
        '''returns list of rows in SPINE format'''
        #  check for multiple names
        name_keys = self.find_names(row)
        
        spine_rows = []
        for name in name_keys:
            spine_rows.append(self.format_row(name,row))

        return spine_rows


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