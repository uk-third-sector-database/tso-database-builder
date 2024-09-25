
import re
from datetime import datetime

from .base import DataHandler

exclude_filters = {
    "companycategory": [
        "private limited company",
        "limited partnership",
        "limited liability partnership",
        "public limited company",
        "private unlimited company",
        "scottish partnership",
        "private unlimited",
        "investment company with variable capital(umbrella)",
        "priv ltd sect. 30 (private limited company, section 30 of the companies act)",
        "investment company with variable capital (securities)",
        "investment company with variable capital",
        "overseas entity",
        "united kingdom economic interest grouping",
        "old public company",
        "united kingdom societas",
        "converted/closed",
        "other company type",
        "protected cell company",
        "royal charter company",
        "further education and sixth form college corps",
        "other company type"
    ]
}


class CompaniesHouse2014DataHandler(DataHandler):
    fileencoding='Latin-1'

    def all_filters(self, row: dict) -> bool:
        
        # exclude row if in exclude_filters
        for fieldname, exclude_values in exclude_filters.items():
            if row.get(fieldname).lower() in exclude_values:
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
    

    def find_names(self, fieldnames) -> list:
        ''' returns name keys which have non-null values'''
        return [n for n in fieldnames if re.search('.*ompanyname',n)]
        

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
        new_row["id_in_source"] = row['companynumber']
        new_row["fulladdress"] = ''
        new_row["city"] = ''
        new_row["postcode"] = row['regaddresspostcode']
        new_row["source"] = row['companycategory']#'CompaniesHouse2014'#CH
        new_row["removeddate"] = self.map_date(row['chremy'])
        new_row["registerdate"] = self.map_date(row['chregy'])
        new_row["iteration"] = '2014'
        new_row['SIC'] = ''
        
        

        super().sort_address_fields(new_row)
        return new_row


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