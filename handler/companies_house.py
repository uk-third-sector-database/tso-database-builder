
import re
import datetime

from .base import DataHandler

exclude_filters = {
    "CompanyCategory": [
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
include_filters = {
    "CompanyCategory":[
    'pri/ltd by guar/nsc (private, limited by guarantee, no share capital)',
    "pri/lbg/nsc (private, limited by guarantee, no share capital, use of 'limited' exemption)",
    'charitable incorporated organisation',
    'community interest company',
    'registered society',
    'scottish charitable incorporated organisation',
    'industrial and provident society'
]
}

class CompaniesHouseDataHandler(DataHandler):
    fileencoding='UTF8'
    tmp_fields = ['iteration','extraname']
    
    def all_filters(self, row: dict) -> bool:
        
        ##exclude row if in exclude_filters
        for fieldname, exclude_values in exclude_filters.items():
            if row.get(fieldname).lower() in exclude_values:
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
        new_row["id_in_source"] = row[' CompanyNumber']

        if row['RegAddress.POBox']:
            new_row["addressline1"] = row['RegAddress.POBox']
            new_row["addressline2"] = row['RegAddress.AddressLine1']
            new_row["addressline3"] = row[' RegAddress.AddressLine2']
        else:
            new_row["addressline1"] = row['RegAddress.AddressLine1']
            new_row["addressline2"] = row[' RegAddress.AddressLine2']
            new_row["addressline3"] = ''
        new_row["city"] = row['RegAddress.PostTown']
        new_row["postcode"] = row['RegAddress.PostCode']
        new_row["source"] = 'CH'
        new_row["companytype"] = row['CompanyCategory']#'CompaniesHouse'#'CH'
        new_row["removeddate"] = row['DissolutionDate']
        new_row["registerdate"] = row['IncorporationDate']
        if 'PreviousName' in namefield:
            new_row['extraname'] = 1
        else:
            new_row['extraname'] = 0
        
        #sic_codes = [row['SICCode.SicText_1'],row['SICCode.SicText_2'],row['SICCode.SicText_3'],row['SICCode.SicText_4']]
        #new_row['SIC'] = ', '.join([f for f in sic_codes if f]) 
        
        

        super().sort_address_fields(new_row)
        return new_row
        
    def find_primary_info(self, details_list):
        return super().find_primary_info(details_list)
    
    def combine_org_details_per_source(self, rows: list):
        return super().combine_org_details_per_source(rows)



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



'''
Included company types: 

 "PRI/LTD BY GUAR/NSC (Private, limited by guarantee, no share capital) "
 "Charitable Incorporated Organisation "
 "Community Interest Company "
 "Registered Society "
 "PRI/LBG/NSC (Private, Limited by guarantee, no share capital, use of 'Limited' exemption) "
 "Scottish Charitable Incorporated Organisation "
 "Industrial and Provident Society "

'''



