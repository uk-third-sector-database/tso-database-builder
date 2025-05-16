
from datetime import datetime
from .base import DataHandler
from .base_definitions import sub_spine_entry_creator,extra_csv_entry_creator
'''

'''


from .base import DataHandler,sort_encoding_issue

exclude_filters = {
    "organisationname": ['N/A']
}


class CCNIDataHandler(DataHandler):
    fileencoding='utf-8'
    tmp_fields = ['iteration']

    def all_filters(self, row: dict) -> bool:
        # other filters?
        for fieldname, exclude_values in exclude_filters.items():
            if row.get(fieldname) in exclude_values:
                return False
        return True
    

    def map_date(self, datestr):
        if not datestr:
            return ''
        try:
            d = datetime.strptime(datestr,'%d%b%Y')
            return d.strftime('%d/%m/%Y')
        except:
            try:
                d = datetime.strptime(datestr,'%d/%m/%Y')
                return d.strftime('%d/%m/%Y')
            except:
                try:
                    d = datetime.strptime(datestr,'%Y-%m-%d')
                    return d.strftime('%d/%m/%Y')
                except:
                    print('error with date',datestr)
        return ''
    

    def find_names(self, row) -> list:
        return ['organisationname']


    def format_row(self,namefield,row) -> dict:
        '''format a row into Spine format, for given namefield'''
        new_row={}
        
        new_row["uid"] =  'GB-NIC-'+ row['charitynumber']   
        new_row["organisationname"] = row[namefield]
        new_row["normalisedname"] = ''
        new_row["companyid"] = row['companyid']   
        new_row["charitynumber"] = row['charitynumber']
        new_row["housenumber"] = row['housenumber']
        new_row["addressline1"] = row["address"]
        new_row["city"] = row['city']
        new_row["localauthority"] = row['localauthority']
        new_row["postcode"] = row['postcode']
        new_row["source"] = 'ccni'
        new_row['source_register'] = 'Charity Commission for Northern Ireland'
        new_row["id_in_source"] = row['charitynumber']
        new_row["registerdate"] = self.map_date(row['registerdate'])
        new_row["removeddate"] = self.map_date(row['removeddate'])
        new_row['iteration'] = row['iteration']
        
        super().sort_address_fields(new_row)
        return new_row
    


    def find_primary_info(self, details_list):
        return super().find_primary_info(details_list)
    

    def combine_org_details_per_source(self, rows: list):
        return super().combine_org_details_per_source(rows)





'''
ccni data fields


uid
charitynumber
organisationname
normalisedname
companyid
housenumber
address
city
localauthority
postcode
registerdate
source

'''