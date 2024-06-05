import csv
import tempfile
import pandas as pd
import os
from  pydantic import BaseModel
from datetime import datetime

from handler.base_definitions import EXTRA_DETAILS_CSV_FIELDS, SPINE_CSV_FIELDS, MATCHES_CSV_FIELDS, match_csv_entry_creator, ORG_ID_MAPPING

def read_dkane_sameas(file):
    #print(os.getcwd())
    def get_org_code(org_id):
        parts = str(org_id).split('-')
        return parts[1] if len(parts) > 1 else None


    df = pd.read_csv(file,usecols=['org_id_a','org_id_b'])
    df['org_a_code'] = df['org_id_a'].apply(get_org_code)
    df['org_b_code'] = df['org_id_b'].apply(get_org_code)

    codes = set(ORG_ID_MAPPING.values())

    trimmed_df = df[df['org_a_code'].isin(codes) & df['org_b_code'].isin(codes)]

    ftc_dict = {}
    tuples = list(zip(trimmed_df['org_id_a'],trimmed_df['org_id_b']))
    for x,y in tuples:
        if x in ftc_dict:
            ftc_dict[x].append(y)
        else:
            ftc_dict[x] = [y]
        if y in ftc_dict:
            ftc_dict[y].append(x)
        else:
            ftc_dict[y] = [x]

    return ftc_dict
    

ftc_dict = read_dkane_sameas('../raw_data/dkane_relationships_sameas.csv')

class ExtraInfo(BaseModel):
    uid: str
    organisationname: str = ''
    normalisedname: str = ''
    fulladdress: str = ''
    city: str = ''
    postcode: str = ''
    registerdate: str = ''
    removeddate: str = ''
    source: str = ""

    def __eq__(self, value: "ExtraInfo") -> bool:
        return self.model_dump(exclude="source") == value.model_dump(exclude="source")

    def isempty(self):
        fields = list(self.model_fields.keys())
        fields.remove('uid')
        fields.remove('source')
        return all(getattr(self, field) == '' for field in fields)
    
class MatchInfo(BaseModel):
    uid: str
    orgA_id_in_source : str
    orgA_source : str
    orgA_uid : str
    orgB_id_in_source : str
    orgB_source : str
    orgB_uid : str
    match_type : str

class CoreOrganisation(BaseModel): # orgs for public spine
    uid: str
    organisationname: str
    normalisedname: str
    fulladdress: str
    city: str
    postcode: str
    companyid: str
    registerdate: str
    removeddate: str
    source: str
    id_in_source: str
    cqc_reg: str = ""
    crossborder: str = ""

    extras: list[ExtraInfo] = []

    matched_orgs: list = []
    sorted_matches: list[MatchInfo] = []

  #def __str__(self):
  #    return (
  #        f"CoreOrganisation(uid={self.uid}, "
  #        f"organisationname={self.organisationname}, "
  #        f"normalisedname={self.normalisedname}, "
  #        f"fulladdress={self.fulladdress}, "
  #        f"city={self.city}, "
  #        f"postcode={self.postcode}, )"
  #             )

    def to_extra_info(self) -> ExtraInfo:
        
        return ExtraInfo(**self.model_dump())

    
    def to_main_csv(self):
        return self.model_dump(exclude={"extras","matched_orgs","matches"})
        
    def to_extras_csv(self):
        for x in self.extras:
            if not x.isempty():
                yield x.model_dump()


    def to_match_csv(self):
        for m in self.sorted_matches:
            yield m.model_dump()


    def sort_matches(self):
        # decide what goes in main spine and what's in extras

        # all matches considered to create single organisation other than matchtype = 'companyid - companyid' which occurs
        # when two organisations are mapped to the same companyid, which creates a link in the match table but not an identical
        # organisation UNLESS also in the ftc mappings.
        # self.matches is a list of (CoreOrganisation,matchtype) tuples
        # matchtype is in ['companyid - companyid', 'name - cqc', 'name - crossborder', 'companyid - coop mutual', 'companyid - id_in_source', 'ftc']

        matchtype_order = ['ftc', 'name - cqc', 'name - crossborder', 'companyid - coop mutual', 'companyid - id_in_source' , 'name - housing', 'name - care', 'companyid - companyid']


        if len(self.matched_orgs)==0:
            return
        
        new_main_rows = []
        assured_matched_orgs = []

        for matchtype in matchtype_order:
            
            matched_org = [item[0] for item in self.matched_orgs if item[1] == matchtype]
            if not matched_org:
                continue

            matched_org = matched_org[0]


            if not matchtype == 'companyid - companyid':
                assured_matched_orgs.append(matched_org)
                e = matched_org.to_extra_info()
                if not e in self.extras:
                    self.extras.append(e) #matched_org.to_extra_info())
                for e in matched_org.extras:
                    if not e in self.extras:
                        self.extras.append(e)
                self.sorted_matches.append(MatchInfo(uid = self.uid, 
                    orgA_id_in_source = self.id_in_source,
                    orgA_source = self.source,
                    orgA_uid = self.uid,
                    orgB_id_in_source = matched_org.id_in_source,
                    orgB_source = matched_org.source,
                    orgB_uid = matched_org.uid,
                    match_type = matchtype))

            else:
                if not matched_org in assured_matched_orgs:
                    if not matched_org.source.lower() in ['careinspectoratescot','carequalitycommission']:
                        new_main_rows.append(matched_org)
                    
                    self.sorted_matches.append(MatchInfo(uid = '', 
                    orgA_id_in_source = self.id_in_source,
                    orgA_source = self.source,
                    orgA_uid = self.uid,
                    orgB_id_in_source = matched_org.id_in_source,
                    orgB_source = matched_org.source,
                    orgB_uid = matched_org.uid,
                    match_type = matchtype))

            
        return new_main_rows


    def sort_extras(self):
        # Helper function to handle date parsing
        def parse_date(date_str):
            if date_str:
                return datetime.strptime(date_str, '%d/%m/%Y')
            return None

        # Processing of self.extras to find the most recent removeddate, and the earliest registerdate
        def fix_dates_set(dates_set, order):
            ret = list(dates_set)
            ret = [i for i in ret if i is not None]
            ret.sort()
            if ret:
                primary = ret[order]
            else:
                return None
            return primary

        registerdates = []
        removeddates = []

        for e in self.extras:
            if e.registerdate:
                registerdates.append(parse_date(e.registerdate))
            if e.removeddate:
                removeddates.append(parse_date(e.removeddate))

        earliest_register = fix_dates_set(registerdates, 0)
        latest_removed = fix_dates_set(removeddates, -1)

        if earliest_register:
            orgregdate = parse_date(self.registerdate)
            if not orgregdate:
                self.registerdate = earliest_register.strftime('%d/%m/%Y')
            elif earliest_register < orgregdate:
                self.extras.append(ExtraInfo(uid = self.uid, source=self.source, registerdate=self.registerdate))
                self.registerdate = earliest_register.strftime('%d/%m/%Y')

        if latest_removed:
            orgremdate = parse_date(self.removeddate)
            if not orgremdate:
                self.removeddate = latest_removed.strftime('%d/%m/%Y')
            elif latest_removed > orgremdate:
                self.extras.append(ExtraInfo(uid = self.uid, source=self.source, removeddate=self.removeddate))
                self.removeddate = latest_removed.strftime('%d/%m/%Y')

        # if address info missing in primary data, find in extras? Add here if so.


        for x in self.extras:       
            if (self.organisationname == x.organisationname) and (self.normalisedname == x.normalisedname):
                x.normalisedname=''
                x.organisationname=''
            if (self.fulladdress == x.fulladdress) and (self.postcode == x.postcode) and (self.city == x.city):
                x.fulladdress = ''
                x.postcode=''
                x.city=''
            if self.registerdate == x.registerdate:
                x.registerdate=''
            if self.removeddate == x.removeddate:
                x.removeddate=''
    
        self.extras = [e for e in self.extras if not e.isempty()]


class SubSpineOrg(BaseModel):  # sub spine format (per source)
    uid: str
    organisationname: str
    normalisedname: str
    fulladdress: str
    city: str
    postcode: str
    companyid: str
    registerdate: str
    removeddate: str
    source: str
    id_in_source: str
    crossborder: str = ""
    cqc_reg: str = ""

    extras: list[ExtraInfo] = []

    def to_extra_info(self) -> ExtraInfo:
        #print(self.model_dump())
        return ExtraInfo(**self.model_dump())


    def to_core_org(self) -> CoreOrganisation:
        kwargs = self.model_dump()
        return CoreOrganisation(**kwargs)


    def matches(self, byname:dict, bycompanyid:dict, bysourceid:dict, spinelist:dict):
        #print('in SubSpineOrg.matches')

        # TO DO: we also want to look for matches in extras - spinelist[org].extras.[companyid | normalisedname] - perhaps this needs an inverse dictionary too?
        # TO DO: need to also look in org.matched_orgs so we don't miss anything.

        matches_here = []
        
        if self.companyid and (self.companyid in bycompanyid):
            match = bycompanyid[self.companyid]
#            print(f' --- match on companyid {self.companyid}')
            matches_here.extend([(i, 'companyid - companyid') for i in match])

        if self.normalisedname in byname: 
            match = byname[self.normalisedname]
            if self.source == 'cqc' and any(x.cqc_reg == '1' for x in match): # need to make this work by adding cqc_reg field to core orgs so we don't lose this info
#                print(f' --- match on normalisedname {self.normalisedname}')
                matches_here.extend([(i, 'name - cqc') for i in match])
                
            if self.crossborder=='1':# and any(x.source.lower() in ['ccew','ccni'] for x in match): # allow matches by name if we expect a match
#                print(f' --- crossborder match found for {self.normalisedname} (match.source = {[x.source.lower() for x in match]})')
                matches_here.extend([(i, 'name - crossborder') for i in match])

            if self.source.lower() == 'scottishhousingregulator' and any(x.source.lower == 'oscr' for x in match):
#                print(f' --- SHR match found for {self.normalisedname}')
                matches_here.extend([(i, 'name - housing') for i in match])   

            if self.source.lower() == 'socialhousingengland' and any(x.source.lower() == 'ccew' for x in match):
#                print(f' --- SHE match found for {self.normalisedname}')
                matches_here.extend([(i, 'name - housing') for i in match])   

            if self.source.lower() == 'careinspectoratescot' and any(x.source.lower() == 'oscr' for x in match):
#                print(f' --- CIS name match found for {self.normalisedname}')
                matches_here.extend([(i, 'name - care') for i in match])   


            if self.source.lower() == 'carequalitycommission' and any(x.source.lower() == 'ccew' for x in match):
#                print(f' --- cqc name match found for {self.normalisedname}')
                matches_here.extend([(i, 'name - care') for i in match])   

                
        if self.companyid in bysourceid:
            match = bysourceid[self.companyid]
            #for m in match:
            if self.source.lower() == 'coops' and any(x.source.lower() in ['mutuals','ch'] for x in match): #(m.source.lower() == 'mutuals' or m.source.lower() == 'ch'):
#                print(f' --- coops and mutuals match (X) found for {self.normalisedname}, {self.companyid}')
                matches_here.extend([(i, 'companyid - coop mutual') for i in match])
            elif self.source.lower() == 'mutuals' and any(m.source.lower() == 'coops' for m in match):
#                print(f' --- coops and mutuals match (Y) found for {self.normalisedname}, {self.companyid}')
                matches_here.extend([(i, 'companyid - coop mutual') for i in match])

               
                
        if self.id_in_source in bycompanyid:
            match = bycompanyid[self.id_in_source]
            if self.source.lower() == 'ch':
                # companies house counterpart to charity
#                print(f' --- companies house match found for {self.normalisedname}, {self.companyid}')
                matches_here.extend([(i, 'companyid - id_in_source') for i in match])
            for m in match:
                if self.source.lower() == 'mutuals' and m.source.lower() == 'coops':
#                    print(f' --- coops and mutuals match (Z) found for {self.normalisedname}, {self.companyid}')
                    matches_here.extend([(i, 'companyid - coop mutual') for i in match])
            
        # find matches in dkane _sameas csv
        if self.uid in ftc_dict:
            matched_uids = ftc_dict[self.uid]
            for m in matched_uids:
                if m in spinelist:
#                    print(f' --- FTC match found for {self.normalisedname}, {self.uid} with {spinelist[m].normalisedname}, {spinelist[m].uid}')
                    matches_here.append((spinelist[m],'ftc')) 
    

        return matches_here




class MainOrgList:
    def __init__(self):
        self._store: dict[str, CoreOrganisation] = {}
        self.byname: dict[str, list[CoreOrganisation]] = {}
        self.bycompanyid: dict[str, list[CoreOrganisation]] = {}
        self.bysourceid: dict[str, list[CoreOrganisation]] = {}


    def __iter__(self):
        return iter(self._store)
    
    def add_to_stores(self, org):#:SubSpineOrg):

        def add_to_dict(dictionary, key, org):
            if key:
                if key not in dictionary:
                    dictionary[key] = [org]
                elif org not in dictionary[key]:
                    dictionary[key].append(org)


        if isinstance(org, SubSpineOrg):
            new_core_org = org.to_core_org()
            self._store[org.uid] = new_core_org



            add_to_dict(self.byname, org.normalisedname, new_core_org)
            if org.companyid and org.companyid != '0' * len(org.companyid):
                add_to_dict(self.bycompanyid, org.companyid, new_core_org)
            add_to_dict(self.bysourceid, org.id_in_source, new_core_org)
            


        # also add the keys for anything in org.matched_orgs
        if isinstance(org, CoreOrganisation):
            for m,matchtype in org.matched_orgs:
                add_to_dict(self.byname, m.normalisedname, org)
                if m.companyid and m.companyid != '0' * len(m.companyid):
                    add_to_dict(self.bycompanyid, m.companyid, org)
                add_to_dict(self.bysourceid, m.id_in_source, org)

        
        

    def old_add_to_stores(self,org):
        if isinstance(org,SubSpineOrg):
            new_core_org = org.to_core_org()
            self._store[org.uid] = new_core_org




            if not org.normalisedname in self.byname:
                self.byname[org.normalisedname] = [new_core_org]
            elif new_core_org not in self.byname[org.normalisedname]:
                self.byname[org.normalisedname].append(new_core_org)

            if org.companyid and org.companyid != '0'*len(org.companyid):
                if not org.companyid in self.bycompanyid:
                    self.bycompanyid[org.companyid] = [new_core_org]
                elif new_core_org not in self.bycompanyid[org.companyid]:
                    self.bycompanyid[org.companyid].append(new_core_org)

            if not org.id_in_source in self.bysourceid:
                self.bysourceid[org.id_in_source] = [new_core_org]
            elif new_core_org not in self.bysourceid[org.id_in_source]:
                self.bysourceid[org.id_in_source].append(new_core_org)


        # also add the keys for anything in org.matched_orgs
        if isinstance(org,CoreOrganisation):
            for m in org.matched_org:
                if not m.normalisedname in self.byname:
                    self.byname[m.normalisedname] = [org]
                elif org not in self.byname[m.normalisedname]:
                    self.byname[m.normalisedname].append(org)

                if m.companyid and m.companyid != '0'*len(m.companyid):
                    if not m.companyid in self.bycompanyid:
                        self.bycompanyid[m.companyid] = [org]
                    elif org not in self.bycompanyid[m.companyid]:
                        self.bycompanyid[m.companyid].append(org)

                if not m.id_in_source in self.bysourceid:
                    self.bysourceid[m.id_in_source] = [org]
                elif org not in self.bysourceid[m.id_in_source]:
                    self.bysourceid[m.id_in_source].append(org)

        

        #print(f'\n\n are stores updated?? \
        #     \nself.store.keys = {self._store.keys()}\
        #     \nself.byname.keys() = {self.byname.keys()}\
        #     \nself.bycompanyid.keys() = {self.bycompanyid.keys()}\
        #     \nself.bysourceid.keys() = {self.bysourceid.keys()}\n\n')

    def merge(self, orgs: list[SubSpineOrg]):

        for org in orgs:
            matched_org = org.matches(self.byname,self.bycompanyid,self.bysourceid, self._store)
            if matched_org:
   
                # add this org to all matched org already in the spine:
                for o,matchtype in matched_org: # o is higher up the precedence order than org
                    o.matched_orgs.append((org,matchtype))
                    self.add_to_stores(o)

            else:
                self.add_to_stores(org)



    def restore_from_csv(self, filename_main: str, filename_extras: str):
        with open(filename_main) as in_main:
            main_csv = csv.DictReader(in_main)
            for main_row in main_csv:
                new_org = CoreOrganisation(**main_row)
                self._store[new_org.id] = new_org

            with open(filename_extras) as in_extras:
                extras_csv = csv.DictReader(in_extras)
                for extras_row in extras_csv:
                    main_row = self._store[extras_row["uid"]]
                    main_row.extras.append(ExtraInfo(**extras_row))


    def sort_matches(self):
        new_store_items = []
        for org in self._store.values():
            for_store = org.sort_matches()
            if for_store:
                new_store_items.extend(for_store)

        for s in new_store_items:
            self.add_to_stores(s)

    def sort_extras(self):
        for org in self._store.values():
            org.sort_extras()


    def write_out(self, filename_main: str, filename_extras: str, filename_matches: str):

        self.sort_matches()
        print('\n\nsort_matches complete.')

        self.sort_extras()
        print('\n\nsort_extras complete.')


        with open(filename_main, "w+") as out_main:
            with open(filename_extras, "w+") as out_extras:
                with open(filename_matches, 'w+') as out_matches:
                    #csv_keys = list(CoreOrganisation.model_fields.keys())
                    #csv_keys.remove("extras")
                    main_csv = csv.DictWriter(out_main, fieldnames=SPINE_CSV_FIELDS)
                    extras_csv = csv.DictWriter(out_extras, fieldnames=EXTRA_DETAILS_CSV_FIELDS)
                    matches_csv = csv.DictWriter(out_matches,fieldnames=MATCHES_CSV_FIELDS)
                    for csv_x in [main_csv,extras_csv,matches_csv]:
                        csv_x.writeheader()

                    for org in self._store.values():
                        if org.source.lower() in ['careinspectoratescot','carequalitycommission']:
                            continue
                        
                        for row in [org.to_main_csv()]:
                            filtered_row = {key: row[key] for key in SPINE_CSV_FIELDS if key in row}
                            main_csv.writerow(filtered_row)
                        
                        for row in org.to_extras_csv():
                            filtered_row = {key: row[key] for key in EXTRA_DETAILS_CSV_FIELDS if key in row}
                            extras_csv.writerow(filtered_row)
                        
                        for row in org.to_match_csv():
                            matches_csv.writerow(row)



def convert_csv_to_list_of_subspine_orgs(csv_file: str) -> list[SubSpineOrg]:
    
    file_root, file_ext = os.path.splitext(csv_file)
    supp_file = file_root + '.supplementary.csv'
    
    extras_dict = {}
    if os.path.exists(supp_file):
        with open(supp_file) as supp_csv:
            csv_reader = csv.DictReader(supp_csv)
            for row in csv_reader:
                uid = row['uid']
                if not uid in extras_dict:
                    extras_dict[uid] = [ExtraInfo(**row)]
                else:
                    extras_dict[uid].append(ExtraInfo(**row))
    else:
        print(f'Missing supplementary file {supp_file}')

    orglist = []
    with open(csv_file) as in_csv:
        csv_reader = csv.DictReader(in_csv)
        for row in csv_reader:
            if any(field.strip() for field in row.values()):
                try:
                    neworg = SubSpineOrg(**row)
                except TypeError as e:
                    print(f'{e} : row = {row}')
                if neworg.uid in extras_dict:
                    neworg.extras = extras_dict[neworg.uid]
                orglist.append(neworg)


    

    print(f'PROCESS: Files ingested: {len(orglist)} organisations, of which {len([x for x in orglist if x.extras])} have supplementary information')
    return orglist


def process_csvs_to_build_spine(csv_file_list_order):
    main_orgs = MainOrgList()
    for csv_file in csv_file_list_order:
        print(f'\n\n------------------ PROCESS: Processing file {csv_file} ------------------')

        base_orgs = convert_csv_to_list_of_subspine_orgs(csv_file)
        #print(f'\n\nbase_orgs = {base_orgs}\n\n')
        main_orgs.merge(base_orgs)

        print(f'\nPROCESS: Orgs merged into main spine: {len(main_orgs._store.keys())} organisations, of which {len([x for x in main_orgs._store.keys() if main_orgs._store[x].matched_orgs])} have matched orgs\n\n')

        

    return main_orgs

