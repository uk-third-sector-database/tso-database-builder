
from datetime import datetime

from .base import DataHandler,sort_encoding_issue
from .base_definitions import sub_spine_entry_creator,extra_csv_entry_creator


exclude_filters = {
    "organisationname": ['N/A']
}


class CCEWDataHandler(DataHandler):
    fileencoding='utf-8' #'Latin-1'
    tmp_fields = ["primary_name","primary_address","cqc_reg"]
    

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
        except:
            print('error with date',datestr)
        return d.strftime('%d/%m/%Y')


    def find_names(self, row) -> list:
        ''' returns name keys which have non-null values'''
        # 
        return ['organisationname']


    def format_row(self,namefield,row) -> dict:
        '''format a row into Sub-Spine format, for given namefield'''
        new_row={}
            
        new_row["uid"] =  'GB-CHC-'+ row['charitynumber']   
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
        new_row["city"] = row['city']
        new_row["postcode"] = row['postcode']
        new_row["source"] = row['source']
        new_row["registerdate"] = self.map_date(row['registerdate'])
        new_row["removeddate"]  = self.map_date(row['removeddate'])
        new_row["primary_name"] = row["primary_name"].replace('other','0')
        new_row["primary_address"] = row["primary_address"].replace('other','0')
        new_row["cqc_reg"] = row["cqc_reg"]

        super().sort_address_fields(new_row)
        return new_row
        

    def find_primary_info(self,s):
        '''input is a set generated in combine_org_details_per_source.
        Find primary details and return as list, where list[0] is primary'''
        s = list(s)
        new_s = set()
        primary = ()
        
        for item in s:
            item_data = item[:-1]
            
            primary_flag = item[-1]
            if primary_flag == '1':
                if len(primary) == 0:
                    primary = item_data
                else:
                    new_s.add(primary)
                    primary = ()
            new_s.add(item_data)

        if len(primary) == 0:
            primary = ('',)*len(item_data)

        extra_rows = [i for i in new_s if (i != primary) and 
                      not all(f == '' for f in i)]

        return primary, extra_rows


    def combine_org_details_per_source(self, rows):

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

        #print('in combine org details per source (ccew)')
        names = set()
        addresses = set()
        regdates = set()
        remdates = set()
        cqc_reg = False
        
        
        # gather up the various options for name, address, and dates
        for r in rows:
            uid = r['uid']
            for field in self.tmp_fields:
                if not field in r.keys(): r[field] = ''
            try:
                n = (r['organisationname'],r['normalisedname'],r['primary_name'])
                a = (r['fulladdress'],r['city'],r['postcode'],r['primary_address'])
                reg = r['registerdate']
                dis = r['removeddate']
                if r['cqc_reg']:
                    if r['cqc_reg'] == '1':
                        cqc_reg = True
            except KeyError as e:
                print(f'KeyError searching for names, addresses and/or dates in row {r} : {e}\n')
                return []
            
            for var in [(n,names),(a,addresses),(reg,regdates),(dis,remdates)]:
                var[1].add(var[0])
                

        primary_name,    extra_names = self.find_primary_info(names)
        primary_address, extra_addresses = self.find_primary_info(addresses)
        primary_regdate, extra_regdates = fix_dates_set(regdates,0) # use earliest registration date
        primary_remdate, extra_remdates = fix_dates_set(remdates,-1) # use latest removal date

        #primary details:
        new_sub_spine_row = sub_spine_entry_creator(
            {'uid' : uid,
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
        if cqc_reg:
            new_sub_spine_row['cqc_reg'] = 1
        
        

        # add remaining names and addresses to extra_rows
        new_extras_rows = []
        for name in extra_names:
            new_extras_rows.append(
                extra_csv_entry_creator({
                "uid" : uid,
                "organisationname" : name[0],
                "normalisedname" : name[1],
                }))
            
        for address in extra_addresses:
            new_extras_rows.append(
                extra_csv_entry_creator({
                "uid" : uid,
                "fulladdress" : address[0],
                "city" : address[1],
                "postcode" : address[2]
                }))
        
        for date in extra_regdates:
            new_extras_rows.append(
                extra_csv_entry_creator({
                "uid" : uid,
                "registerdate" : date,
            }))

        for date in extra_remdates:
            new_extras_rows.append(
                extra_csv_entry_creator({
                "uid" : uid,
                "removeddate" : date
            }))

        for entry in new_extras_rows:
            entry['source'] = r['source']

        return new_sub_spine_row,new_extras_rows
        

'''
ccew data fields
[for public spine]
uid,charitynumber,organisationname,normalisedname,companyid,housenumber,addressline1,addressline2,addressline3,addressline4,addressline5,
city,localauthority,postcode,registerdate,removeddate,name_origin,address_origin,regdate_origin,remdate_origin,iteration,source,
cqc_reg 

uid,charitynumber,organisationname,normalisedname,companyid,housenumber,addressline1,addressline2,addressline3,addressline4,addressline5,
city,localauthority,postcode,registerdate,removeddate,name_origin,primary_name,address_origin,primary_address,regdate_origin,remdate_origin,iteration,source,cqc_reg

#cqc_reg = should be registered in CQC too

'''

'''
(.tso) fionack@Fionas-MacBook-Air tso-database-builder % grep 'Ã^ÃÂ' ../raw_data/ccew_spine_public.csv|wc -l
     372
(.tso) fionack@Fionas-MacBook-Air tso-database-builder % grep 'Ã^ÃÂ' ../public_spine_data/ccew.spine.csv|wc -l
     146
(.tso) fionack@Fionas-MacBook-Air tso-database-builder % grep 'Ã^ÃÂ' ../public_spine_data/ccew.spine.supplementary.csv|wc -l
     227
     '''