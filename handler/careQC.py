

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

    def find_names(self, row:dict) -> list:
        ''' returns name keys which have non-null values'''
        # 
        name_keys=[]
        v = ['Name','Also known as']

        for i in v:
            if row[i]: name_keys.append(i)
        return name_keys


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