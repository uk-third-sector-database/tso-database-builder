

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

    

        new_row["uid"] = 'GB-CQC-'+ row['CQC Provider ID (for office use only)']      
        new_row["organisationname"] = row[namefield]
        new_row["normalisedname"] = ''
        new_row["fulladdress"] = row['Address']
        new_row["city"] = ''
        new_row["postcode"] = row['Postcode']
        new_row["source"] = 'CareQualityCommission'
        new_row["id_in_source"] = row['CQC Provider ID (for office use only)'] 
        new_row["registerdate"] = ''
        new_row["removeddate"] = ''
        new_row['companyid'] = ''


        super().sort_address_fields(new_row)
        return new_row
        

    def combine_org_details_per_source(self, rows: list):
        '''Need to '''
        print(f" Combine_org_details_per_source currrently not implemented for careQC: {rows}")
        return '',''


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