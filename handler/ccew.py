
from datetime import datetime
import pandas as pd

from .base import DataHandler,sort_encoding_issue
from .base_definitions import sub_spine_entry_creator,extra_csv_entry_creator
nulls = (None, '', [], {}, ())

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
            
        new_row["uid"] =  'GB-CHC-'+ row['charitynumber'].split('-')[0]  
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
        
    def iteration_datetime(self,d):
        try:
            if len(d)==4:
                iteration = datetime.strptime(d, "%Y")
            else:
                iteration = datetime.strptime(d, "%m/%Y")
        except ValueError:
            if d=='Other':
                iteration = datetime(2000, 1, 1)
            else:
                print(f"Invalid date format: {d}")
                return None
        return iteration

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
            if all(f in nulls for f in item_data):
                continue
            
            iteration = None
            if iteration_str:
                iteration = self.iteration_datetime(iteration_str)
                if not iteration:
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
        # rows is a list of csv dictionaries. Each item is one row from pre-processed data.
        # all rows share the same uid, however may not share the same id_in_source, 
        # which is what we want to condition our primary selection on if '-0' exists


        # ================ EMBEDDED FUNCTIONS ===========================

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

        def create_umbrella_rows(umbrella_rows,cqc_reg,company_id):
            # collect most recent data from umbrella_rows for subspine entry,
            # and create extra_csv_entries for any additional (previous) data.

            names = {(r['organisationname'], r['normalisedname'], '', r['iteration']) for r in umbrella_rows}
            addresses = {(r['fulladdress'],r['city'],r['postcode'],'', r['iteration']) for r in umbrella_rows}
            regdates = {r['registerdate'] for r in umbrella_rows}
            remdates = {r['removeddate'] for r in umbrella_rows}

            new_sub_spine_row = sub_spine_entry_creator(
                {'uid' : r['uid'],
                "id_in_source" : r['id_in_source'],
                "companyid" : company_id,
                "source_register" : r['source_register'],
                "source" : r['source'],})
            if cqc_reg: new_sub_spine_row['cqc_reg'] = 1

            return generate_subspine_and_extras(new_sub_spine_row,names,addresses,regdates,remdates)

        def generate_subspine_and_extras(new_sub_spine_row,names,addresses,regdates,remdates):

            primary_name, extra_names = self.find_primary_info(names)
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
#            print(f'in generate_subspine_and_extras. {len(new_extra_rows)} rows created.')
#            print(f'in generate_subspine_and_extras. new subspine row: {new_sub_spine_row}')
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
            #print(f'in generate_extra_rows. {len(new_extras_rows)} rows created.')
            return new_extras_rows



        def generate_extra_rows_umbrella(names, addresses, regdates, remdates):

            names = list(names)
            addresses = list(addresses)
            regdates = list(regdates)
            remdates = list(remdates)

            new_extras_rows = []
            max_len = max(len(names), len(addresses), len(regdates), len(remdates), 1)

            for i in range(max_len):
                row = {}

                if i < len(names):
                    row["organisationname"] = names[i][0]
                    row["normalisedname"] = names[i][1]

                if i < len(addresses):
                    row["fulladdress"] = addresses[i][0]
                    row["city"] = addresses[i][1]
                    row["postcode"] = addresses[i][2]

                if i < len(regdates):
                    row["registerdate"] = regdates[i]

                if i < len(remdates):
                    row["removeddate"] = remdates[i]

                if row:
                    new_extras_rows.append(extra_csv_entry_creator(row))
            return new_extras_rows



        def extras_for_umbrella_org(non_primary_rows):
            # takes a set of rows which share the same id_in_source and should be consolidated
            # as original code, keeping names and addressses together and removing duplicates
            names=set()
            addresses=set()
            regdates=set()
            remdates=set()

            for r in non_primary_rows:
                n = (r['organisationname'],r['normalisedname'])#,r['primary_name'], r['iteration'])
                a = (r['fulladdress'],r['city'],r['postcode'] )#,r['primary_address'], r['iteration'])
                reg = r['registerdate']
                dis = r['removeddate']
                for var in [(n,names),(a,addresses),(reg,regdates),(dis,remdates)]:
                    if var[0]: var[1].add(var[0])

            return generate_extra_rows_umbrella(names,addresses,regdates,remdates)




        def merge_extra_rows(new_extra_rows, extra_rows, key_field="normalisedname"):
            """
            Merge extra_rows into new_extra_rows without losing data.
            Rows are merged if possible, otherwise kept as separate rows.
            Multiple rows per normalisedname are allowed.
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
                
                normalisedname = e.get(key_field)
                if not normalisedname:
                    # No normalisedname → just append
                    result.append(e)
                    continue

                placed = False

                for i, r in enumerate(result):
                    if r.get(key_field) != normalisedname:
                        continue

                    if is_compatible(r, e):
                        new_r = merged_row(r, e)

                        #if new_r != r:
                        #    print(f"\nMERGED for {normalisedname}")
                        #    print(f"OLD: {r}")
                        #    print(f"NEW: {new_r}")

                        result[i] = new_r
                        placed = True
                        break

                if not placed:
                    #print(f"\nNEW ROW for {normalisedname}: {e}")
                    result.append(e)

            return result

        '''
        def merge_extra_rows(new_extra_rows, extra_rows, key_field="normalisedname"):
            """
            Merge extra_rows into new_extra_rows, keeping only the richest row per normalisedname.

            Parameters
            ----------
            new_extra_rows : list of dict
                Existing collection of extra rows.
            extra_rows : list of dict
                Newly collected rows to evaluate and merge.
            key_field : str
                The dict key to use as the unique identifier. Default is 'normalisedname'.

            Returns
            -------
            list of dict
                Updated new_extra_rows with only the most complete rows preserved per normalisedname.
            """

            def compare_rows(r1, r2):
                """Return 1 if r1 is richer, -1 if r2 is richer, 0 if equal/incomparable."""
                def count_filled(row):
                    return sum(1 for v in row.values() if v not in ("", None) and not pd.isna(v))
                r1_count = count_filled(r1)
                r2_count = count_filled(r2)
                if r1_count > r2_count:
                    return 1
                elif r2_count > r1_count:
                    return -1
                else:
                    return 0

            # Build index of current rows by normalisedname
            index = {r[key_field]: r for r in new_extra_rows if key_field in r and r[key_field]}

            for e in extra_rows:
                if not any(e.values()):  # skip fully empty rows
                    continue
                key = e.get(key_field)
                if not key:
                    # No normalisedname → append as is
                    new_extra_rows.append(e)
                    continue

                if key in index:
                    cmp = compare_rows(e, index[key])
                    if cmp == 1:  # e is richer
                        #print(f"Replacing row for '{key}':\n  old: {index[key]}\n  new: {e}")
                        index[key] = e
                else:
                    index[key] = e

            return list(index.values())
        
        
        '''
        def check_for_old_data(subspine:dict,datarows:list[dict]):
            '''Called if umbrella row AND removed: find datafields from datarows
            for address and dates if they're null in subspine row'''
            null_fields = []
            for field,value in subspine.items():
                if not value: null_fields.append(field)
            
            for field in null_fields:
                collection={}
                for row in datarows:
                    if row[field]:
                        collection[self.iteration_datetime(row['iteration'])]=row[field]
                if collection:
                    most_recent_data, _ = fix_dates_set(collection.keys(),0)
                    subspine[field] = collection[most_recent_data]
            #        print(f'added data {subspine[field]} to {field}')
            return subspine

        # ============ END OF EMBEDDED FUNCTIONS =======================================



        # set up defaults
        names = set()
        addresses = set()
        regdates = set()
        remdates = set()
        cqc_reg = False
        company_id = ''
        umbrella_charity_found=False
        charity_removed=False
        umbrella_id = ''
        new_extra_rows = []
        source_id_dict = {}
        uid = rows[0]['uid']
        source = rows[0]['source']
        source_register = rows[0]['source_register']


        # cycle through rows collecting the above information

        for r in rows:
            if r['companyid']: company_id = r['companyid']
            if r['removeddate']: charity_removed=True
            if r['id_in_source'].endswith('-0'): 
                umbrella_charity_found = True
                umbrella_id = r['id_in_source']
            if r['cqc_reg'] == '1': cqc_reg = True

            for field in self.tmp_fields: 
                if not field in r.keys(): r[field] = ''
            if not r['id_in_source'] in source_id_dict.keys():
                source_id_dict[r['id_in_source']] = [r]
            else:
                source_id_dict[r['id_in_source']].append(r)

            n = (r['organisationname'],r['normalisedname'],r['primary_name'], r['iteration'])
            a = (r['fulladdress'],r['city'],r['postcode'],r['primary_address'], r['iteration'])
            reg = r['registerdate']
            dis = r['removeddate']

            for var in [(n,names),(a,addresses),(reg,regdates),(dis,remdates)]: 
                if var[0]: var[1].add(var[0])


        if umbrella_charity_found: 
            # if there's an umbrella charity, we want to prioritise its name and details for the spine 
            new_sub_spine_row, extra_rows = create_umbrella_rows(source_id_dict[umbrella_id],cqc_reg,company_id)
            if charity_removed:
                # if it's been removed, we might only have its details from older data, which might not have the '-0' tag.
                # here we need to find the old data for new_sub_spine_row, as it might not be in the downloads 
                base_uid = umbrella_id.split('-0')[0]
                if base_uid in source_id_dict.keys():
                    new_sub_spine_row = check_for_old_data(new_sub_spine_row,source_id_dict[umbrella_id.split('-0')[0]])
            new_extra_rows = merge_extra_rows(new_extra_rows, extra_rows)
            #print(f'Extras from creating umbrella row = {len(new_extra_rows)}')
            for id,datarows in source_id_dict.items():
                #print(id)
                if id == umbrella_id: continue
                new_extra_rows = merge_extra_rows(new_extra_rows, extras_for_umbrella_org(datarows))
#                print(f'Extras after umbrella row = {len(new_extra_rows)}')

        else:
            new_sub_spine_row = sub_spine_entry_creator(
                {'uid' : uid,
                "id_in_source" : uid,
                "companyid" : company_id,
                "source_register" : source_register,
                "source" : source,})


            new_sub_spine_row, extra_rows = generate_subspine_and_extras(new_sub_spine_row,names,addresses,regdates,remdates)
            new_extra_rows = merge_extra_rows(new_extra_rows, extra_rows)

        for entry in new_extra_rows:
            entry['uid'] = uid
            entry['source'] = source
            entry['source_register'] = source_register

        return new_sub_spine_row,new_extra_rows







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