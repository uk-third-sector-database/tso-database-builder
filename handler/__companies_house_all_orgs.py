
import re
import datetime
from .base import DataHandler

# for AD for 360Giving matching - no excluded company types, uid, name and type for all orgs
exclude_filters = {
    "": []
}


class CompaniesHouse_ALL_DataHandler(DataHandler):
    fileencoding='UTF8'
    tmp_fields = ['iteration','extraname']
    
    def all_filters(self, row: dict) -> bool:
        
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
            new_row["addressline1"] = ''#row['RegAddress.POBox']
            new_row["addressline2"] = ''#row['RegAddress.AddressLine1']
            new_row["addressline3"] = ''#row[' RegAddress.AddressLine2']
        else:#
            new_row["addressline1"] = ''#row['RegAddress.AddressLine1']
            new_row["addressline2"] = ''#row[' RegAddress.AddressLine2']
            new_row["addressline3"] = ''
        new_row["city"] = ''#row['RegAddress.PostTown']
        new_row["postcode"] = ''#row['RegAddress.PostCode']
        new_row["source"] = row['CompanyCategory']#'CompaniesHouse'#'CH'
        new_row["removeddate"] = ''#row['DissolutionDate']
        new_row["registerdate"] = ''#row['IncorporationDate']
        if 'PreviousName' in namefield:
            new_row['extraname'] = 1
        else:
            new_row['extraname'] = 0
        
        
        

        super().sort_address_fields(new_row)
        return new_row
        
    def find_primary_info(self, details_list):
        return super().find_primary_info(details_list)
    
    def combine_org_details_per_source(self, rows: list):
        return super().combine_org_details_per_source(rows)



