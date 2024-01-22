
from handler.base import SPINE_CSV_FORMAT, NEW_SPINE_CSV_FORMAT, FINAL_SPINE_CSV_FORMAT
import csv
import string
import sys
import pandas
import re
from datetime import datetime

ORG_ID_MAPPING = {
'CCEW':'CHC',
'OSCR':'SC',
'CCNI':'NIC',
'PRI/LTD BY GUAR/NSC (Private, limited by guarantee, no share capital)':'COH',
"PRI/LBG/NSC (Private, limited by guarantee, no share capital, use of 'Limited' exemption)":'COH',
'Charitable Incorporated Organisation':'COH',
'Community Interest Company':'COH',
'Registered Society':'COH',
'Scottish Charitable Incorporated Organisation':'COH',
'Industrial and Provident Society':'COH',
'CareQualityCommission':'CQC', # not in org_id - might need to update mapping
'ScottishHousingRegulator':'SHR',
'SocialHousingEngland':'SHPE',
'CoOps':'COOP', # not in org_id - might need to update mapping
'Mutuals Public Register': 'MPR'
}

def normalizer(name, norm_dict=None):
    ''' normalise entity names with manually curated dict'''
    norm_dict={}
    if isinstance(name, str):
        name = name.upper()
        for key, value in norm_dict.items():
            name = name.replace(key, value)
        name = name.replace(r"\(.*\)", "")  # remove brackets
        name = "".join(l for l in name if l not in string.punctuation) # keep text other than punctuation
        name = ' '.join(name.split()) # remove additional spaces
        name = name.strip() # remove trailing spaces
        return name
    return None
    
def check_spine_format(csv_fields):
    """
    Given input row (which will be top row of an input CSV), check it matches fields in SPINE_FORMAT
    """
    # check mapping - 
    if not csv_fields:
        return False
    for field in NEW_SPINE_CSV_FORMAT:
        if field not in csv_fields:
            if field in ['fulladdress','charitynumber','normalisedname','city']: # these fields can be added by processing
                continue
            else:
                print(f'field {field} not in input file fields')
                return False
    for field in csv_fields:
        try:
            if field not in SPINE_CSV_FORMAT: 
                print('unexpected field %s in input file\n'%field)
                continue
        except UnicodeDecodeError as e:
            print("%s\n\t%s"%(e,field))
            continue

    else:
      return csv_fields


def consolidate_address(row):

    address_fields = [
    "housenumber",
    "addressline1",
    "addressline2",
    "addressline3",
    "addressline4",
    "addressline5"]
    
    fulladdress = ''

    row['postcode'] = row['postcode'].strip()
       
    
    for line in address_fields:
        try:
            if row[line]:
                fulladdress += '%s, '%row[line].strip().strip(',').strip('"')
        except KeyError:
            pass

    try:
        fulladdress = fulladdress.split(row['postcode'])[0]
    except ValueError:
        pass

    return fulladdress.strip(', ')


def concat(csv_ins, csv_out):
    """
    Given a list of csv file handlers, in SPINE format, and an output file handler

    * Concatenate csvs, adding normalized name to each row, consolidating address fields -> 'fulladdress', 
        adding uid in ord_id format (where possible)
    * Write out to output location
    """
    writer = csv.DictWriter(csv_out, fieldnames=NEW_SPINE_CSV_FORMAT, extrasaction='ignore')
    writer.writeheader()
    for csv_in in csv_ins:
      processed_rows = 0
      sys.stdout.write('Processing file %s.......\n'%csv_in)
      csv_data = csv.DictReader(csv_in)
      if not check_spine_format(csv_data.fieldnames):
        raise ValueError('file %s is not in SPINE format'%csv_in)
      
      for row in csv_data:
        row['normalisedname'] = normalizer(row['organisationname'])
        if not 'fulladdress' in row.keys():
            row['fulladdress'] = consolidate_address(row)
        if not row['uid']:
            row['uid'] = 'GB-%s-%s'%(ORG_ID_MAPPING[row['source']],row['charitynumber'])
        row['fulladdress'] = row['fulladdress'].upper()
        row['city']=row['city'].upper()
        try:
            row['fulladdress'] = row['fulladdress'].split(row['city'])[0].strip(',')
        except ValueError:
            pass
        row['fulladdress'] = row['fulladdress'].replace(' ,',',')
        try:
            writer.writerow(row)
            processed_rows += 1
        except UnicodeEncodeError as e:
            sys.stdout.write("%s\n\t%s"%(e,row))
            continue


      sys.stdout.write(".......... processed, %d lines written to output file\n"%(processed_rows))


    
def dict_indexed_by_field(csv_in,fieldname):
    field_dict={}
    for row in csv.DictReader(csv_in):
        
        if not row[fieldname] in field_dict.keys():
            field_dict[row[fieldname]]=[row]
        else:
            field_dict[row[fieldname]].append(row)
    return field_dict


def dedupe_addr(a):
    '''
    Takes list of tuples (fulladdress,city,postcode).
    Searches for postcodes, if any identical, and one tuple has info in fulladdress and city and the other doesn't,
    remove the ('','',postcode) tuple.
    Also, for those with ('ADDR, CITY','','POSTCODE') with matching ('ADDR','CITY','POSTCODE'), retain only the latter
    '''
    postcode_dict = {}
    for (addr,city,pc) in a:
        if not pc in postcode_dict.keys(): 
            postcode_dict[pc]=[(addr,city)]
        else: postcode_dict[pc].append((addr,city))
    
    addresses = []
    for pc in postcode_dict.keys():
        
        if len(postcode_dict[pc]) != 1:
            # for the same postcode, there is addrress data, so ignore the line that has only the postcode
            try:
                postcode_dict[pc].remove(('',''))
            except: 
                pass

            cities=[]
            for (addr,city) in postcode_dict[pc]:
                if not city in cities: 
                    cities.append(city)
            
            for (addr,city) in postcode_dict[pc]:
                for c in cities:
                    if not city:
                        try:
                            new_tuple = (addr.split(c)[0].strip(', '),c) # get address without city
                            postcode_dict[pc].remove((addr,'')) # remove tuple ('address,city','')
                            if not new_tuple in postcode_dict[pc]: 
                                postcode_dict[pc].append(new_tuple)
                        except ValueError:
                            pass

    for pc in postcode_dict.keys():
        for (addr,city) in postcode_dict[pc]:
            addresses.append((addr,city,pc))
    
    return addresses


def replace_CH_source_field(s):
    # s is string or list of sources
    # return same type, with mapped_sources = ["2014_prior","2023_download","adv_api"] replaced by 'CH'
    mapped_sources = ["2014_prior","2023_download","adv_api"]
    print('replacing CH source fields...')
    def ch(x):
        for i in mapped_sources:
            if i in x: return 'CH'
        return x
    
    if type(s)==str:
        for i in mapped_sources:
            if i in s:
                return 'CH'
            else: return s
            
    if type(s)==list:
        return list(map(ch,s))


def sort_dates(date_list):
    ''' convert input list of str dates to set (no duplicates) of datetime objects, to then sort'''
    d_set = set()
    for date in date_list:
        if date:
           d_set.add(datetime.strptime(date,'%d/%m/%Y'))

    d_list = list(d_set)

    d_list.sort() #sorts from longest ago to most recent

    as_str = []
    for date in d_list:
        as_str.append(date.strftime('%d/%m/%Y'))
    
    if len(as_str) == 0:
        as_str=['']

    return as_str


def combine_org_details(rows, final):
    '''
    For input rows of data, find unique names and addresses, and create rows for each combination of name & address
    (called by permutate)
    '''
    names=[]
    addresses=[]
    charityid = ''
    companyid = ''
    source = []
    reg_dates = []
    dis_dates = []
    for r in rows:
        try:
            n,a = ((r['organisationname'],r['normalisedname']),(r['fulladdress'],r['city'],r['postcode']))
        except KeyError:
            sys.stdout.write('KeyError searching for organisationname, normalisedname, fulladdress, city and postcode in row %s\n'%r)
            return []
        if n not in names: names.append(n)
        if not a in addresses: addresses.append(a)
        if r['charitynumber']: charityid = r['charitynumber']
        if r['companyid']: companyid = r['companyid']
        source.append(r['source'])
        reg_dates.append(r['registrationdate'])
        dis_dates.append(r['dissolutiondate'])

    try:
        names.remove(('',''))
    except:
        pass

    # if there's more than one address, we don't care about an empty one
    if len(addresses)>1:
        try:
            addresses.remove(('','',''))
        except:
            pass

    # check addresses: remove any that are ('','',POSTCODE) if POSTCODE is part of a fuller address elsewhere
    # (occurs as a result of the slimmer data source from 2014, at least)
    addresses = dedupe_addr(addresses)


    # if there are multiple options for the registration and dissolution date we want the widest range:
    sorted_registration_dates = sort_dates(reg_dates)
    #if len(sorted_registration_dates)>1:
    #    print('possible competing registration dates for ',r['uid'],' : ',sorted_registration_dates)
    
    sorted_dissolution_dates = sort_dates(dis_dates)
    #if len(sorted_dissolution_dates)>1:
    #    print('possible competing dissolution dates for ',r['uid'],' : ',sorted_dissolution_dates)

    reg = sorted_registration_dates[0]
    dis = sorted_dissolution_dates[-1]


    # we want all CH sources to be consolidated for final spine output
    if final:
        sources_simple = replace_CH_source_field(source)
    else:
        sources_simple = source


    uid = r['uid']
    new_rows = []
    for (orgname,normname) in names:
        for (addr,city,pc) in addresses:
            new_rows.append({'uid':uid,
                             'organisationname':orgname,
                             'normalisedname':normname,
                             'companyid':companyid,
                             'charitynumber':charityid,
                             'fulladdress':addr,
                             'city':city,
                             'postcode':pc,
                             'source': ' - '.join(sorted(set(sources_simple))),
                             'registrationdate':reg,
                             'dissolutiondate':dis
                             })
    return new_rows
        

def permutate(csv_in,csv_out,final):
    """
    For all records with the same uid, find unique names and addresses and create all permutations of these
    If final permutation (after matching etc), remove references to different companies house scrapes
    """


    # create dictionary key'd by uid
    uid_dict = dict_indexed_by_field(csv_in,'uid')

    # for each uid, if more than one record, find unique names and addresses
    # and write lines to csv_out
    writer = csv.DictWriter(csv_out, fieldnames=NEW_SPINE_CSV_FORMAT, extrasaction='ignore')
    writer.writeheader()
    for uid in uid_dict.keys():
        if len(uid_dict[uid]) > 1: # more than one record with this uid - create combinations
            writer.writerows(combine_org_details(uid_dict[uid],final))

        else: # only one record with this uid - write directly
            # replace source if needed:
            if final:
                uid_dict[uid][0]['source'] = replace_CH_source_field(uid_dict[uid][0]['source'])
                
            writer.writerow(uid_dict[uid][0])


def wrangle_findthatcharity_data(infile:str,field:str,ofile):
    df = pandas.read_csv(infile,usecols=[field])
    new_df = pandas.DataFrame

    for index, row in df.iterrows():
        res = []
        s= re.findall('GB-[^\s,]+',row[field])
        for part in s:
            res.append(part.strip('[]"').strip("'"))

        df.at[index, 'uid'] = '_'.join(sorted(set(res)))
    
    new_df = df[['uid']]
    new_df.to_csv(ofile)
    return new_df


def final_processing(fulldatafile):
    # read in fulldatafile, add rowid field with unique value per row, and ignore field charitynumber
    
    ofilename = fulldatafile.name[:-3] + 'final.csv' #'final_matching_spine.csv'
    ofile = open(ofilename,'w+')

    writer = csv.DictWriter(ofile, fieldnames=FINAL_SPINE_CSV_FORMAT, extrasaction='ignore')
    writer.writeheader()
    rowid = 1

    with open(fulldatafile.name,'r') as openfile:
        for row in csv.DictReader(openfile):
                
                new_row = {}
                for field in FINAL_SPINE_CSV_FORMAT:
                    if field == 'rowid':
                        new_row['rowid']=rowid
                        rowid += 1

                    else:
                        new_row[field] = row[field]

                writer.writerow(new_row)
    
    return ofilename