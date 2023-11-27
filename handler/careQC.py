

from .base import DataHandler

exclude_filters = {
    "": []
}


class CQCDataHandler(DataHandler):
    fileencoding='UTF8'
    def all_filters(self, row: dict) -> bool:

        # other filters?
        for fieldname, exclude_values in exclude_filters.items():
            if row.get(fieldname) in exclude_values:
                return False
        return True
    
    def map_date(self, datestr):
        return super().map_date(datestr)

    def find_names(self, fieldnames) -> list:
        ''' returns name keys which have non-null values'''
        # 
        v = ['Name','Also known as']
        return [i for i in v if i in fieldnames]
        

    def format_row(self,namefield,row) -> dict:
        '''format a row into Spine format, for given namefield'''
        new_row={}
        for field in row:
            row[field] = row[field].strip()

        new_row["uid"] =  'GB-CQC-'+ row['CQC Provider ID (for office use only)']      
        new_row["organisationname"] = row[namefield]
        new_row["normalisedname"] = ''
        new_row["companyid"] = row['CQC Provider ID (for office use only)']   
        new_row["charitynumber"] = ''
        new_row["housenumber"] = ''
        
        new_row["addressline1"] = row['Address']
        new_row["addressline2"] = ''
        new_row["addressline3"] = ''
        new_row["addressline4"] = ''
        new_row["addressline5"] = ''
        new_row["city"] = ''
        new_row["localauthority"] = row['Local authority']
        new_row["postcode"] = row['Postcode']
        new_row["source"] = 'CareQualityCommission'
        new_row["dissolutiondate"] = '' 
        new_row["registrationdate"] = ''
        super().sort_address_fields(new_row)
        #print(f' *** In format_row. new_row = {new_row}')
        return new_row
        



'''
CQC data fields

Name,
Also known as,
Address,
Postcode,
Phone number,
Service's website (if available),
Service types,
Date of latest check,
Specialisms/services,
Provider name,
Local authority,
Region,
Location URL,
CQC Location ID (for office use only),
CQC Provider ID (for office use only)
'''