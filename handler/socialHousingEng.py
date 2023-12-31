
import datetime


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
        datestr = datestr.strip()
        if not datestr:
            return ''
        try:
            d = datetime.strptime(datestr,'%d/%m/%Y')
        except:
            print('error with date *%s*'%datestr)
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
        new_row["companyid"] = row['Registration number']
        new_row["charitynumber"] = ''
        new_row["housenumber"] = ''
        
        new_row["addressline1"] = ''
        new_row["addressline2"] = ''
        new_row["addressline3"] = ''
        new_row["addressline4"] = ''
        new_row["addressline5"] = ''
        new_row["city"] = ''
        new_row["localauthority"] = ''
        new_row["postcode"] = ''
        new_row["source"] = 'SocialHousingEngland'
        new_row["dissolutiondate"] = ''
        #new_row["registrationdate"] = self.map_date(row['Registration date'])   #this errors, not obvious why, as field has normal looking dates in it.
        new_row["registrationdate"] = row['Registration date']
        
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