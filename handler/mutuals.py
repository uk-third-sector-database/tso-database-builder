
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
        

        new_row["uid"] = 'GB-MPR-'+ row['societynumber']   
        new_row["organisationname"] = row[namefield]
        new_row["normalisedname"] = ''
        new_row["fulladdress"] = fulladdress
        new_row["city"] = row['city']
        new_row["postcode"] = row['postcode']
        new_row["primarysource"] = row['source']
        new_row["primaryid"] = row['societynumber'] 
        new_row["primaryregdate"] = ''
        new_row["dissolutiondate"] = ''
        new_row["secondarysource"] = ''
        new_row["secondaryid"] = ''
        new_row["secondaryregdate"] = ''

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