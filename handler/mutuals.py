
from .base import DataHandler

exclude_filters = {
    "": []
}


class MutualsDataHandler(DataHandler):
    fileencoding='UTF8'
    
    def all_filters(self, row: dict) -> bool:
      
        return True

    def find_names(self,row):
        return ['organisationname']

    def map_date(self, datestr):
        return super().map_date(datestr)
    
    def format_row(self,namefield,row) -> dict:
        '''format a row into Spine format, for given namefield'''
        new_row={}
        for field in row:
            row[field] = row[field].strip()

        fulladdress = ''
        if row['postcode']:
            fulladdress = row['address'].split(row['postcode'])[0].strip(', ')
        else:
            fulladdress = row['address']

        fulladdress = ','.join(fulladdress.split(', ')) # deal with formatting "1 King Street, Area,City
        new_row["uid"] =  'GB-MPR-'+ row['societynumber']   
        new_row["organisationname"] = row[namefield]
        new_row["normalisedname"] = ''
        new_row["companyid"] = row['societynumber']   
        new_row["charitynumber"] = ''
        new_row["housenumber"] = ''
        
        new_row["addressline1"] = fulladdress
        new_row["addressline2"] = ''
        new_row["addressline3"] = ''
        new_row["addressline4"] = ''
        new_row["addressline5"] = ''
        new_row["city"] = row['city']
        new_row["localauthority"] = ''
        new_row["postcode"] = row['postcode']
        new_row["source"] = row['source']
        new_row["dissolutiondate"] = '' 
        new_row["registrationdate"] = ''

        super().sort_address_fields(new_row)
        return new_row
        



'''
mutuals data fields
societynumber,
organisationname
address
source
uid
normalisedname
companyid
housenumber
city
localauthority
postcode
'''