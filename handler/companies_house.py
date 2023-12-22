
import re
import datetime

from .base import DataHandler

exclude_filters = {
    "CompanyCategory": [
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


class CompaniesHouseDataHandler(DataHandler):
    fileencoding='UTF8'
    
    def all_filters(self, row: dict) -> bool:
        
        # exclude row if in exclude_filters
        for fieldname, exclude_values in exclude_filters.items():
            if row.get(fieldname) in exclude_values:
                return False
        return True
            

    def map_date(self, datestr):
        if not datestr:
            return ''
        try:
            d = datetime.strptime(datestr,'%d/%m/%Y')
        except:
            print('error with date',datestr)
        return d.strftime('%d/%m/%Y')
    


    def find_names(self, fieldnames) -> list:
        return [n for n in fieldnames if re.search('.*ompanyname',n, flags=re.IGNORECASE)]

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

        new_row["uid"] =  'GB-COH-'+ row[' CompanyNumber']       
        new_row["organisationname"] = row[namefield]
        new_row["normalisedname"] = ''
        new_row["companyid"] = row[' CompanyNumber']
        new_row["charitynumber"] = ''
        new_row["housenumber"] = ''
        if row['RegAddress.POBox']:
            new_row["addressline1"] = row['RegAddress.POBox']
            new_row["addressline2"] = row['RegAddress.AddressLine1']
            new_row["addressline3"] = row[' RegAddress.AddressLine2']
        else:
            new_row["addressline1"] = row['RegAddress.AddressLine1']
            new_row["addressline2"] = row[' RegAddress.AddressLine2']
            new_row["addressline3"] = ''
        new_row["addressline4"] = ''
        new_row["addressline5"] = ''
        new_row["city"] = row['RegAddress.PostTown']
        new_row["localauthority"] = row['RegAddress.County']
        new_row["postcode"] = row['RegAddress.PostCode']
        new_row["source"] = '2023_download %s'%row['CompanyCategory']#'CompaniesHouse'
        new_row["dissolutiondate"] = row['DissolutionDate']
        new_row["registrationdate"] = row['IncorporationDate']

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


# "CompanyName": "",
#         "CompanyNumber": "",
#         "RegAddress.CareOf": "",
#         "RegAddress.POBox": "",
#         "RegAddress.AddressLine1": "",
#         "RegAddress.AddressLine2": "",
#         "RegAddress.PostTown": "",
#         "RegAddress.County": "",
#         "RegAddress.Country": "",
#         "RegAddress.PostCode": "",
#         "CompanyCategory": "",
#         "CompanyStatus": "",
#         "CountryOfOrigin": "",
#         "DissolutionDate": "",
#         "IncorporationDate": "",
#         "Accounts.AccountRefDay": "",
#         "Accounts.AccountRefMonth": "",
#         "Accounts.NextDueDate": "",
#         "Accounts.LastMadeUpDate": "",
#         "Accounts.AccountCategory": "",
#         "Returns.NextDueDate": "",
#         "Returns.LastMadeUpDate": "",
#         "Mortgages.NumMortCharges": "",
#         "Mortgages.NumMortOutstanding": "",
#         "Mortgages.NumMortPartSatisfied": "",
#         "Mortgages.NumMortSatisfied": "",
#         "SICCode.SicText_1": "",
#         "SICCode.SicText_2": "",
#         "SICCode.SicText_3": "",
#         "SICCode.SicText_4": "",
#         "LimitedPartnerships.NumGenPartners": "",
#         "LimitedPartnerships.NumLimPartners": "",
#         "URI": "",
#         "PreviousName_1.CONDATE": "",
#         "PreviousName_1.CompanyName": "",
#         "PreviousName_2.CONDATE": "",
#         "PreviousName_2.CompanyName": "",
#         "PreviousName_3.CONDATE": "",
#         "PreviousName_3.CompanyName": "",
#         "PreviousName_4.CONDATE": "",
#         "PreviousName_4.CompanyName": "",
#         "PreviousName_5.CONDATE": "",
#         "PreviousName_5.CompanyName": "",
#         "PreviousName_6.CONDATE": "",
#         "PreviousName_6.CompanyName": "",
#         "PreviousName_7.CONDATE": "",
#         "PreviousName_7.CompanyName": "",
#         "PreviousName_8.CONDATE": "",
#         "PreviousName_8.CompanyName": "",
#         "PreviousName_9.CONDATE": "",
#         "PreviousName_9.CompanyName": "",
#         "PreviousName_10.CONDATE": "",
#         "PreviousName_10.CompanyName": "",
#         "ConfStmtNextDueDate": "",
#         "ConfStmtLastMadeUpDate": "",
#         r = row.copy()
#         r["transformed"] = "yes"

#         return [r]
