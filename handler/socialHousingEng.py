
from datetime import datetime


from .base import DataHandler

include_filters = {
    "Designation": ['Non-profit']
}


class SocialHousingEngDataHandler(DataHandler):
    fileencoding='Latin-1'
    def all_filters(self, row: dict) -> bool:

        # other filters?
        for fieldname, include_values in include_filters.items():
            if row.get(fieldname) in include_values:
                return True
            else:
                return False
        return False

    def map_date(self, datestr):
        print(f'input date str = {datestr}, type = {type(datestr)}')
        datestr = datestr.strip()
        if not datestr:
            return ''
        try:
            d = datetime.strptime(datestr,'%d/%m/%Y')
        except Exception as e:
            print(f"error with date *{datestr} ({e})")
            return ''
        return d.strftime('%d/%m/%Y')
    
    def find_names(self, fieldnames) -> list:

        v = ['Organisation name','ï»¿Organisation name','\ufeffOrganisation name']
                
        return [item for item in v if item in fieldnames]

    def format_row(self,namefield,row) -> dict:
        '''format a row into Spine format, for given namefield'''
        new_row={}
        for field in row:
            row[field] = row[field].strip()

        new_row["uid"] =  'GB-SHPE-'+ row['Registration number']   
        new_row["organisationname"] = row[namefield]
        new_row["normalisedname"] = ''
        new_row["primaryid"] = row['Registration number']
        new_row["fulladdress"] = ''
        new_row["city"] = ''
        new_row["postcode"] = ''
        new_row["primarysource"] = 'SocialHousingEngland'
        new_row["dissolutiondate"] = ''
        new_row["primaryregdate"] = self.map_date(row['Registration date'])   
        new_row["secondarysource"] = ''
        new_row["secondaryid"] = ''
        new_row["secondaryregdate"] = ''

        super().sort_address_fields(new_row)
        return new_row
        


'''
Social Housing England data fields
Organisation name,
Registration number,
Registration date,
Designation,
Corporate form
'''