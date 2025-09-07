
from datetime import datetime

from .base import DataHandler,sort_encoding_issue
from .base_definitions import sub_spine_entry_creator,extra_csv_entry_creator


exclude_filters = {
    "organisationname": ['N/A']
}


class CCEWDataHandler(DataHandler):
    fileencoding='utf-8' #'Latin-1'
    tmp_fields = ["primary_name","primary_address","cqc_reg",'iteration']
    

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
        new_row["source"] = 'ccew'
        new_row['source_register'] = 'Charity Commission for England and Wales'
        new_row["registerdate"] = self.map_date(row['registerdate'])
        new_row["removeddate"]  = self.map_date(row['removeddate'])
        new_row["primary_name"] = row["primary_name"].replace('other','0')
        new_row["primary_address"] = row["primary_address"].replace('other','0')
        new_row["cqc_reg"] = row["cqc_reg"]
        new_row["iteration"] = row['iteration']

        super().sort_address_fields(new_row)
        return new_row
        


    def find_primary_info(self, s):
        """
        Input: a set of tuples ending with (primary_flag, iteration),
               where iteration is a string like '03/2022'.

        Returns:
            - primary: the selected primary record (tuple without flag/iteration)
            - extra_rows: other non-empty rows that are not the primary

        Original (historic) ccew data had 'primary_flag' set to determine the details 
        for the spine. This needs to be superseded if there are more recent data for an org.
        """
        s = list(s)
        new_s = set()
        primary = None
        primary_iteration = None
        fallback_candidates = []

        for item in s:
            *item_data, primary_flag, iteration_str = item
            item_data = tuple(item_data)
            if all(f == '' for f in item_data):
                continue
            
            iteration = None
            if iteration_str:
                try:
                    if len(iteration_str)==4:
                        iteration = datetime.strptime(iteration_str, "%Y")
                    else:
                        iteration = datetime.strptime(iteration_str, "%m/%Y")
                except ValueError:
                    if iteration_str=='Other':
                        iteration = datetime(2000, 1, 1)
                    else:
                        print(f"Invalid date format: {iteration_str}")
                        return None, None


            fallback_candidates.append((iteration, item_data))

            if primary_flag == '1':
                #if primary is None and any(f != '' for f in item_data):
                if primary_flag =='1' and any(f != '' for f in item_data):
                    primary = item_data
                    primary_iteration = iteration
                else:
                    new_s.add(item_data)  # demote previous or bad primary
            else:
                new_s.add(item_data)

        # Determine the most recent iteration among all candidates
        if fallback_candidates:
            most_recent_iteration, most_recent_data = max(fallback_candidates, key=lambda x: x[0])

            # Replace primary if its iteration is older
            if primary_iteration is None or (most_recent_iteration and primary_iteration and primary_iteration < most_recent_iteration):
                if primary is not None:
                    new_s.add(primary)  # move old primary to extras
                primary = most_recent_data
                primary_iteration = most_recent_iteration

        # Fallback to most recent iteration if needed
        if primary is None or all(f == '' for f in primary):
            if fallback_candidates:
                # Sort by latest iteration first
                fallback_candidates.sort(reverse=True)
                primary = fallback_candidates[0][1]
            else:
                primary = tuple('' for _ in item_data)
        # Build list supplementary data
        extra_rows = [i for i in new_s if i != primary and any(f != '' for f in i)]
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
        company_id = ''
        #print(f"\n\nUID = {rows[0]['uid']}")
        
        # gather up the various options for name, address, and dates
        for r in rows:
#            print(f'row = {r}')
            uid = r['uid']
            for field in self.tmp_fields:
                if not field in r.keys(): r[field] = ''
            try:
                n = (r['organisationname'],r['normalisedname'],r['primary_name'], r['iteration'])
                a = (r['fulladdress'],r['city'],r['postcode'],r['primary_address'], r['iteration'])
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
        
        # find company id:
        for r in rows:
            if r['companyid']:
                company_id = r['companyid']
                break

        primary_name,    extra_names = self.find_primary_info(names)
        try:
            primary_address, extra_addresses = self.find_primary_info(addresses)
        except Exception as e:
            print(f'Error in find_primary_info for addresses: {e} for addresses = {addresses}')


        primary_regdate, extra_regdates = fix_dates_set(regdates,0) # use earliest registration date
        primary_remdate, extra_remdates = fix_dates_set(remdates,-1) # use latest removal date

        #primary details:
        new_sub_spine_row = sub_spine_entry_creator(
            {'uid' : uid,
            "id_in_source" : r['id_in_source'],
            "companyid" : company_id,
            "source_register" : r['source_register'],
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
            entry['source_register'] = r['source_register']


#        print(f'new_sub_spine_row = {new_sub_spine_row}')
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