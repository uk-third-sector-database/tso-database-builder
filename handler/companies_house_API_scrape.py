"""
This code processes the bulk download from the companies house advanced search,
filtered on 'dissolved date between 01/01/2013 and 01/01/2023'
to capture the organisations which would be missing from both the data available at
the start of this project and the legacy data held by soton (2014)
"""


from datetime import datetime

from .base import DataHandler,sort_encoding_issue

""" exclude_filters = {
    "company_type": [
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
} """

exclude_filters = {}
# removing these filters, as a filter was already applied when the API scrape was carried out.
'''
    "company_type": [
        'private limited company',
        'limited partnership',
        'limited liability partnership',
        'public limited company',
        'private unlimited company',
        'scottish partnership',
        'private unlimited',
        'investment company with variable capital(umbrella)',
        'priv ltd sect. 30 (private limited company, section 30 of the companies act)',
        'investment company with variable capital (securities)',
        'investment company with variable capital',
        'overseas entity',
        'united kingdom economic interest grouping',
        'old public company',
        'united kingdom societas',
        'converted/closed',
        'converted-or-closed',
        'other company type',
        'protected cell company',
        'royal charter company',
        'further education and sixth form college corps',
        'other company type']
}'''


class CH_APIScrape_DataHandler(DataHandler):
    fileencoding='UTF8'
    tmp_fields = ['SIC']
    
    def all_filters(self,row: dict) -> bool:

        # exclude row if in exclude_filters
        for fieldname, exclude_values in exclude_filters.items():
            if row.get(fieldname).lower() in exclude_values:
                return False
            

        return True

    def map_date(self, datestr):
        if not datestr:
            return ''
        try:
            d = datetime.strptime(datestr,'%Y-%m-%d')
        except:
            print('error with date',datestr)
        return d.strftime('%d/%m/%Y')
    
    def find_names(self, row) -> list:
        return ['company_name']


    def format_row(self,namefield,row) -> dict:
        '''format a row into Spine format, for given namefield'''
        new_row={}
        
        new_row["uid"] =  'GB-COH-'+ row['company_number']       
        new_row["organisationname"] = row[namefield]
        new_row["normalisedname"] = ''
        new_row["id_in_source"] = row['company_number']
        new_row["addressline1"] = row['address_line_1']
        new_row["addressline2"] = row['address_line_2']
        new_row["addressline3"] = ''
        new_row["addressline4"] = ''
        new_row["addressline5"] = ''
        new_row["city"] = row['locality']
        new_row["postcode"] = row['postal_code']
        
        new_row["source"] = 'CH'
        new_row['source_register'] = 'Companies House' #' '.join([row['company_type'],row['company_subtype']]).strip()
        new_row["companytype"] = ' '.join([row['company_type'],row['company_subtype']]).strip()
        new_row["removeddate"] = self.map_date(row['date_of_cessation'])
        new_row["registerdate"] = self.map_date(row['date_of_creation'])
        new_row["iteration"] = '2022'
        new_row['is_cic'] = bool(row['company_subtype'] == 'community-interest-company')
        new_row['SIC'] = row['sic_codes'].strip('[').strip(']').replace("'",'')
        

        super().sort_address_fields(new_row)
        return new_row
        



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


# input csv fields:
#etag,
#hits,
#company_name,
#company_number,
#company_status,
#company_subtype,
#company_type,
#date_of_cessation,
#date_of_creation,
#sic_codes,
#kind,
#address_line_1,
#address_line_2,
#country,
#locality,
#postal_code,
#region
    


