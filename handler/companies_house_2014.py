
import re
import time
from datetime import datetime

from .base import DataHandler

exclude_filters = {
    "companycategory": [
        "Private Limited Company",
        "Limited Partnership",
        "Limited Liability Partnership",
        "Public Limited Company",
        "Private Unlimited Company",
        "Scottish Partnership",
        "Private Unlimited",
        "Investment Company with Variable Capital(Umbrella)",
        "PRIV LTD SECT. 30 (Private limited company, section 30 of the Companies Act)",
        "Investment Company with Variable Capital (Securities)",
        "Investment Company with Variable Capital",
        "Overseas Entity",
        "United Kingdom Economic Interest Grouping",
        "Old Public Company",
        "United Kingdom Societas",
        "Converted/Closed",
        "Other Company Type",
        "Protected Cell Company",
        "Royal Charter Company",
        "Further Education and Sixth Form College Corps",
        "Other company type"
    ]
}


class CompaniesHouse2014DataHandler(DataHandler):
    fileencoding='Latin-1'

    def all_filters(self, row: dict) -> bool:
        
        # exclude row if in exclude_filters
        for fieldname, exclude_values in exclude_filters.items():
            if row.get(fieldname) in exclude_values:
                return False
            
        # exclude row if org dissolved prior to 1997
        if row.get("chremy"):
            d_date = time.strptime(row.get("chremy"),'%Y')
            bsd_date = time.strptime('1997','%Y')
            if d_date < bsd_date:
                return False
        return True
    
    def map_date(self, datestr):
        if not datestr:
            return ''
        try:
            d = datetime.strptime(datestr,'%Y')
            ## since we will accept the earlier of two registration dates for final match, using last day of the year for the data which only contains year
            d = d.replace(month = 12)
            d = d.replace(day = 31)
        except:
            print('error with date',datestr)
        return d.strftime('%d/%m/%Y')
    

    def find_names(self, row:dict) -> list:
        ''' returns name keys which have non-null values'''
        name_keys=[]
        for k in row.keys():
            v = re.findall(('.*ompanyname'),k)
            for i in v:
                if i:
                    if row[i]: name_keys.append(i)
        return name_keys

    def find_addresses(self, row:dict) -> list:
        ''' returns list of address keys which have non-null values
        '''
        addr_keys=[]
        for k in row.keys():
            if 'RegAddress' in k and not 'CareOf' in k and row[k]:
                addr_keys.append(k)
        return addr_keys

    def format_row(self,namefield,row) -> dict:
        '''format a row into Spine format, for given namefield'''
        new_row={}
        for field in row:
            row[field] = row[field].strip()

        new_row["uid"] =  'GB-COH-'+ row['companynumber']       
        new_row["organisationname"] = row[namefield]
        new_row["normalisedname"] = ''
        new_row["companyid"] = row['companynumber']
        new_row["charitynumber"] = ''
        new_row["housenumber"] = ''
        new_row["addressline1"] = ''
        new_row["addressline2"] = ''
        new_row["addressline3"] = ''
        new_row["addressline4"] = ''
        new_row["addressline5"] = ''
        new_row["city"] = ''
        new_row["localauthority"] = ''
        new_row["postcode"] = row['regaddresspostcode']
        new_row["source"] = '2014_prior %s'%row['companycategory']#'CompaniesHouse2014'
        new_row["dissolutiondate"] = self.map_date(row['chremy'])
        new_row["registrationdate"] = self.map_date(row['chregy'])

        return new_row
        
    def transform_row(self, row: dict) -> list[dict]:
        '''returns list of rows in SPINE format'''
        #  check for multiple names
        name_keys = self.find_names(row)
        
        spine_rows = []
        for name in name_keys:
            spine_rows.append(self.format_row(name,row))

        return spine_rows

#          "uid"
#         "organisationname",
#         "normalisedname",
#         "companyid",
#         "housenumber",
#         "addressline1",
#         "addressline2",
#         "addressline3",
#         "addressline4",
#         "addressline5",
#         "city",
#         "localauthority",
#         "postcode",
#         "source",


# fields in source data:
# companynumber,regaddresspostcode,companyname,companycategory,chregy,chremy