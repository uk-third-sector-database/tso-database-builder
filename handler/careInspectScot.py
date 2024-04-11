
from datetime import datetime

from .base import DataHandler
from .base_definitions import sub_spine_entry_creator,extra_csv_entry_creator

include_filters = {
    "ServiceType": ['Voluntary or Not for Profit'],
    "Service Type": ['Voluntary or Not for Profit'],
}


class CareInspScotDataHandler(DataHandler):
    fileencoding='Latin-1'
    tmp_fields=['iteration']
    
    def all_filters(self, row: dict) -> bool:

        for fieldname, include_values in include_filters.items():
            if row.get(fieldname) in include_values:
                return True

        return False
    
    def map_date(self, datestr):
        if not datestr:
            return ''
        try:
            d = datetime.strptime(datestr,'%d/%m/%Y')
        except:
            try:
                d = datetime.strptime(datestr,'%d-%b-%y')
            except:
                print('error with date',datestr)
        return d.strftime('%d/%m/%Y')

    def find_names(self, fieldnames) -> list:
        ''' returns name keys which have non-null values'''
        
        #v = ['Service_Provider','ServiceProvider','ServiceName']
        #return [i for i in v if i in fieldnames]
        return ['ServiceName']

    def find_id_name(self,row:dict) -> str:
        v = ['CSNumber', 'CaseNumber','ï»¿CSNumber']
        for i in v:
            if i in row.keys():
                return i
        return False


    def format_row(self,namefield,row) -> dict:
        '''format a row into Spine format, for given namefield'''
        new_row={}
        for field in row:
            row[field] = row[field].strip()

        id = self.find_id_name(row)
        if not id:
            print(row.keys())

        new_row["uid"] = 'GB-CIS-'+ row[id]     
        new_row["organisationname"] = row[namefield]
        new_row["normalisedname"] = ''
        new_row["city"] = row['Service_town']
        new_row["addressline1"] = row['Address_line_1']
        new_row["addressline2"] = row['Address_line_2']
        new_row["addressline3"] = row['Address_line_3']
        new_row["addressline4"] = row['Address_line_4']
        new_row["postcode"] = row['Service_Postcode']
        new_row["source"] = 'CareInspectorateScot'
        new_row["id_in_source"] = row[id]
        new_row["registerdate"] = self.map_date(row['DateReg'])
        new_row["removeddate"] = ''
        new_row['companyid'] = ''
        new_row["iteration"] = row['Iteration']

        super().sort_address_fields(new_row)
        return new_row



    def find_primary_info(self,details_list):
        '''details_list is list of tuples (fulladdress,city,postcode,iteration) | (name,normname,iteration)
        and primary details are that found in most recent iteration'''
        details_list = list(details_list) 
        primary = tuple('' for _ in range(len(details_list[0])-1))
        date = 2000
        extra_details = set()
        #print(details_list)
        for item in details_list:
            data_tuple = item[:-1]
            if len([i for i in data_tuple if i]) == 0:
                continue
            iteration = item[-1]
            if iteration:
                iteration = int(iteration)
                if iteration > date:
                    date = iteration
                    primary = data_tuple
            extra_details.add(data_tuple)


        extra_details = [i for i in extra_details if i != primary and i != ('','','')]
        #print(f'primary address = {primary}')
        #print(f'extra addresses = {extra_details}')
        return primary, extra_details




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
                n = (r['organisationname'],r['normalisedname'],r['iteration'])
                a = (r['fulladdress'],r['city'],r['postcode'],r['iteration'])
                reg = r['registerdate']
                dis = r['removeddate']
            except KeyError as e:
                print(f'KeyError searching for names, addresses and/or dates in row {r} : {e}\n')
                return []
            
             
            for var in [(n,names),(a,addresses),(reg,regdates),(dis,remdates)]:
                var[1].add(var[0])
                
        primary_name, extra_names = self.find_primary_info(names)
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
        
        return new_sub_spine_row, new_extras_rows


#---- used to add the year to the careinspectorate data, from file name, and create one datafile. ----#
import csv
import glob
import os
fields = ["CSNumber",
        "ServiceName",
        "ServiceType",
        "Combined_Service_",
        "CaseNumber_Combined",
        "CareService",
        "Subtype",
        "Service",
        "Address_line_1",
        "Address_line_2",
        "Address_line_3",
        "Address_line_4",
        "Service_town",
        "Service_Postcode",
        "ManagerName",
        "Council_Area_Name",
        "Health_Board_Name",
        "DateReg",
        "Iteration"]

def fix_care_inspectorate_files_A():
    # Pre-process the raw files to include the source date (found in filename) as a field
    raw_files = glob.glob('../raw_data/CareInspectScot/MDSF_data*.csv')
    print(raw_files)
    output_file = '../raw_data/CareInspectScot.all.csv'
    
    with open(output_file, 'w', newline='', encoding='Latin-1') as outfile:
        
        csv_writer = csv.DictWriter(outfile, fieldnames=fields)  # Create DictWriter object
        csv_writer.writeheader()  # Write header to output file
        
        # Iterate over each raw file
        for file in raw_files:
            date = os.path.basename(file).split('MDSF_data_')[-1].strip('.csv')
            with open(file, 'r', newline='', encoding='Latin-1') as infile:
                csv_reader = csv.DictReader(infile)
                v = ['CSNumber', 'CaseNumber','ï»¿CSNumber']
                for i in v:
                    if i in csv_reader.fieldnames:
                        id_field = i
                
                v = ['ServiceType','Service Type']
                for i in v:
                    if i in csv_reader.fieldnames:
                        servicetype = i

                for row in csv_reader:
                    
                    row['CSNumber'] = row[id_field]
                    row['ServiceType'] = row[servicetype]
                    row['Iteration'] = date
                    for key in fields:
                        row.setdefault(key, '') 
                    row = {key: row[key] for key in fields}
                    
                    csv_writer.writerow(row)
                        
            print(f"iteration {date} added to file {output_file}")



'''
CareInspectorateScot data fields:


CSNumber,
Combined_Service_,
CaseNumber_Combined,
CareService,
Subtype,
Service Type,
ServiceName,
Address_line_1,
Address_line_2,
Address_line_3,
Address_line_4,
Service_town,
Service_Postcode,
ManagerName,
Service_Phone_Number,
Eforms_email_address,
SP_number,
ServiceProvider,
Provided_by_Local_Authority,
ServiceStatus,
DateReg,
Date_Reg,
SIMD2020_Rank,
SIMD2020_Decile,
Datazone,
Integration_Authority_Name,
TotalBeds,
SingleBedrooms,
BedsInDoubleRooms,
BedsInBedroomsFor3OrMore,
Dec18_Annual_Return_Submitted,
CareHome_Main_Area_of_Care,
Care_Home_All_Areas_of_Provision,
Council_Area_Name,
Health_Board_Name,
NumberStaff,
Registered_Places,
Client_group,
PublicList,
RADScore,
GradeSpread,
MinGrade,
MaxGrade,
Publication_of_Latest_Grading,
Year_Month_latest_grade,
Quality_of_Information,
Quality_of_Care_and_Support,
Quality_of_Environment,
Quality_of_Staffing,
Quality_of_Mgmt_and_Lship,
KQ_Support_Wellbeing,
KQ_Care_and_Support_Planning,
KQ_Setting,
KQ_Staff_Team,
KQ_Leadership,
Comb_Eval_CareSupport_Wellbeing,
Comb_Eval_CareSupport_Planning,
Comb_Eval_Setting_Env,
Comb_Eval_Staff_StaffTeam,
Comb_Eval_Leadership_ML,
MinGrade_change,
CS_Wellbeing_change,
CS_Planning_change,
Setting_change,
Staff_change,
Leadership_change,
Complnt_upheld_or_partially_1718,
Complnt_upheld_or_partially_1819,
Complnt_upheld_or_partially_1920,
Enforcements_issued_1718,
Enforcements_issued_1819,
Enforcements_issued_1920,
any_requirements_1718,
any_requirements_1819,
any_requirements_1920,
Count any reqs 1718,
Count any reqs 1819,
Count any reqs 1920,
Last_inspection_Date,
first_date_1819,
first_case_1819,
first_recs_1819,
first_reqs_1819,
second_date_1819,
second_case_1819,
second_recs_1819,
second_reqs_1819,
third_date_1819,
third_case_1819,
third_recs_1819,
third_reqs_1819,
first_date_1920,
first_case_1920,
first_recs_1920,
first_reqs_1920,
second_date_1920,
second_case_1920,
second_recs_1920,
second_reqs_1920,
third_date_1920,
third_case_1920,
third_recs_1920,
third_reqs_1920,
fourth_date_1920,
fourth_case_1920,
fourth_recs_1920,
fourth_reqs_1920
'''