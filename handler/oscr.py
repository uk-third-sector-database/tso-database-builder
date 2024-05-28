
from datetime import datetime

from .base import DataHandler
from .base_definitions import sub_spine_entry_creator,extra_csv_entry_creator

exclude_filters = {
    "organisationname": ['N/A']
}


class OSCRDataHandler(DataHandler):
    fileencoding='Latin-1'
    tmp_fields = ['crossborder','name_origin','iteration']

    def all_filters(self,row: dict) -> bool:
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
        except:
            print('error with date',datestr)
        return d.strftime('%d/%m/%Y')
    

    def find_names(self, row) -> list:
        ''' returns name keys which have non-null values'''
        # 
        return ['organisationname']


    def format_row(self,namefield,row) -> dict:
        '''format a row into Spine format, for given namefield'''
        new_row={}
        for field in row:
            row[field] = row[field].strip()


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
        new_row["source"] = row['source']
        new_row["registerdate"] = self.map_date(row['registerdate'])
        new_row["removeddate"] = self.map_date(row['removeddate'])

        new_row['name_origin'] = row['name_origin'].replace('Sept 2021','2021').replace('Feb 2021','2020')

        new_row['iteration'] = row['iteration'].replace('Sept 2021','2021').replace('Feb 2021','2020')
        new_row['crossborder'] = row['crossborder']
        
        super().sort_address_fields(new_row)
        return new_row
    

    def find_primary_name(self,names_list):
        '''names_list is list of tuples (orgname,normname,name_origin)'''
        primary=('','')
        extra_names = set()
        date = 2000
        for name in names_list:
            name_tuple = name[:-1]
            name_origin = name[-1]
            #print(f'name_origin = {name_origin}')
            #print(f'name_tuple = {name_tuple}')
            if 'NAME' in name_origin.upper():
                d = int(name_origin.split(' ')[0])
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
        date = 2000
        extra_addresses = []

        for item in address_list:
            address_tuple = item[:-1]
            iteration = item[-1]
            if iteration:
                iteration = int(iteration)
                if iteration > date:
                    date = iteration
                    primary = address_tuple
            extra_addresses.append(address_tuple)
            
        extra_addresses = [i for i in extra_addresses if i != primary and i != ('','','')]
        #print(f'primary address = {primary}')
        #print(f'extra addresses = {extra_addresses}')
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
        
        names = set()
        addresses = set()
        regdates = set()
        remdates = set()

        for r in rows:
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
                var[1].add(var[0])
                
        primary_name, extra_names = self.find_primary_name(names)
        primary_address, extra_addresses = self.find_primary_info(addresses)
        primary_regdate, extra_regdates = fix_dates_set(regdates,0) # use earliest registration date
        primary_remdate, extra_remdates = fix_dates_set(remdates,-1) # use latest removal date
        
        new_sub_spine_row = sub_spine_entry_creator(
            {'uid' : r['uid'],
            "id_in_source" : r['id_in_source'],
            "companyid" : r['companyid'],
            "source" : r['source'],})
        
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

        new_extras_rows = []
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