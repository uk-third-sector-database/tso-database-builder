
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
        result = super().combine_org_details_per_source(rows)
        if not result:
            # the base helper returns [] when a row is missing required fields
            return result
        sub_spine_row, extras = result

        # The base helper reads the identifier fields off whichever row happened to
        # be last in the group. For CCNI that is a removals row or an older snapshot
        # for most charities, which silently discarded the company number. Take the
        # FIRST nonblank company number across the charity's rows instead.
        # This deliberately differs from the CCEW convention of taking the LAST
        # nonblank value (handler/ccew.py): the 2024 seed rows come first in
        # ccni.all.csv and their numbers are proven - they produced real links in
        # v1.0-v1.2 - whereas CCNI's self-reported 'Company number' download field is
        # wrong in 2 of the 5 charities where the two sources overlap: 107318 reports
        # '999999' against seed NI661353 (now caught earlier as repeated-digit filler)
        # and 107859 reports '64999', a truncation of seed NI649994.
        company_id = ''
        for r in rows:
            if r['companyid']:
                company_id = r['companyid']
                break
        sub_spine_row['companyid'] = company_id

        return sub_spine_row, extras





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