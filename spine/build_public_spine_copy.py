import csv
import pandas as pd
import os
from  pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime
from memory_profiler import profile
from tqdm import tqdm  

from handler.base_definitions import EXTRA_DETAILS_CSV_FIELDS, SPINE_CSV_FIELDS, MATCHES_CSV_FIELDS, ORG_ID_MAPPING, SAMEAS_FILE, OSCR_LINKS_FILE


source_precedence_order = [
    'ccew',
    'oscr',
    'ccni',
    'mutuals',
    'ch',
    'coops',
    'scottishhousingregulator',
    'socialhousingengland',
    'careinspectoratescot',
    'carequalitycommission']


debug_uids = {
    'GB-CHC-1135523',# c - DAWLISH CHRISTIAN FELLOWSHIP
    'GB-CHC-1175498',# b - LAWYERS FOR PALESTINIAN HUMAN RIGHTS
    'GB-CHC-1142158',# e - LAWYERS FOR PALESTINIAN HUMAN RIGHTS
    'GB-COH-10972293',# f - LAWYERS FOR PALESTINIAN HUMAN RIGHTS
    'GB-CHC-1178345',}# a - HOPE CHURCH / DAWLISH CHRISTIAN FELLOWSHIP
#'GB-CHC-245698',
#'GB-SC-SC033491',
#'GB-MPR-31169R',
#'GB-CIS-CS2012306141',}
#   'GB-CIS-CS2004075277',
#'GB-CIS-CS2004075279',
#'GB-CIS-CS2004075290',
#'GB-CIS-CS2004075293',
#'GB-CIS-CS2004075297',
#'GB-CIS-CS2004075301',
#'GB-CIS-CS2004075303',
#'GB-CIS-CS2004075307',
#'GB-CIS-CS2004075308',
#'GB-CIS-CS2006116474',
#'GB-CIS-CS2006124410',
#'GB-CIS-CS2011298798',
#'GB-CIS-CS2011298803',
#'GB-CIS-CS2012306141',
#'GB-CIS-CS2014333203',
#'GB-CIS-CS2014333209',
#'GB-CIS-CS2014333292',
#'GB-CIS-CS2015341633',
#'GB-CIS-CS2015341636',
#'GB-CIS-CS2016351073',
#'GB-CIS-CS2019376641',
#'GB-CIS-CS2020378748',
#'GB-CIS-CS2020378749',
#'GB-CIS-CS2021000227',
#'GB-CIS-CS2021000228'}
#    'GB-SC-SC005117',
#    'GB-CHC-224469',
#    'GB-COH-00214077',
#    'GB-CHC-218186',
#    'GB-COH-00552847',
#    'GB-SC-SC038925',
#    'GB-CQC-1-101678950',
#    'GB-CIS-CS2003015115', 'GB-CIS-CS2004079574', 'GB-CIS-CS2004079575', 'GB-CIS-CS2007143010',
#    'GB-CIS-CS2003000232',
# 'GB-CIS-CS2003000237',
# 'GB-CIS-CS2003000787',
# 'GB-CIS-CS2003000828',
# 'GB-CIS-CS2003000829',
# 'GB-CIS-CS2003000830',
 #'GB-CIS-CS2003000831',
 #'GB-CIS-CS2003000865',
 #'GB-CIS-CS2003000929',
 #'GB-CIS-CS2003000932',
 #'GB-CIS-CS2003000933',
 #'GB-CIS-CS2003000934',
# 'GB-SC-SC006878',
# 'GB-MPR-1692RS',
# 'GB-COH-SP1692RS'
#
#}



def read_dkane_sameas(file):

    def get_org_code(org_id):
        parts = str(org_id).split('-')
        return parts[1] if len(parts) > 1 else None

    wanted_cols = ['org_id_a', 'org_id_b', 'source']

    try:
        df = pd.read_csv(file,low_memory=False)
    except OSError as e:
        print(f'Error reading file {file} in function read_dkane_sameas: {e}')
        return {}, []

    # Ensure required columns exist
    for col in wanted_cols:
        if col not in df.columns:
            df[col] = None

    df = df[wanted_cols]

    df['org_a_code'] = df['org_id_a'].apply(get_org_code)
    df['org_b_code'] = df['org_id_b'].apply(get_org_code)

    codes = set(ORG_ID_MAPPING.values())

    trimmed_df = df[
        df['org_a_code'].isin(codes) &
        df['org_b_code'].isin(codes)
    ]

    ftc_dict = {}

    tuples = list(zip(
        trimmed_df['org_id_a'],
        trimmed_df['org_id_b'],
        trimmed_df['source'],
    ))

    primary_orgs = []

    for x, y, source in tuples:

        x_source = x.split('-')[1]
        y_source = y.split('-')[1]
        if (
            x_source == 'CHC'
            and y_source == 'CHC'
            and source
            and 'merger' in source.lower()
        ):
            if x in primary_orgs:
                primary_orgs.remove(x)
                #print(
                #    f'Merger already found for {x} - removing from primary orgs and replacing with {y}'
                #)

            primary_orgs.append(y)

        ftc_dict.setdefault(x, set()).add(y)
        ftc_dict.setdefault(y, set()).add(x)

    return ftc_dict, primary_orgs



ftc_dict, primary_ccew_orgs_ftc = read_dkane_sameas(SAMEAS_FILE)
oscr_linkage_lookup, _ = read_dkane_sameas(OSCR_LINKS_FILE)

class ExtraInfoList(list):

    def append(self, item):
        if item.isempty():
            return

        if item not in self:
            super().append(item)

class ExtraInfo(BaseModel):
    uid: str
    organisationname: str = ''
    normalisedname: str = ''
    fulladdress: str = ''
    city: str = ''
    postcode: str = ''
    registerdate: str = ''
    removeddate: str = ''
    source: str = ''
    source_register: str = ''

    @model_validator(mode="after")
    def validate_required_fields(self):
        for field in ("uid",  "source_register"):#"source",
            value = getattr(self, field)
            if value is None or str(value).strip() == "":
                raise ValueError(
                    f"ExtraInfo: '{field}' must not be empty (uid={self.uid!r})"
                )
        return self

    def __eq__(self, value: "ExtraInfo") -> bool:
        return self.model_dump(exclude="source") == value.model_dump(exclude="source")

    def isempty(self):
        ignored = {"uid", "source", "source_register"}
        empty_values = {"", "na", "n/a"}

        return all(
            str(getattr(self, field)).strip().lower() in empty_values
            for field in self.model_fields
            if field not in ignored
        )

    def __hash__(self):
        return hash(self.model_dump(exclude="source"))
    
    def hash_addr(self):
        return hash((self.fulladdress, self.city, self.postcode))
    
    def hash_names(self):
        return hash((self.organisationname, self.normalisedname))
    
    def hash_reg(self):
        return hash(self.registerdate)
    
    def hash_rem(self):
        return hash(self.removeddate)
    
def consolidate_extras(values):
    # before adding anything to extras, check extras lists for duplicates
    seen_names = set()
    seen_adresses = set()
    seen_reg_dates = set()
    seen_rem_dates = set()
    processed_extras = ExtraInfoList()
    for item in values:
        if isinstance(item, dict):
            item_obj = ExtraInfo(**item)
        else:
            item_obj = item
        

        addr_hash = item_obj.hash_addr()
        names_hash = item_obj.hash_names()
        reg_hash = item_obj.hash_reg()
        rem_hash = item_obj.hash_rem()
        
        updates={}
        if addr_hash in seen_adresses:
            updates.update({'fulladdress':'' , 'city':'', 'postcode':''})
        else:
            seen_adresses.add(addr_hash)
        if names_hash in seen_names:
            updates.update({'organisationname':'', 'normalisedname':''})
        else:   
            seen_names.add(names_hash)
        if reg_hash in seen_reg_dates:
            updates.update({'registerdate':''})
        else:
            seen_reg_dates.add(reg_hash)
        if rem_hash in seen_rem_dates:
            updates.update({'removeddate':''})
        else:
            seen_rem_dates.add(rem_hash)

        new_item = item_obj.model_copy(update=updates)
        if not new_item.isempty():
            processed_extras.append(new_item)

    return processed_extras
    

class MatchInfo(BaseModel):
    uid: str
    orgA_id_in_source : str
    orgA_source : str
    orgA_uid : str
    orgB_id_in_source : str
    orgB_source : str
    orgB_uid : str
    match_type : str

    @model_validator(mode="after")
    def validate_match(self):
        if self.orgA_uid == self.orgB_uid:
            raise ValueError(
                f"Self-match detected for uid={self.orgA_uid!r}, "
                f"match_type={self.match_type!r}"
            )
        return self

class MatchedOrgList(list):

    def append(self, item):
        org, matchtype = item

        key = (org.uid, matchtype)

        if not any(
            (existing.uid, mt) == key
            for existing, mt in self
        ):
            super().append(item)

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
    source_register: str
    id_in_source: str
    cqc_reg: str = ""
    crossborder: str = ""
    is_cic: str = "False"

    extras: list[ExtraInfo] =  Field(default_factory=ExtraInfoList)

    matched_orgs: list =  Field(default_factory=MatchedOrgList) # list of (SubSpineOrg,matchtype:str) tuples
    sorted_matches: list[MatchInfo] =  Field(default_factory=list)
    sorted_extras: list[ExtraInfo] =  Field(default_factory=list)

    @field_validator('extras', mode='before')
    def validate_extras(cls,values):
        return consolidate_extras(values)

    @model_validator(mode="after")
    def validate_core(self):
        for field in ("uid", "source", "source_register"):
            value = getattr(self, field)
            if value is None or str(value).strip() == "":
                raise ValueError(
                    f"CoreOrganisation: '{field}' must not be empty (uid={self.uid!r})"
                )

        if self.source.lower() in {
            "careinspectoratescot",
            "carequalitycommission",
        }:
            raise ValueError(
                f"{self.uid} ({self.source}) must never become a CoreOrganisation\n{self}"
            )

        return self

    def add_matched_org(self, org, matchtype):
        if org.uid == self.uid:
            print(
                f"Attempted to add self ({self.uid}) as a matched organisation "
                f"via '{matchtype}'"
            )
        else:
            self.matched_orgs.append((org, matchtype))


    def to_extra_info(self) -> ExtraInfo:
        return ExtraInfo(**self.model_dump())
    
    # if an org is added to matched_orgs, check if it is_cic, and if so, set is_cic flag for this org
    @field_validator('matched_orgs', mode='before')
    def validate_matched_orgs(cls,values):
        for m,matchtype in values:
            if m.is_cic == 'True':
                cls.is_cic = 'True'
        return values

    
    def to_main_csv(self):
        self.is_cic = self.is_cic if self.is_cic else 'False'
        return self.model_dump(exclude={"extras","matched_orgs","sorted_matches"})
        
    def to_extras_csv(self):
        for x in self.extras:
            if not x.isempty():
                yield x.model_dump()


    def to_match_csv(self):
        for m in self.sorted_matches:
            yield m.model_dump()


    def sort_matches(self):
        '''
        decide what goes in main spine and what's in extras.
        all matches considered to create single organisation other than matchtype = 'companyid - companyid' which occurs
        when two organisations are mapped to the same companyid, which creates a link in the match table but not an identical
        organisation UNLESS also in the ftc mappings.
        self.matches is a list of (CoreOrganisation,matchtype) tuples
        matchtype is in ['companyid - companyid', 'name - cqc', 'name - crossborder', 'companyid - coop mutual', 'companyid - id_in_source', 'ftc']
        '''

        matchtype_order = ['ftc', 'oscr', 'name - cqc', 'name - crossborder', 'companyid - coop mutual', 'companyid - id_in_source' , 'name - housing', 'name - care', 'companyid - companyid', 'merge via']
#   
        if len(self.matched_orgs)==0:
            return
        
        new_main_rows = []
        assured_matched_orgs = []
        debug = self.uid in debug_uids

        if debug:
            print(f"\n========== sort_matches({self.uid}) ==========")
            print("Matched orgs:")
            for o, mt in self.matched_orgs:
                print(f"    {o.uid:20} {mt}")
        for matchtype in matchtype_order:
            
            matched_orgs = [item for item in self.matched_orgs if item[1].startswith(matchtype)] # == matchtype]

            if not matched_orgs:
                continue


            for matched_org, mt in matched_orgs:
                if debug:
                    print(f"\nConsidering {matched_org.uid} ({mt})")
                # if matched_org has is_cic flag set to True, set is_cic flag for this org:
                if matched_org.is_cic == 'True':
                    self.is_cic = 'True'

                if not matchtype == 'companyid - companyid':
                    assured_matched_orgs.append(matched_org)
                    e = matched_org.to_extra_info()
                    if not e in self.extras:
                        self.extras.append(e) 
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
                        match_type = mt))

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
                        match_type = mt))

        if debug:
            print("\nFinal state")
            print("Assured:", [o.uid for o in assured_matched_orgs])
            print("New main rows:", [o.uid for o in new_main_rows])
            print("Extras:", len(self.extras))
            print("Sorted matches:", len(self.sorted_matches))
            

        return new_main_rows


#
    def sort_extras(self):
        """ 
        1. Find earliest register date & latest removed date 
        2. Remove duplicates 
        3. Consolidate extras 
        """

        def parse_date(date_str):
            """ Convert date string to datetime object (if valid). """
            try:
                return datetime.strptime(date_str, '%d/%m/%Y') if date_str else None
            except ValueError:
                return None

        def fix_dates_set(dates, order):
            """ Get earliest (order=0) or latest (order=-1) date from a set. """
            valid_dates = sorted(filter(None, dates))
            return valid_dates[order] if valid_dates else None


        def add_or_update_date(extra_info_list, uid, source, datefield, date, source_register):
            """
            Update an existing ExtraInfo with matching uid if possible.
            Otherwise create and append a new ExtraInfo.
            """

            for extra in extra_info_list:
                if extra.uid == uid:
                    # Found matching uid
                    if not getattr(extra, datefield, None):
                        setattr(extra, datefield, date)
                        return extra_info_list
                    else:
                        # Already has a register/removal date → create new object
                        break
                    
            # If no matching uid found OR existing one already had register/removal date
            new_obj = ExtraInfo(
                uid=uid,
                source=source,
                source_register=source_register,
                **{datefield: date},
            )
            extra_info_list.append(new_obj)

            return extra_info_list


        def find_dates(orgs, reg_dates, rem_dates):
            """ Collect all valid register & removal dates. """
            for o in orgs:
                if type(o) == tuple:
                    o = o[0]
                reg_date = parse_date(o.registerdate)
                rem_date = parse_date(o.removeddate)
                if reg_date: reg_dates.add(reg_date)
                if rem_date: rem_dates.add(rem_date)

        # Track dates
        registerdates, removeddates = set(), set()
        all_orgs_removed = bool(self.removeddate)

        # Check if all matched orgs are removed
        for m in self.matched_orgs:
            if not m[0].removed():
                # and not m[0].id_in_source.startswith('CE'):
                ## if the match is between CCEW and CompaniesHouse CIO type, we want to use the CCEW removal date if there is one, since
                ## CIO filing is superseded by CCEW and so CIO data does not reflect check_removal_dates
                all_orgs_removed = False

        # Collect dates from matched orgs and extras
        find_dates(self.matched_orgs, registerdates, removeddates)
        find_dates(self.extras, registerdates, removeddates)

        # Update register date
        earliest_register = fix_dates_set(registerdates, 0)
        orgregdate = parse_date(self.registerdate)

        if earliest_register and ((not orgregdate) or (earliest_register < orgregdate)):
            # there's a registration date that's not in the spine org, or is earlier than that of the spine org: replace and store alternative in extras
            if orgregdate:
                self.extras = add_or_update_date(self.extras, self.uid, self.source, 'registerdate', self.registerdate, self.source_register)
                #self.extras.append(ExtraInfo(uid=self.uid, source=self.source, registerdate=self.registerdate, source_register=self.source_register))
            self.registerdate = earliest_register.strftime('%d/%m/%Y')

        # Update removed date
        # if there's a removal date in the mainorg and its source was ccew, use this regardless of matches, as it is the primary register
        # for organisations which are also CIOs or Care Inspectorate members
        if all_orgs_removed:
            latest_removed = fix_dates_set(removeddates, -1)
            orgremdate = parse_date(self.removeddate)

            if latest_removed and (not orgremdate or latest_removed > orgremdate):
                if orgremdate:
                    self.extras = add_or_update_date(self.extras, self.uid, self.source, 'removeddate', self.removeddate, self.source_register)
                    #self.extras.append(ExtraInfo(uid=self.uid, source=self.source, removeddate=self.removeddate, source_register=self.source_register))
                self.removeddate = latest_removed.strftime('%d/%m/%Y')
        else:
            if not self.source.lower()=='ccew':
                if self.removeddate:
                    self.extras = add_or_update_date(self.extras, self.uid, self.source, 'removeddate', self.removeddate, self.source_register)
                    self.removeddate = ''

        # Remove redundant fields from extras
        for x in self.extras:
            if (self.organisationname, self.normalisedname) == (x.organisationname, x.normalisedname):
                x.organisationname = x.normalisedname = ''
            if (self.fulladdress, self.city, self.postcode) == (x.fulladdress, x.city, x.postcode):
                x.fulladdress = x.city = x.postcode = ''
            if self.postcode == x.postcode:
                x.postcode = ''
            if self.registerdate == x.registerdate:
                x.registerdate = ''
            if self.removeddate == x.removeddate:
                x.removeddate = ''
        
        # consolidate extras per uid so that supplementary.csv has as few rows as possible
        self.extras = consolidate_extras(self.extras)


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
    source_register: str
    id_in_source: str
    crossborder: str = ""
    cqc_reg: str = ""
    is_cic: str = ""

    extras: list[ExtraInfo] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_required_fields(self):
        for field in ("uid", "source", "source_register"):
            value = getattr(self, field)
            if value is None or str(value).strip() == "":
                raise ValueError(
                    f"SubSpineOrg: '{field}' must not be empty (uid={self.uid!r})"
                )
        return self


    def to_extra_info(self) -> ExtraInfo:
        return ExtraInfo(**self.model_dump())

    @field_validator('extras', mode='before')
    def validate_extras(cls,values):
        return consolidate_extras(values)

    def to_core_org(self) -> CoreOrganisation:
        kwargs = self.model_dump()
        return CoreOrganisation(**kwargs)
    
    def removed(self) -> bool:
        removed = False
        if self.removeddate:
            removed = True
        for e in self.extras:
            if e.removeddate:
                removed = True
        return removed


#    @profile
    def matches(self, byname:dict, bycompanyid:dict, bysourceid:dict, spinelist:dict):

        matches_here = []
        
        if self.companyid and (self.companyid in bycompanyid):
            match = bycompanyid[self.companyid]
            matches_here.extend([(i, 'companyid - companyid') for i in match])

        if self.normalisedname in byname: 
            match = byname[self.normalisedname]
            if self.source == 'cqc' and any(x.cqc_reg == '1' for x in match): # need to make this work by adding cqc_reg field to core orgs so we don't lose this info
                matches_here.extend([(i, 'name - cqc') for i in match])
                
            if self.crossborder=='1':
                matches_here.extend([(i, 'name - crossborder') for i in match])

            if self.source.lower() == 'scottishhousingregulator' and any(x.source.lower() == 'oscr' for x in match):
                matches_here.extend([(i, 'name - housing') for i in match])   

            if self.source.lower() == 'socialhousingengland' and any(x.source.lower() == 'ccew' for x in match):
                matches_here.extend([(i, 'name - housing') for i in match])   

            if self.source.lower() == 'careinspectoratescot' and any(x.source.lower() == 'oscr' for x in match):
                matches_here.extend([(i, 'name - care') for i in match])   

            if self.source.lower() == 'carequalitycommission' and any(x.source.lower() == 'ccew' for x in match):
                matches_here.extend([(i, 'name - care') for i in match])   

                
        if self.companyid in bysourceid:
            match = bysourceid[self.companyid]
            #for m in match:
            if self.source.lower() == 'coops' and any(x.source.lower() in ['mutuals','ch'] for x in match): 
                matches_here.extend([(i, 'companyid - coop mutual') for i in match])
            elif self.source.lower() == 'mutuals' and any(m.source.lower() == 'coops' for m in match):
                matches_here.extend([(i, 'companyid - coop mutual') for i in match])

                
        if self.id_in_source in bycompanyid:
            match = bycompanyid[self.id_in_source]
            if self.source.lower() == 'ch':
                # companies house counterpart to charity
                matches_here.extend([(i, 'companyid - id_in_source') for i in match])
            for m in match:
                if self.source.lower() == 'mutuals' and m.source.lower() == 'coops':
                    matches_here.extend([(i, 'companyid - coop mutual') for i in match])
            
        # find matches in dkane _sameas csv
        if self.uid in ftc_dict:
            matched_uids = ftc_dict[self.uid]
            for m in matched_uids:
                if m in spinelist:
                    matches_here.append((spinelist[m],'ftc')) 
    
        # find matches using historic oscr data
        if self.uid in oscr_linkage_lookup:
            matched_uids = oscr_linkage_lookup[self.uid]
            for m in matched_uids:
                if m in spinelist:
                    matches_here.append((spinelist[m],'oscr')) 

        if len(matches_here) > 1:
            matched_orgs = [(i[0].uid,i[1]) for i in matches_here]
            distinct_matches = set([i[0] for i in matched_orgs])
            #if len(distinct_matches) > 1:
            #    print(f'more than one matched org: {matched_orgs} for {self.uid} {self.normalisedname} {self.source}')
        return matches_here




class MainOrgList:
    def __init__(self):
        self._store: dict[str, CoreOrganisation] = {}
        self.byname: dict[str, list[CoreOrganisation]] = {}
        self.bycompanyid: dict[str, list[CoreOrganisation]] = {}
        self.bysourceid: dict[str, list[CoreOrganisation]] = {}


    def __iter__(self):
        return iter(self._store)

#    @profile
    def report(self):
        sourcedict = {}
        matchdict = {}
        all_uids = set()
        for uid in self._store:
            all_uids.add(uid)
            source = self._store[uid].source
            if source in sourcedict:
                sourcedict[source] += 1
            else:
                sourcedict[source] = 1
            matches = self._store[uid].matched_orgs
            for m,matchtype in matches:
                all_uids.add(m.uid)
                if not m.source in matchdict:
                    matchdict[m.source] = 1
                else:
                    matchdict[m.source] += 1
        return sourcedict,matchdict,len(list(all_uids))
    
    def add_to_stores(self, org):
        
        def add_to_dict(dictionary, key, org):
            if key:
                if key not in dictionary:
                    dictionary[key] = [org]
                elif org not in dictionary[key]:
                    dictionary[key].append(org)


        if isinstance(org, SubSpineOrg):
            new_core_org = org.to_core_org()
            org = new_core_org

        self._store[org.uid] = org
        #add_to_dict(self._store, org.uid, org)
        add_to_dict(self.byname, org.normalisedname, org)
        if org.companyid and org.companyid != '0' * len(org.companyid):
            add_to_dict(self.bycompanyid, org.companyid, org)
        add_to_dict(self.bysourceid, org.id_in_source, org)

        # also add the keys for anything in org.matched_orgs
        if isinstance(org, CoreOrganisation):

            for m,matchtype in org.matched_orgs:
                add_to_dict(self.byname, m.normalisedname, org)
                if m.companyid and m.companyid != '0' * len(m.companyid):
                    add_to_dict(self.bycompanyid, m.companyid, org)
                add_to_dict(self.bysourceid, m.id_in_source, org)

        if org.uid in debug_uids:
            print(f"add_to_stores({org.uid}, {type(org).__name__})")
            #if isinstance(org,CoreOrganisation):
            #    print(org.matched_orgs)

    def remove_from_stores(self, org):
        if org.uid in debug_uids:
            print(f"remove_from_stores({org.uid}, {type(org).__name__})")
        def remove_from_dict(dictionary, key, org):
            values = dictionary.get(key)
            if not values:
                return
            dictionary[key] = [x for x in values if x.uid != org.uid]
            if not dictionary[key]:
                del dictionary[key]

        remove_from_dict(self.byname, org.normalisedname, org)
        remove_from_dict(self.bycompanyid, org.companyid, org)
        remove_from_dict(self.bysourceid, org.id_in_source, org)
#        remove_from_dict(self._store, org.uid, org)
        self._store.pop(org.uid,None)



    def unique_core_matches(self, matched_org):
        """
        Given a list of (CoreOrganisation, matchtype) tuples,
        return the unique CoreOrganisations.
        """


        unique = {}
        for core, _ in matched_org:
            unique[core.uid] = core


        return list(unique.values())


    def choose_primary_core(self, cores):
        """
        Decide which existing CoreOrganisation should remain the
        primary organisation after two cores become connected.
        """


        if len(cores) == 1:
            return cores[0]

        precedence = {
            source: i
            for i, source in enumerate(source_precedence_order)
        }

        return min(
            cores,
            key=lambda org: precedence.get(org.source.lower(), float("inf"))
        )



    def merge_coreorganisations(self, cores, bridge_uid):
        """
        Merge several CoreOrganisations into one (when an organisation matches two on the spine, 
        but the two weren't already linked).
    
        Returns the surviving CoreOrganisation.
        """
    
        primary = self.choose_primary_core(cores)
    
        for other in cores:
        
            if other.uid == primary.uid:
                continue
            #print('other = ',other.uid, type(other))
            #
            # Remove from lookup dictionaries first
            #
            self.remove_from_stores(other)
    
            #
            # Bring across all existing matched organisations
            #
            for m, matchtype in other.matched_orgs:
                if (m.uid, matchtype) not in {
                    (existing.uid, mt)
                    for existing, mt in primary.matched_orgs
                }:
                    primary.add_matched_org(m, matchtype)
            
                #if not any(existing.uid == m.uid
                #           for existing, _ in primary.matched_orgs):
                #        
                #    primary.add_matched_org(m, matchtype)
    
            #
            # Downgrade the losing core into a SubSpineOrg
            #
            reverted = SubSpineOrg(**other.model_dump())
    
    
            #
            # Add the losing primary itself as a matched organisation
            #
            if not any(existing.uid == reverted.uid
                       for existing, _ in primary.matched_orgs):
                    
                primary.add_matched_org(reverted, "merge via %s"%bridge_uid)
    
        #
        # Re-index the surviving core.
        #
        self.add_to_stores(primary)
    
        return primary
    



    def merge(self, orgs: list[SubSpineOrg]):
        '''merge SubSpineOrgs onto MainOrgList (self): check for matches'''

        def check_removal_dates(subspine_org, matched_orgs):
            ''' 
            if any matched orgs are from the same source as subspine_org, check for removal dates:
            the primary org is the one without a removal date, or with the most recent removal date.
            '''

            def parse_date(date_str):
                if date_str:
                    return datetime.strptime(date_str, '%d/%m/%Y')
                return None
            
            org_merging_on_remdate = parse_date(subspine_org.removeddate)


            # if any matched_orgs have a later removal date than subspine_org, output an error message
            for m,matchtype in matched_orgs:
                matched_coreorg_remdate = parse_date(m.removeddate)
                if m.source == subspine_org.source:
                    # two cases which are problematic: 
                    # 1. org_merging_on_remdate is later than matched_coreorg_remdate, and 
                    # 2. null org_merging_on_remdate but not null matched_coreorg_remdate (meaning that the org merging on is still active while the matched org is not)
                    if matched_coreorg_remdate:
                        if not org_merging_on_remdate:
                            print(f'ERROR: {subspine_org.normalisedname} ({subspine_org.uid}) has no removal date, but {m.normalisedname} ({m.uid}, {m.removeddate}) does in source {m.source}')
                        elif org_merging_on_remdate and (org_merging_on_remdate > matched_coreorg_remdate):
                            print(f'ERROR: {subspine_org.normalisedname} ({subspine_org.uid}) has a later removal date ({subspine_org.removeddate}) than {m.normalisedname} ({m.uid}, {m.removeddate}) in source {m.source}')




        
        for this_subspine_org in tqdm(orgs, desc='Processing orgs'):
            # does this_subspine_org match anything already in the spine (MainList (self))?

            debug = this_subspine_org.uid in debug_uids

            matched_org = this_subspine_org.matches(self.byname, self.bycompanyid, self.bysourceid, self._store)

            if debug:
                print(f"\n=== Processing {this_subspine_org.uid} ===")
                print(this_subspine_org.organisationname, this_subspine_org.normalisedname)
                if matched_org:
                    print("Matched:")
                    for core, mt in matched_org:
                        print(f"    {core.uid} via {mt}")
                else:
                    print("No matches found")

            if matched_org:
                
                unique_cores = {}
                for core, _ in matched_org:
                    unique_cores.setdefault(core.uid, core)

                unique_cores = list(unique_cores.values())
                if debug:
                    print('Unique cores: ',[c.uid for c in unique_cores])

                if len(unique_cores) > 1:

                    merged_core = self.merge_coreorganisations(unique_cores,this_subspine_org.uid)
                    
                    if debug:
                        print(f'*** more than one match; {[i.uid for i in unique_cores]}, primary chosen = {merged_core.uid}, matches = {[i.uid for (i,_) in merged_core.matched_orgs]}')
                    matched_org = [
                        (merged_core, matchtype)
                        for _, matchtype in matched_org]
                    
                    

                #print('\nmatch: ',this_subspine_org.uid,this_subspine_org.normalisedname,' \n   to: ',matched_org)
                check_removal_dates(this_subspine_org, matched_org)
                # check if this org should be primary rather than matched:
                if (this_subspine_org.uid in primary_ccew_orgs_ftc):
                    #print(f"primary org found ({this_subspine_org.uid})")
                    # this is the primary org in the match
                    new_coreorg = this_subspine_org.to_core_org()
                    if debug: print('becomes new primary org')
                    # need to attach any matches so far to new_coreorg, instead of matched_org
                    for m,matchtype in matched_org:
                        new_coreorg.matched_orgs.extend([i for i in m.matched_orgs if i not in new_coreorg.matched_orgs])
                        reverted_m = SubSpineOrg(**m.__dict__)  # need to downgrade matched coreorg to subspine, and put it as a match in new_coreorg.
                        self.add_to_stores(reverted_m)
                        self.remove_from_stores(m)
                        new_coreorg.add_matched_org(reverted_m,matchtype)
                        self.add_to_stores(new_coreorg)
                
                else:
                    # add this_subspine_org to all matched this_subspine_org already in the spine:
                    for matched_coreorg,matchtype in matched_org: # o is higher up the precedence order than this_subspine_org
                        matched_coreorg.add_matched_org(this_subspine_org,matchtype)
                        self.add_to_stores(matched_coreorg)

            else:
                # no matches: add this as a new org in the spine
                if not this_subspine_org.source.lower() in {
                    "careinspectoratescot",
                    "carequalitycommission",
                }:
                    self.add_to_stores(this_subspine_org)
                


    def restore_from_csv(self, filename_main: str, filename_extras: str):
        with open(filename_main) as in_main:
            main_csv = csv.DictReader(in_main)
            for main_row in main_csv:
                new_org = CoreOrganisation(**main_row)
                self._store[new_org.uid] = new_org

            with open(filename_extras) as in_extras:
                extras_csv = csv.DictReader(in_extras)
                for extras_row in extras_csv:
                    main_row = self._store[extras_row["uid"]]
                    main_row.extras.append(ExtraInfo(**extras_row))



    def sort_matches(self):
        new_store_items = []
        for org in tqdm(self._store.values(), desc='Sorting matches'):
            debug = org.uid in debug_uids
            if debug:
                print(f"\n========== sort_matches loop ({org.uid}) ==========")
                for o, mt in org.matched_orgs:
                    print(f"    {o.uid:20} {mt}")
            for_store = org.sort_matches()
            if for_store:
                new_store_items.extend(for_store)

        for s in new_store_items:
            self.add_to_stores(s)

    def sort_extras(self):
        for org in tqdm(self._store.values(), desc='Sorting extras'):
            org.sort_extras()


    def write_out(self, filename_main: str, filename_extras: str, filename_matches: str):

        self.sort_matches()
        print('\n\nsort_matches complete.')

        self.sort_extras()
        print('\n\nsort_extras complete.')

        with open(filename_main, "w+") as out_main:
            with open(filename_extras, "w+") as out_extras:
                with open(filename_matches, 'w+') as out_matches:

                    main_csv = csv.DictWriter(out_main, fieldnames=SPINE_CSV_FIELDS)
                    extras_csv = csv.DictWriter(out_extras, fieldnames=EXTRA_DETAILS_CSV_FIELDS)
                    matches_csv = csv.DictWriter(out_matches,fieldnames=MATCHES_CSV_FIELDS)
                    for csv_x in [main_csv,extras_csv,matches_csv]:
                        csv_x.writeheader()

                    for org in tqdm(self._store.values(), desc='Writing to files'):

                        if not org.source.lower() in ['careinspectoratescot','carequalitycommission']:
                        
                            for row in [org.to_main_csv()]:
                                filtered_row = {key: row[key] for key in SPINE_CSV_FIELDS if key in row}
                                main_csv.writerow(filtered_row)

                            for row in org.to_extras_csv():
                                filtered_row = {key: row[key] for key in EXTRA_DETAILS_CSV_FIELDS if key in row}
                                extras_csv.writerow(filtered_row)

                            for row in org.to_match_csv():
                                matches_csv.writerow(row)
        
        # remove duplicates from supplementary.csv
        df = pd.read_csv(filename_extras)
        df.drop_duplicates(inplace=True)
        df.to_csv(filename_extras, index=False) 
        print(f'\nFiles written to {filename_main}, {filename_matches}, {filename_extras}\n')



def convert_csv_to_list_of_subspine_orgs(csv_file: str) -> list[SubSpineOrg]:
    
    file_root, _ = os.path.splitext(csv_file)
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
    progress = []
    for csv_file in csv_file_list_order:
        print(f'\n\n------------------ PROCESS: Processing file {csv_file} ------------------')

        base_orgs = convert_csv_to_list_of_subspine_orgs(csv_file)

        print(f'\nFile contained {len(base_orgs)} organisations \n\n')
        main_orgs.merge(base_orgs)
        source_dict, match_dict, unique_uids = main_orgs.report()
        if base_orgs:
            progress.append((base_orgs[0].source,source_dict,match_dict,unique_uids))

        print(f'BUILD PROGRESS:\n Cumulative total of {unique_uids} organisations now processed.\n')
        print(f'Orgs merged into main spine: {len(main_orgs._store.keys())} organisations, of which {len([x for x in main_orgs._store.keys() if main_orgs._store[x].matched_orgs])} have matched orgs\n\n')
        print(f'Sources now in the main spine: {source_dict}\nSources from which matches were found: {match_dict}\n')

    print('For plotting:\n reports = [')  
    for t in progress:
        print(f'{t},')
    print(']')

    return main_orgs

