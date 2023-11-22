
from datetime import datetime
'''

'''


from .base import DataHandler

exclude_filters = {
    "organisationname": ['N/A']
}


class OSCRDataHandler(DataHandler):
    fileencoding='Latin-1'
    def all_filters(self, row: dict) -> bool:
        # other filters?
        for fieldname, exclude_values in exclude_filters.items():
            if row.get(fieldname) in exclude_values:
                return False
        return True
    

    def map_date(self, datestr):
        if not datestr:
            return ''
        try:
            d = datetime.strptime(datestr,'%d%b%Y')
        except:
            print('error with date',datestr)
        return d.strftime('%d/%m/%Y')
    

    def find_names(self, row:dict) -> list:
        ''' returns name keys which have non-null values'''
        # 
        name_keys=['organisationname']
        return name_keys


    def format_row(self,namefield,row) -> dict:
        '''format a row into Spine format, for given namefield'''
        new_row={}
        for field in row:
            row[field] = row[field].strip()


        new_row["uid"] =  'GB-SC-'+ row['charitynumber']   
        new_row["organisationname"] = row[namefield]
        new_row["normalisedname"] = ''
        new_row["companyid"] = row['companyid']   
        new_row["charitynumber"] = row['charitynumber']
        new_row["housenumber"] = row['housenumber']
        
        new_row["addressline1"] = row["addressline1"]
        new_row["addressline2"] = row["addressline2"]
        new_row["addressline3"] = row["addressline3"]
        new_row["addressline4"] = row["addressline4"]
        new_row["addressline5"] = row["addressline5"]
        new_row["city"] = row['city']
        new_row["localauthority"] = row['localauthority']
        new_row["postcode"] = row['postcode']
        new_row["source"] = row['source']
        new_row["registrationdate"] = self.map_date(row['registerdate'])
        new_row["dissolutiondate"] = self.map_date(row['removeddate'])
        
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
oscr data fields
uid
charitynumber
organisationname
normalisedname
companyid
address
housenumber
addressline1
addressline2
addressline3
addressline4
addressline5
addressline6
addressline7
addressline8
city
localauthority
postcode
source
name_origin
register

'''