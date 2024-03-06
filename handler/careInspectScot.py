
from datetime import datetime

from .base import DataHandler

include_filters = {
    "ServiceType": ['Voluntary or Not for Profit'],
    "Service Type": ['Voluntary or Not for Profit'],
}


class CareInspScotDataHandler(DataHandler):
    fileencoding='Latin-1'
    
    
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
        
        v = ['Service_Provider','ServiceProvider','ServiceName']
        return [i for i in v if i in fieldnames]


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
        new_row["primarysource"] = 'CareInspectorateScot'
        new_row["primaryid"] = row[id]
        new_row["primaryregdate"] = self.map_date(row['DateReg'])
        new_row["dissolutiondate"] = ''
        new_row["secondarysource"] = ''
        new_row["secondaryid"] = ''
        new_row["secondaryregdate"] = ''

        super().sort_address_fields(new_row)
        return new_row




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