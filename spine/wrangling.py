
from handler.base_definitions import FINAL_SPINE_CSV_FORMAT, FINAL_EXTRA_DETAILS_CSV_FIELDS
import csv
import sys
import pandas
import re
from datetime import datetime



    
def check_spine_format(csv_fields):
    """
    Given input row (which will be top row of an input CSV), check it matches fields in SPINE_FORMAT
    """
    # check mapping - 
    if not csv_fields:
        return False
    for field in FINAL_SPINE_CSV_FORMAT:
        if field not in csv_fields:

            print(f'field {field} not in input file fields')
            return False
    for field in csv_fields:
        try:
            if field not in FINAL_SPINE_CSV_FORMAT: 
                print('unexpected field %s in input file\n'%field)
                continue
        except UnicodeDecodeError as e:
            print("%s\n\t%s"%(e,field))
            continue

    else:
      return True



def concat(csv_ins, csv_out):
    """
    Given a list of csv file handlers, in SPINE format, and an output file handler

    * Concatenate csvs, adding normalized name to each row, consolidating address fields -> 'fulladdress', 
        adding uid in org_id format (where possible)
    * Write out to output location
    """
    writer = csv.DictWriter(csv_out, fieldnames=FINAL_SPINE_CSV_FORMAT, extrasaction='ignore')
    writer.writeheader()
    for csv_in in csv_ins:
      processed_rows = 0
      sys.stdout.write('Processing file %s.......\n'%csv_in)
      csv_data = csv.DictReader(csv_in)
      if not check_spine_format(csv_data.fieldnames):
        raise ValueError('file %s is not in SPINE format'%csv_in)
      
      for row in csv_data:
        
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


def combine_org_details(rows, final=True):
    '''
    For input rows of data, find unique names and addresses, and create rows for each combination of name & address
    (called by compress_per_org and permutate)
    '''
    names=[]
    addresses=[]
    
    primaryid = ''
    primarysource = []
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
        
        if r['primaryid']: 
            primaryid = r['primaryid']
        primarysource.append(r['primarysource'])

        if ' - ' in r['primaryregdate']:
            reg_dates.extend(r['primaryregdate'].split(' - '))
        else:
            reg_dates.append(r['primaryregdate'])

        if ' - ' in r['dissolutiondate']:
            dis_dates.extend(r['dissolutiondate'].split(' - '))
        else:
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

    sorted_registration_dates = sort_dates(reg_dates)
   
    sorted_dissolution_dates = sort_dates(dis_dates)


    reg = ' - '.join(sorted_registration_dates)
    dis = ' - '.join(sorted_dissolution_dates)


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
    return new_spine_rows,new_extras_rows
        

def compress_per_org(csv_in,spine_csv_out,details_csv_out):
    '''run as part of initial processing of an input 
    required as some sources have details across multiple lines, while do_csv_processing reads line by line
    '''


    # create dictionary key'd by uid
    print(f'Running spine.wrangling.compress with file {csv_in}')
    uid_dict = dict_indexed_by_field(csv_in,'uid')

    # for each uid, if more than one record, find unique names and addresses
    # and write line to csv_out, with additional data to details_csv_out
    spine_writer = csv.DictWriter(spine_csv_out, fieldnames=FINAL_SPINE_CSV_FORMAT, extrasaction='ignore')
    extras_writer = csv.DictWriter(details_csv_out, fieldnames=FINAL_EXTRA_DETAILS_CSV_FIELDS, extrasaction='ignore')
    spine_writer.writeheader()
    extras_writer.writeheader()
    for uid in uid_dict.keys():
        if not uid.split('-')[-1]:
            # uid doesn't have id attached, don't permutate across addresses
            for line in uid_dict[uid]:
                print(f'in wrangling.compress. Line has truncated uid: {line}')
                spine_writer.writerow(line)
        elif len(uid_dict[uid]) > 1: # more than one record with this uid - create combinations
            spine_data,extra_data = combine_org_details(uid_dict[uid])
            spine_writer.writerows(spine_data)
            extras_writer.writerows(extra_data)
        else: # only one record with this uid - write directly
            uid_dict[uid][0]['source'] = replace_CH_source_field(uid_dict[uid][0]['source'])
            spine_writer.writerow(uid_dict[uid][0])

    print(f'Completed spine.wrangling.compress - output in {spine_csv_out} and {details_csv_out}')


def permutate(csv_in,csv_out,final):
    """
    For all records with the same uid, find unique names and addresses and create all permutations of these
    If final permutation (after matching etc), remove references to different companies house scrapes
    """


    # create dictionary key'd by uid
    print(f'Running spine.wrangling.permutate with file {csv_in}')
    uid_dict = dict_indexed_by_field(csv_in,'uid')

    # for each uid, if more than one record, find unique names and addresses
    # and write lines to csv_out
    writer = csv.DictWriter(csv_out, fieldnames=FINAL_SPINE_CSV_FORMAT, extrasaction='ignore')
    writer.writeheader()
    for uid in uid_dict.keys():
        if not uid.split('-')[-1]:
            # uid doesn't have id attached, don't permutate across addresses
            for line in uid_dict[uid]:
                print(f'in wrangling.permutate. Line has truncated uid: {line}')
                writer.writerow(line)

        elif len(uid_dict[uid]) > 1: # more than one record with this uid - create combinations
            writer.writerows(combine_org_details(uid_dict[uid],final))

        else: # only one record with this uid - write directly
            # replace source if needed:
            if final:
                uid_dict[uid][0]['source'] = replace_CH_source_field(uid_dict[uid][0]['source'])
                
            writer.writerow(uid_dict[uid][0])
    print(f'Completed spine.wrangling.permutate - output in {csv_out}')


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