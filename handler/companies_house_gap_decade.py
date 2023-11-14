"""
This code processes the bulk download from the companies house advanced search,
filtered on 'dissolved date between 01/01/2013 and 01/01/2023'
to capture the organisations which would be missing from both the data available at
the start of this project and the legacy data held by soton (2014)
"""


from datetime import datetime

from .base import DataHandler

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

exclude_filters = {
    "company_type": [
        'PRIVATE LIMITED COMPANY',
        'LIMITED PARTNERSHIP',
        'LIMITED LIABILITY PARTNERSHIP',
        'PUBLIC LIMITED COMPANY',
        'PRIVATE UNLIMITED COMPANY',
        'SCOTTISH PARTNERSHIP',
        'PRIVATE UNLIMITED',
        'INVESTMENT COMPANY WITH VARIABLE CAPITAL(UMBRELLA)',
        'PRIV LTD SECT. 30 (PRIVATE LIMITED COMPANY, SECTION 30 OF THE COMPANIES ACT)',
        'INVESTMENT COMPANY WITH VARIABLE CAPITAL (SECURITIES)',
        'INVESTMENT COMPANY WITH VARIABLE CAPITAL',
        'OVERSEAS ENTITY',
        'UNITED KINGDOM ECONOMIC INTEREST GROUPING',
        'OLD PUBLIC COMPANY',
        'UNITED KINGDOM SOCIETAS',
        'CONVERTED/CLOSED',
        'OTHER COMPANY TYPE',
        'PROTECTED CELL COMPANY',
        'ROYAL CHARTER COMPANY',
        'FURTHER EDUCATION AND SIXTH FORM COLLEGE CORPS',
        'OTHER COMPANY TYPE']
}


class CompaniesHouseGapDataHandler(DataHandler):
    fileencoding='UTF8'
    def all_filters(self,row: dict) -> bool:
        
        # exclude row if in exclude_filters
        for fieldname, exclude_values in exclude_filters.items():
            if row.get(fieldname).upper() in exclude_values:
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
    



    def format_row(self,namefield,row) -> dict:
        '''format a row into Spine format, for given namefield'''
        new_row={}
        for field in row:
            row[field] = row[field].strip()

        new_row["uid"] =  'GB-COH-'+ row['company_number']       
        new_row["organisationname"] = row[namefield]
        new_row["normalisedname"] = ''
        new_row["companyid"] = row['company_number']
        new_row["charitynumber"] = ''
        new_row["housenumber"] = ''
        new_row["addressline1"] = row['address_line_1']
        new_row["addressline2"] = row['address_line_2']
        new_row["addressline3"] = ''
        new_row["addressline4"] = ''
        new_row["addressline5"] = ''
        new_row["city"] = row['locality']
        new_row["localauthority"] = ''
        new_row["postcode"] = row['postal_code']
        new_row["source"] = 'adv_api %s'%' '.join([row['company_type'],row['company_subtype']])
        new_row["dissolutiondate"] = self.map_date(row['date_of_cessation'])
        new_row["registrationdate"] = self.map_date(row['date_of_creation'])

        return new_row
        
    def transform_row(self, row: dict) -> list[dict]:
        '''returns list of rows in SPINE format'''
        
        name = 'company_name'
        return [self.format_row(name,row)]


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