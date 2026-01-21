
from datetime import datetime
import pandas as pd

from .base import DataHandler,sort_encoding_issue
from .base_definitions import sub_spine_entry_creator,extra_csv_entry_creator
nulls = (None, '', [], {}, ())

exclude_filters = {
    "organisationname": ['N/A']
}


class OSCRDataHandler(DataHandler):
    fileencoding='utf-8'#'Latin-1'
    tmp_fields = ['crossborder','name_origin','iteration']

    def all_filters(self,row: dict) -> bool:
        # other filters?
        for fieldname, exclude_values in exclude_filters.items():
            if row.get(fieldname) in exclude_values:
                return False
        return True
    

    def map_date(self, datestr):
        if not datestr or '########' in datestr:
            return ''
        try:
            d = datetime.strptime(datestr,'%d%b%Y')#'%d/%m/%Y')  previous version
            return d.strftime('%d/%m/%Y')
        except:
            try:
                d = datetime.strptime(datestr,'%d/%m/%Y')
                return d.strftime('%d/%m/%Y')
            except: 
                print('error with date',datestr)
                return 
        
    

    def find_names(self, row) -> list:
        ''' returns name keys which have non-null values'''
        # 
        return ['organisationname']


    def format_row(self,namefield,row) -> dict:
        '''format a row into Spine format, for given namefield'''
        new_row={}
                        

        new_row["uid"] =  'GB-SC-'+ row['charitynumber']   
        new_row["organisationname"] = row[namefield]
        new_row["normalisedname"] = ''
        new_row["companyid"] = row['companyid']   
        new_row["id_in_source"] = row['charitynumber']
        new_row["housenumber"] = row['housenumber']
        
        new_row["addressline1"] = row["addressline1"]
        new_row["addressline2"] = row["addressline2"]
        new_row["addressline3"] = row["addressline3"]
        new_row["addressline4"] = row["addressline4"]
        new_row["addressline5"] = row["addressline5"]
        new_row["addressline6"] = row["addressline6"]
        new_row["addressline7"] = row["addressline7"]
        new_row["addressline8"] = row["addressline8"]

        new_row["city"] = row['city']
        new_row["localauthority"] = row['localauthority']
        new_row["postcode"] = row['postcode']
        new_row["source_register"] = 'Scottish Charity Register'
        new_row["source"] = 'OSCR'
        new_row["registerdate"] = self.map_date(row['registerdate'])
        new_row["removeddate"] = self.map_date(row['removeddate'])

        new_row['name_origin'] = row['name_origin']#.replace('Sept 2021','2021').replace('Feb 2021','2020')

        new_row['iteration'] = row['iteration']#.replace('Sept 2021','2021').replace('Feb 2021','2020')
        new_row['crossborder'] = row['crossborder']
        
        super().sort_address_fields(new_row)
        return new_row
    

    def find_primary_name(self,names_list):
        '''names_list is list of tuples (orgname,normname,name_origin)'''
        primary=('','')
        extra_names = set()
        date = datetime(2000,1,1)
        for name in names_list:
            name_tuple = name[:-1]
            if all(x in nulls for x in name_tuple): continue
            name_origin = name[-1]
            #print(f'name_origin = {name_origin}')
            #print(f'name_tuple = {name_tuple}')
            if 'NAME' in name_origin.upper():
                d = datetime.strptime((name_origin.split(' ')[0]),'%m/%Y')
                if d > date:
                    date = d
                    extra_names.add(primary)
                    primary = name_tuple
                    #print(f' -- primary = {primary}')
                    #print(f' -- extra_names = {extra_names}')
            
            extra_names.add(name_tuple)

        extra_names = [i for i in extra_names if i != ('','') and i != primary]
        #print(f'primary name = {primary}')
        #print(f'extra names = {extra_names}')
        return primary,extra_names
    
    def find_primary_info(self,address_list):
        '''address_list is list of tuples (fulladdress,city,postcode,iteration)
        and primary address is that found in most recent iteration'''

        primary = ('','','')
        date = datetime(2000,1,1)
        extra_addresses = []
        for item in address_list:
            address_tuple = item[:-1]
            if all(x in nulls for x in address_tuple): continue
            iteration = item[-1]
            if iteration:
                iteration = datetime.strptime(iteration,'%m/%Y')
                if iteration > date:
                    date = iteration
                    primary = address_tuple

            extra_addresses.append(address_tuple)
            
        extra_addresses = [i for i in extra_addresses if i != primary and i != ('','','')]
        print(f'address_list = {address_list}')
        print(f'primary address = {primary}')
        print(f'extra addresses = {extra_addresses}')
        return primary, extra_addresses





    def combine_org_details_per_source(self, rows: list):
        ''' use data iteration to find primary address, and name_origin field to find 
         primary name. As per ccew, using earliest date for registration and 
          latest for dissolution (though could change this to use the dates in 
          the most recent iteration instead) '''
        
        def fix_dates_set(datesset, order):
            ret = list(datesset)
            ret = [i for i in ret if i !='']
            ret.sort()
            if ret:
                primary = ret[order]
                extra_dates = [i for i in ret if i != primary]
            else:
                return '',''

            return primary,extra_dates
        
        def generate_subspine_and_extras(new_sub_spine_row,names,addresses,regdates,remdates):
            primary_name, extra_names = self.find_primary_name(names)
            primary_address, extra_addresses = self.find_primary_info(addresses)
            primary_regdate, extra_regdates = fix_dates_set(regdates,0) 
            primary_remdate, extra_remdates = fix_dates_set(remdates,-1)
            if primary_name:
                new_sub_spine_row["organisationname"] =  primary_name[0]
                new_sub_spine_row["normalisedname"] =  primary_name[1]
            if primary_address:
                new_sub_spine_row["fulladdress"] =  primary_address[0]
                new_sub_spine_row["city"] =  primary_address[1]
                new_sub_spine_row["postcode"] =  primary_address[2]
            if primary_regdate:
                new_sub_spine_row["registerdate"] =  primary_regdate 
            if primary_remdate:
                new_sub_spine_row["removeddate"] =  primary_remdate 
            new_extra_rows = generate_extra_rows(extra_names,extra_addresses,extra_regdates,extra_remdates)
            print(f'in generate_subspine_and_extras. {len(new_extra_rows)} rows created.')
            print(f'in generate_subspine_and_extras. new subspine row: {new_sub_spine_row}')
            return new_sub_spine_row,new_extra_rows
        
        def generate_extra_rows(names,addresses,regdates,remdates):   
            new_extras_rows = []
            for name in names:
                new_extras_rows.append(
                    extra_csv_entry_creator({
                    "organisationname" : name[0],
                    "normalisedname" : name[1],
                    }))
            for address in addresses:
                new_extras_rows.append(
                    extra_csv_entry_creator({
                    "fulladdress" : address[0],
                    "city" : address[1],
                    "postcode" : address[2]
                    }))
            for date in regdates:
                new_extras_rows.append(
                    extra_csv_entry_creator({
                    "registerdate" : date,
                }))
            for date in remdates:
                new_extras_rows.append(
                    extra_csv_entry_creator({
                    "removeddate" : date
                }))
            print(f'in generate_extra_rows. {len(new_extras_rows)} rows created. \n\n{new_extras_rows}\n\n')
            return new_extras_rows
        
        def merge_extra_rows(new_extra_rows, extra_rows, key_field="uid"):
            """
            Merge extra_rows into new_extra_rows without losing data.
            Rows are merged if possible, otherwise kept as separate rows.
            Multiple rows per uid are allowed.
            """

            def clean(v):
                if v in ("", None) or pd.isna(v):
                    return None
                return str(v).strip()

            def is_compatible(r1, r2):
                """
                True if r1 and r2 can be merged without losing or overwriting info.
                (Shared keys must either match or one must be empty)
                """
                for k in set(r1) | set(r2):
                    v1 = clean(r1.get(k))
                    v2 = clean(r2.get(k))

                    if v1 is not None and v2 is not None and v1 != v2:
                        return False
                return True

            def merged_row(r1, r2):
                """
                Merge two compatible rows, preferring non-empty values.
                """
                merged = {}

                for k in set(r1) | set(r2):
                    v1 = clean(r1.get(k))
                    v2 = clean(r2.get(k))

                    merged[k] = v1 if v1 is not None else v2 if v2 is not None else ""

                return merged

            # Work on a copy so we don't mutate external list
            result = list(new_extra_rows)

            for e in extra_rows:
                if not any(clean(v) for v in e.values()):
                    continue
                
                uid = e.get(key_field)
                if not uid:
                    # No uid → just append
                    result.append(e)
                    continue

                placed = False

                for i, r in enumerate(result):
                    if r.get(key_field) != uid:
                        continue

                    if is_compatible(r, e):
                        new_r = merged_row(r, e)

                        if new_r != r:
                            print(f"\nMERGED for {uid}")
                            print(f"OLD: {r}")
                            print(f"NEW: {new_r}")

                        result[i] = new_r
                        placed = True
                        break

                if not placed:
                    print(f"\nNEW ROW for {uid}: {e}")
                    result.append(e)

            return result        
                


        # ============ END OF EMBEDDED FUNCTIONS =======================================


        
        names = set()
        addresses = set()
        regdates = set()
        remdates = set()
        id_in_source=set()
        new_extras_rows = []
        company_id=''
        uid = rows[0]['uid']
        source = rows[0]['source']
        source_register = rows[0]['source_register']

        for r in rows:
            id_in_source.add(r['id_in_source'])
            if r['companyid']: company_id = r['companyid']
            for field in self.tmp_fields:
                if not field in r.keys(): r[field] = ''
            try:
                n = (r['organisationname'],r['normalisedname'],r['name_origin'])
                a = (r['fulladdress'],r['city'],r['postcode'],r['iteration'])
                reg = r['registerdate']
                dis = r['removeddate']
            except KeyError as e:
                print(f'KeyError searching for names, addresses and/or dates in row {r} : {e}\n')
                return []
            
             
            for var in [(n,names),(a,addresses),(reg,regdates),(dis,remdates)]:
                if var[0]: var[1].add(var[0])
        
        if len(list(id_in_source))>1:
            print(f'Issue with uid {uid}: multiple values for id_in_source: {id_in_source}')
        else:
            id_in_source = list(id_in_source)[0]

        #primary_name, extra_names = self.find_primary_name(names)
        #primary_address, extra_addresses = self.find_primary_info(addresses)
        #primary_regdate, extra_regdates = fix_dates_set(regdates,0) # use earliest registration date
        #primary_remdate, extra_remdates = fix_dates_set(remdates,-1) # use latest removal date
        
        new_sub_spine_row = sub_spine_entry_creator(
            {'uid' : uid,
            "id_in_source" : id_in_source,
            "companyid" : company_id,
            "source" : source,
            "source_register" : source_register})
        
        new_sub_spine_row, extra_rows = generate_subspine_and_extras(new_sub_spine_row,names,addresses,regdates,remdates)
        print('subspine row = ',new_sub_spine_row)
        
        

        for entry in extra_rows:
            entry['uid'] = uid
            entry['source'] = source
            entry['source_register'] = source_register
        print('extras ',extra_rows)
        new_extras_rows = merge_extra_rows(new_extras_rows, extra_rows)

        print(f'returning {new_extras_rows} to base for writing to file')
        '''
        if primary_name:
            new_sub_spine_row["organisationname"] =  primary_name[0]
            new_sub_spine_row["normalisedname"] =  primary_name[1]
        if primary_address:
            new_sub_spine_row["fulladdress"] =  primary_address[0]
            new_sub_spine_row["city"] =  primary_address[1]
            new_sub_spine_row["postcode"] =  primary_address[2]
        if primary_regdate:
            new_sub_spine_row["registerdate"] =  primary_regdate 
        if primary_remdate:
            new_sub_spine_row["removeddate"] =  primary_remdate 

        
        for name in extra_names:
            new_extras_rows.append(
                extra_csv_entry_creator({
                "uid" : r['uid'],
                "organisationname" : name[0],
                "normalisedname" : name[1],
                }))
        for address in extra_addresses:
            new_extras_rows.append(
                extra_csv_entry_creator({
                "uid" : r['uid'],
                "fulladdress" : address[0],
                "city" : address[1],
                "postcode" : address[2]
                }))
        for date in extra_regdates:
            new_extras_rows.append(
                extra_csv_entry_creator({
                "uid" : r['uid'],
                "registerdate" : date,
            }))
        for date in extra_remdates:
            new_extras_rows.append(
                extra_csv_entry_creator({
                "uid" : r['uid'],
                "removeddate" : date
            }))
        for entry in new_extras_rows:
            entry['source'] = r['source']
            entry['source_register'] = r['source_register']
        '''
        return new_sub_spine_row, new_extras_rows


'''
oscr data fields


uid,
charitynumber,
organisationname,
normalisedname,
companyid,
address,
housenumber,
addressline1,
addressline2,
addressline3,
addressline4,
addressline5,
addressline6,
addressline7,
addressline8,
city,
localauthority,
postcode,
registerdate,
removeddate,
name_origin,
iteration,
charitynumber_2012,
companyid1_2012,
companyid2_2012,
companyid3_2012,
source,
crossborder
# crossborder = Should be registered with CCEW too
'''

