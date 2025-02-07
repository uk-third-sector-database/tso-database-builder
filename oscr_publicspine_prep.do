// File: oscr_spine_prep.do
// Creator: Alan Duggan
// Created: 11/12/2023
// Updated: 26/03/2024

******* Overview *******


/* 
	This DO file outlines the steps taken to transform Scottish charity data (charity register, annual returns 
        and removed charities) into a spine dataset of organisations. 
	
	This do file performs the following tasks:
		- imports raw datasets from five different points in time (2012, Jan 2019, Feb 2021, Sept 2021, April 2023)
		- cleans raw datasets
		- constructs dataset for linakge
		
	The data files used in this script:
		- sc_chars2012.xlsx [Historical file from 2012]
                - ocsr_scr-and-ar_20190109.xlsx [Scottish Charity Register and Annual Returns - Jan 2019] 
                - oscr_20210203.xlsx [Scottish Charity Register and Annual Returns - Feb 2021]
                - oscr_20210909.xlsx [Scottish Charity Register and Annual Returns - September 2021]
		- CharityExport-12-Apr-2023.csv [Scottish Charity Register - 12 April 2023 (Open data)]
                - CharityExport-5Years-12-Apr-2023.csv [Scottish Charity Annual Returns - 12 April 2023 (Open data)]
                - CharityExport-Removed-12-Apr-2023.csv [List of removed charities - 12 April 2023 (Open data)]

                NOTE: The last three data files are updated daily on the OSCR website.		
*/


/* Define path */

local datapath C:\Users\ad92\OneDrive\UKRI Fellowship\ADRUK\Spine data\Data files


// Cross check charity register and annual returns sheets in 2019 excel file


import excel using "`datapath'\ocsr_scr-and-ar_20190109.xlsx", sheet("scr") firstrow clear

distinct CharityNumber

save 2019_scr.dta, replace


import excel using "`datapath'\ocsr_scr-and-ar_20190109.xlsx", sheet("ar") firstrow clear

distinct CharityNumber

merge m:1 CharityNumber using 2019_scr.dta, gen(merge_2019)

/*
  All charities in annual returns are present in charity register. Use register as base for 2019. 
*/



// Cross check charity register and annual returns sheets in February 2021 excel file


import excel using "`datapath'\oscr_20210203.xlsx", sheet("mostrecent") firstrow clear

distinct CharityNumber

save 2021_Feb_scr.dta, replace


import excel using "`datapath'\oscr_20210203.xlsx", sheet("historical") firstrow clear

distinct CharityNumber

merge m:1 CharityNumber using 2021_Feb_scr.dta, gen(merge_Feb_2021)

distinct CharityNumber if merge_Feb_2021==1

/* 
  1,668 charities in 2021_Feb_ar that are not in 2021_Feb_scr. Merge missing charities into register
  before using as base for Feb 2021. 
*/



// Cross check charity register and annual returns sheets in September 2021 excel file


import excel using "`datapath'\oscr_20210909.xlsx", sheet("mostrecent") firstrow clear

distinct CharityNumber

save 2021_Sept_scr.dta, replace


import excel using "`datapath'\oscr_20210909.xlsx", sheet("historical") firstrow clear

distinct CharityNumber

merge m:1 CharityNumber using 2021_Sept_scr.dta, gen(merge_Sept_2021)

distinct CharityNumber if merge_Sept_2021==1


/* 
  1,988 charities in 2021_Sept_ar that are not in 2021_Sept_scr. Merge missing charities into register
  before using as base for Sept 2021. 
*/



// Cross check charity register and annual returns from open data (12/04/23)


import delimited "`datapath'\CharityExport-12-Apr-2023.csv", clear

distinct charitynumber

save 2023_scr.dta, replace


import delimited "`datapath'\CharityExport-5Years-12-Apr-2023.csv", clear

distinct charitynumber

merge m:1 charitynumber using 2023_scr.dta, gen(merge_2023)


/*
  All charities in annual returns are present in charity register. 
  Use register and removed charities as base for open data. 
*/



// Take 2021 AR sheets and check that names and addresses are consistent within charitynumber

// February 2021

import excel using "`datapath'\oscr_20210203.xlsx", sheet("historical") firstrow clear

local counter = 1

foreach var in LegalName KnownByName PrincipalContactPostcode {
sort CharityNumber `var'
by CharityNumber (`var'), sort: gen same_`counter' = `var'[1] == `var'[_N]
tab same_`counter'
local counter = `counter' + 1
}


// September 2021

import excel using "`datapath'\oscr_20210909.xlsx", sheet("historical") firstrow clear

local counter = 1

foreach var in LegalName KnownByName PrincipalContactPostcode {
sort CharityNumber `var'
by CharityNumber (`var'), sort: gen same_`counter' = `var'[1] == `var'[_N]
tab same_`counter'
local counter = `counter' + 1
}

/*
  No issues here. 
*/


// Take SCR sheets, keep names, addresses, and dates. Rename and reformat variables. 
// Do same for AR sheets and merge with SCR to pick up missing charities in both 2021 updates 

// 2019 

use 2019_scr.dta, clear

rename CharityNumber charitynumber
rename LegalName name_2019
rename KnownByName knownas_2019
rename PrincipalContactAddressLine1 firstaddress_2019
rename PrincipalContactAddressLine2 secondaddress_2019
rename PrincipalContactAddressLine3 thirdaddress_2019
rename PrincipalContactAddressLine4 fourthaddress_2019
rename PrincipalContactAddressLine5 fifthaddress_2019
rename PrincipalContactPostcode postcode_2019
rename HeadOfficeOrMainOperatingLocatio localauthority_2019
rename FormerLegalName formername_2019

gen address_2019 = firstaddress_2019 + ", " + secondaddress_2019 + ", " + thirdaddress_2019 + ", " + fourthaddress_2019 + ", " + fifthaddress_2019

gen registerdate_2019 = dofc(RegisteredDate)
gen removeddate_2019 = dofc(RemovedDate)

format registerdate_2019 %td
format removeddate_2019 %td

keep charitynumber *_2019

gen type_2019="scr"

save 2019.dta, replace


// February 2021 (Annual returns)

import excel using "`datapath'\oscr_20210203.xlsx", sheet("historical") firstrow clear

rename CharityNumber charitynumber
rename LegalName name_Feb_2021
rename KnownByName knownas_Feb_2021
rename PrincipalContactPostcode postcode_Feb_2021
rename HeadOfficeOrMainOperatingLocatio localauthority_Feb_2021

keep charitynumber *_Feb_2021 RegisteredDate RemovedDate

duplicates drop charitynumber, force

gen type_Feb_2021="ar"

save 2021_Feb_ar.dta, replace


// February 2021 (Charity Register)

use 2021_Feb_scr.dta, clear


// Tidy up formatting of address variable

replace PrincipalOfficeTrusteesAddres = subinstr(PrincipalOfficeTrusteesAddres, ", ,", ",", .)
replace PrincipalOfficeTrusteesAddres = subinstr(PrincipalOfficeTrusteesAddres, ",,", ",", .)
replace PrincipalOfficeTrusteesAddres = subinstr(PrincipalOfficeTrusteesAddres, ",  ,", ",", .)

split PrincipalOfficeTrusteesAddres, p(,)

rename CharityNumber charitynumber
rename CharityName name_Feb_2021
rename KnownAs knownas_Feb_2021
rename PrincipalOfficeTrusteesAddres1 firstaddress_Feb_2021
rename PrincipalOfficeTrusteesAddres2 secondaddress_Feb_2021
rename PrincipalOfficeTrusteesAddres3 thirdaddress_Feb_2021
rename PrincipalOfficeTrusteesAddres4 fourthaddress_Feb_2021
rename PrincipalOfficeTrusteesAddres5 fifthaddress_Feb_2021
rename PrincipalOfficeTrusteesAddres6 sixthaddress_Feb_2021
rename PrincipalOfficeTrusteesAddres7 seventhaddress_Feb_2021
rename PrincipalOfficeTrusteesAddres8 eighthaddress_Feb_2021
rename PrincipalOfficeTrusteesAddres address_Feb_2021
rename Postcode postcode_Feb_2021
rename MainOperatingLocation localauthority_Feb_2021


// Merge annual returns data with register to pick up missing charities 

keep charitynumber *_Feb_2021 RegisteredDate

gen type_Feb_2021="scr"

merge 1:1 charitynumber using 2021_Feb_ar.dta

// Tidy up date formats (Formatting varies for pre-1900 registration dates so needs to be aligned)

gen dummy=1 if strpos(RegisteredDate, "00:00:00")
replace dummy=0 if dummy==.

replace RegisteredDate = subinstr(RegisteredDate, "00:00:00", "", .) if dummy==1
replace RegisteredDate = subinstr(RegisteredDate," ","",.) if dummy==1

gen registerdate1_Feb_2021 = date(RegisteredDate, "DMY") if dummy==1
format registerdate1_Feb_2021 %td if dummy==1

gen registerdate2_Feb_2021 = clock(RegisteredDate, "MDYhm") if dummy==0
format registerdate2_Feb_2021 %tc if dummy==0

replace registerdate2_Feb_2021 = dofc(registerdate2_Feb_2021) if dummy==0
format registerdate2_Feb_2021 %td

replace registerdate2_Feb_2021=registerdate1_Feb_2021 if dummy==1

rename registerdate2_Feb_2021 registerdate_Feb_2021

gen removeddate_Feb_2021 = dofc(RemovedDate)
format removeddate_Feb_2021 %td

drop _merge RegisteredDate RemovedDate registerdate1_Feb_2021

save Feb_2021.dta, replace

 
// September 2021 (Annual returns)

import excel using "`datapath'\oscr_20210909.xlsx", sheet("historical") firstrow clear

rename CharityNumber charitynumber
rename LegalName name_Sept_2021
rename KnownByName knownas_Sept_2021
rename PrincipalContactPostcode postcode_Sept_2021
rename HeadOfficeOrMainOperatingLocatio localauthority_Sept_2021

keep charitynumber *_Sept_2021 RegisteredDate RemovedDate

duplicates drop charitynumber, force

gen type_Sept_2021="ar"

save 2021_Sept_ar.dta, replace


// September 2021 (Charity Register)

use 2021_Sept_scr.dta, clear


// Tidy up formatting of address variable

replace PrincipalOfficeTrusteesAddres = subinstr(PrincipalOfficeTrusteesAddres, ", ,", ",", .)
replace PrincipalOfficeTrusteesAddres = subinstr(PrincipalOfficeTrusteesAddres, ",,", ",", .)
replace PrincipalOfficeTrusteesAddres = subinstr(PrincipalOfficeTrusteesAddres, ",  ,", ",", .)

split PrincipalOfficeTrusteesAddres, p(,)

rename CharityNumber charitynumber
rename CharityName name_Sept_2021
rename KnownAs knownas_Sept_2021
rename PrincipalOfficeTrusteesAddres1 firstaddress_Sept_2021
rename PrincipalOfficeTrusteesAddres2 secondaddress_Sept_2021
rename PrincipalOfficeTrusteesAddres3 thirdaddress_Sept_2021
rename PrincipalOfficeTrusteesAddres4 fourthaddress_Sept_2021
rename PrincipalOfficeTrusteesAddres5 fifthaddress_Sept_2021
rename PrincipalOfficeTrusteesAddres6 sixthaddress_Sept_2021
rename PrincipalOfficeTrusteesAddres7 seventhaddress_Sept_2021
rename PrincipalOfficeTrusteesAddres8 eighthaddress_Sept_2021
rename PrincipalOfficeTrusteesAddres address_Sept_2021
rename Postcode postcode_Sept_2021
rename MainOperatingLocation localauthority_Sept_2021


// Merge annual returns data with register to pick up missing charities 

keep charitynumber *_Sept_2021 RegisteredDate

gen type_Sept_2021="scr"

merge 1:1 charitynumber using 2021_Sept_ar.dta

// Tidy up date formats (Formatting varies for pre-1900 registration dates so needs to be aligned)

gen dummy=1 if strpos(RegisteredDate, "00:00:00")
replace dummy=0 if dummy==.

replace RegisteredDate = subinstr(RegisteredDate, "00:00:00", "", .) if dummy==1
replace RegisteredDate = subinstr(RegisteredDate," ","",.) if dummy==1

gen registerdate1_Sept_2021 = date(RegisteredDate, "DMY") if dummy==1
format registerdate1_Sept_2021 %td if dummy==1

gen registerdate2_Sept_2021 = clock(RegisteredDate, "MDYhm") if dummy==0
format registerdate2_Sept_2021 %tc if dummy==0

replace registerdate2_Sept_2021 = dofc(registerdate2_Sept_2021) if dummy==0
format registerdate2_Sept_2021 %td

replace registerdate2_Sept_2021=registerdate1_Sept_2021 if dummy==1

rename registerdate2_Sept_2021 registerdate_Sept_2021

gen removeddate_Sept_2021 = dofc(RemovedDate)
format removeddate_Sept_2021 %td

drop _merge RegisteredDate RemovedDate registerdate1_Sept_2021 

save Sept_2021.dta, replace

/*
  Note: AR sheets for 2021 excel files contain only postcode and not full address. 
  This may be an issue after we merge them with scr sheets to account for charities 
  missing from scr sheets. 

  Update: This only materially affects one charity, see later in file. 
*/


// Take open data for register and removed charities, merge them, and keep names, addresses, and dates

// Open data

import delimited "`datapath'\CharityExport-Removed-12-Apr-2023.csv", clear

append using 2023_scr.dta, force


// Tidy up formatting of address variable

replace principalofficetrusteesaddress = subinstr(principalofficetrusteesaddress, ", ,", ",", .)
replace principalofficetrusteesaddress = subinstr(principalofficetrusteesaddress, ",,", ",", .)
replace principalofficetrusteesaddress = subinstr(principalofficetrusteesaddress, ",  ,", ",", .)

split principalofficetrusteesaddress, p(,)

rename charityname name_2023
rename knownas knownas_2023
rename principalofficetrusteesaddress1 firstaddress_2023
rename principalofficetrusteesaddress2 secondaddress_2023
rename principalofficetrusteesaddress3 thirdaddress_2023
rename principalofficetrusteesaddress4 fourthaddress_2023
rename principalofficetrusteesaddress5 fifthaddress_2023
rename principalofficetrusteesaddress6 sixthaddress_2023
rename principalofficetrusteesaddress7 seventhaddress_2023
rename principalofficetrusteesaddress8 eighthaddress_2023
rename principalofficetrusteesaddress address_2023
rename postcode postcode_2023
rename mainoperatinglocation localauthority_2023

gen registerdate_2023 = date(registereddate, "DMY")
format registerdate_2023 %td

gen removeddate_2023 = date(ceaseddate, "DMY")
format removeddate_2023 %td

keep charitynumber *_2023 

save 2023.dta, replace



// Merge four iterations together

use 2019.dta, clear

merge 1:1 charitynumber using Feb_2021, gen(merge_1)
merge 1:1 charitynumber using Sept_2021, gen(merge_2)
merge 1:1 charitynumber using 2023.dta, gen(merge_3)

order merge_1 merge_2, before(merge_3)

drop dummy


// Look at nonsensical characters in csv files

foreach var of varlist name_* knownas_* firstaddress_* postcode_* formername_2019 {
count if strpos(`var', "€")
}

/*
Some parsing issues in the csv files are leading to the presence of non-sensical special characters, see below.

â€“ - Should be a hyphen
â€™s - Should be an apostrophe
â€˜ - Should be quotation mark
*/

// Replace special characters in name variables

foreach var of varlist name_* {
    count if strpos(`var', "â€™s")
    count if strpos(`var', "â€™")
    count if strpos(`var', "â€˜")
}

foreach var in name_Feb_2021 name_Sept_2021 {
    replace `var' = subinstr(`var', "â€™s", "'s", .)
    replace `var' = subinstr(`var', "â€™", "'", .)
    replace `var' = subinstr(`var', "â€˜", "'", .)
}

gen dummy_Feb=1 if strpos(name_Feb_2021, "€")
gen dummy_Sept=1 if strpos(name_Sept_2021, "€")

gen position_Feb = strpos(name_Feb_2021, "€") if dummy_Feb==1 
gen position_Sept = strpos(name_Sept_2021, "€") if dummy_Sept==1 

list name_Feb_2021 name_Sept_2021 if dummy_Sept==1
replace name_Feb_2021 = substr(name_Feb_2021, 1, position_Feb+2) + substr(name_Feb_2021, position_Feb+6, .) if dummy_Feb==1
replace name_Sept_2021 = substr(name_Sept_2021, 1, position_Sept+2) + substr(name_Sept_2021, position_Sept+6, .) if dummy_Sept==1
list name_Feb_2021 name_Sept_2021 if dummy_Sept==1


foreach var in name_Feb_2021 name_Sept_2021 {
    replace `var' = subinstr(`var', "â€", "–", .)
}

list name_Feb_2021 name_Sept_2021 if dummy_Sept==1

drop dummy* position*


// Replace some characters in knownas and firstaddress

foreach var of varlist knownas_* firstaddress_* {
    count if strpos(`var', "â€™s")
    count if strpos(`var', "â€™")
}


list knownas_Feb_2021 knownas_Sept_2021 if inlist(charitynumber, "SC002152", "SC008707", "SC011901", "SC013890", "SC014292", "SC016055", "SC037605", "SC038191", "SC047083")

foreach var of varlist knownas_Feb_2021 knownas_Sept_2021 {
    replace `var' = subinstr(`var', "â€™s", "'s", .)
    replace `var' = subinstr(`var', "â€™", "'", .)
}

list knownas_Feb_2021 knownas_Sept_2021 if inlist(charitynumber, "SC002152", "SC008707", "SC011901", "SC013890", "SC014292", "SC016055", "SC037605", "SC038191", "SC047083")


list firstaddress_Feb_2021 firstaddress_Sept_2021 if inlist(charitynumber, "SC002963", "SC014585", "SC016739", "SC030078", "SC035261", "SC039461", "SC039842")

foreach var of varlist firstaddress_Feb_2021 firstaddress_Sept_2021 {
    replace `var' = subinstr(`var', "â€™s", "'s", .)
    replace `var' = subinstr(`var', "â€™", "'", .)
}

list firstaddress_Feb_2021 firstaddress_Sept_2021 if inlist(charitynumber, "SC002963", "SC014585", "SC016739", "SC030078", "SC035261", "SC039461", "SC039842")


// Remove references to insolvency proceedings

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
count if strpos(`var', "(subject to")
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
gen `var'_dummy=1 if strpos(`var', "(subject to")
replace `var'_dummy=0 if `var'_dummy==.
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
list `var' if `var'_dummy==1
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
gen position_`var' = strpos(`var', "(subject") if `var'_dummy==1
} 

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
replace `var' = substr(`var', 1, position_`var'-1) if `var'_dummy==1
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
list `var' if `var'_dummy==1
}

drop *_dummy position*



foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
count if strpos(`var', "- subject to")
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
gen `var'_dummy=1 if strpos(`var', "- subject to")
replace `var'_dummy=0 if `var'_dummy==.
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
list `var' if `var'_dummy==1
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
gen position_`var' = strpos(`var', "- subject") if `var'_dummy==1
} 

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
replace `var' = substr(`var', 1, position_`var'-1) if `var'_dummy==1
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
list `var' if `var'_dummy==1
}

drop *_dummy position*

replace name_2023=subinstr(name_2023,"( ","(",.) if charitynumber=="SC024505"



foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
count if strpos(`var', " subject to")
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
gen `var'_dummy=1 if strpos(`var', " subject to")
replace `var'_dummy=0 if `var'_dummy==.
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
list `var' if `var'_dummy==1
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
gen position_`var' = strpos(`var', " subject") if `var'_dummy==1
} 

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
replace `var' = substr(`var', 1, position_`var'-1) if `var'_dummy==1
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
list `var' if `var'_dummy==1
}

drop *_dummy position*



foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
count if strpos(`var', "('subject to")
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
gen `var'_dummy=1 if strpos(`var', "('subject to")
replace `var'_dummy=0 if `var'_dummy==.
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
list `var' if `var'_dummy==1
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
gen position_`var' = strpos(`var', "('subject") if `var'_dummy==1
} 

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
replace `var' = substr(`var', 1, position_`var'-1) if `var'_dummy==1
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
list `var' if `var'_dummy==1
}

drop *_dummy position*



foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
count if strpos(`var', "'subject to")
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
gen `var'_dummy=1 if strpos(`var', "'subject to")
replace `var'_dummy=0 if `var'_dummy==.
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
list `var' if `var'_dummy==1
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
gen position_`var' = strpos(`var', "'subject") if `var'_dummy==1
} 

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
replace `var' = substr(`var', 1, position_`var'-1) if `var'_dummy==1
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
list `var' if `var'_dummy==1
}

drop *_dummy position*



foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
count if strpos(`var', "(subject to")
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
gen `var'_dummy=1 if strpos(`var', "(subject to")
replace `var'_dummy=0 if `var'_dummy==.
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
list `var' if `var'_dummy==1
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
gen position_`var' = strpos(`var', "(subject") if `var'_dummy==1
} 

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
replace `var' = substr(`var', 1, position_`var'-1) if `var'_dummy==1
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
list `var' if `var'_dummy==1
}

drop *_dummy position*



foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
count if strpos(`var', "subject to")
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
gen `var'_dummy=1 if strpos(`var', "subject to")
replace `var'_dummy=0 if `var'_dummy==.
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
list `var' if `var'_dummy==1
}

gen position = strpos(name_2019, "subject") if name_2019_dummy==1

replace name_2019 = substr(name_2019, 1, position-2) + substr(name_2019, position, .) if name_2019_dummy==1

list name_2019 if name_2019_dummy==1

drop position *_dummy



foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
count if strpos(`var', "(subject to")
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
gen `var'_dummy=1 if strpos(`var', "(subject to")
replace `var'_dummy=0 if `var'_dummy==.
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
list `var' if `var'_dummy==1
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
gen position_`var' = strpos(`var', "(subject") if `var'_dummy==1
} 

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
replace `var' = substr(`var', 1, position_`var'-1) if `var'_dummy==1
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
list `var' if `var'_dummy==1
}

drop *_dummy position*




foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
count if strpos(`var', "subject to")
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
gen `var'_dummy=1 if strpos(`var', "subject to")
replace `var'_dummy=0 if `var'_dummy==.
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
list `var' if `var'_dummy==1
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
gen position_`var' = strpos(`var', "subject") if `var'_dummy==1
} 

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
replace `var' = substr(`var', 1, position_`var'-1) if `var'_dummy==1
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
list `var' if `var'_dummy==1
}

drop *_dummy position*



foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
count if strpos(`var', "(Subject to")
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
gen `var'_dummy=1 if strpos(`var', "(Subject to")
replace `var'_dummy=0 if `var'_dummy==.
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
list `var' if `var'_dummy==1
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
gen position_`var' = strpos(`var', "(Subject to") if `var'_dummy==1
} 

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
replace `var' = substr(`var', 1, position_`var'-1) if `var'_dummy==1
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
list `var' if `var'_dummy==1
}

drop *_dummy position*



foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
count if strpos(`var', " - Subject")
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
gen `var'_dummy=1 if strpos(`var', " - Subject")
replace `var'_dummy=0 if `var'_dummy==.
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
list `var' if `var'_dummy==1
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
gen position_`var' = strpos(`var', " - Subject") if `var'_dummy==1
} 

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
replace `var' = substr(`var', 1, position_`var'-1) if `var'_dummy==1
}

foreach var in name_2019 name_Feb_2021 name_Sept_2021 name_2023 {
list `var' if `var'_dummy==1
}

drop *_dummy position*



// Normalise names and addresses across all iterations
// Create new variables and reformat to check for differences

// Remove leading spaces from string variables identified through 'codebook *, problems'
	
	codebook *, problems

	foreach var of varlist name_* knownas_* firstaddress_* postcode_* formername_* {
		gen `var'_alt = `var'
	}

	foreach var of varlist *_alt {
		replace `var' = ltrim(`var')
	}

	foreach var of varlist *_alt {
		replace `var' = rtrim(`var')
	}

// Remove all spaces from postcode variables

foreach var in postcode_2019 postcode_Feb_2021 postcode_Sept_2021 postcode_2023 {
replace `var'_alt=subinstr(`var'_alt," ","",.)
}


// Remove punctuations from postcode variables

foreach var in postcode_2019 postcode_Feb_2021 postcode_Sept_2021 postcode_2023 {
replace `var'_alt=subinstr(`var'_alt,".","",.)
}

foreach var in postcode_2019 postcode_Feb_2021 postcode_Sept_2021 postcode_2023 {
replace `var'_alt=subinstr(`var'_alt,",","",.)
}

foreach var in postcode_2019 postcode_Feb_2021 postcode_Sept_2021 postcode_2023 {
replace `var'_alt=subinstr(`var'_alt,"?","",.)
}


// Convert strings to lower case 

foreach var of varlist *_alt {
replace `var' = strlower(`var')
}

// Collapse consecutive internal blanks to one blank 

foreach var of varlist *_alt {
replace `var' = itrim(`var')
}

codebook *_alt, problems

save oscr_register.dta, replace


// For name, 'known as', postcode, and first line of address, check if these differ between iterations and are not missing.


// Create list of charities that have 'deleted' as their only name across iterations

keep charitynumber *_alt

drop firstaddress* postcode*

distinct charitynumber

rename name_2019_alt name1
rename name_Feb_2021_alt name2
rename name_Sept_2021_alt name3
rename name_2023_alt name4

rename knownas_2019_alt name5
rename knownas_Feb_2021_alt name6
rename knownas_Sept_2021_alt name7
rename knownas_2023_alt name8

rename formername_2019_alt name9

reshape long name, i(charitynumber) j(count)

count if name=="deleted"

drop if missing(name)

duplicates drop charitynumber name, force

distinct charitynumber

drop if name=="deleted"

keep charitynumber

duplicates drop charitynumber, force

save valid_names.dta, replace




// Create a data file for each of distinct names, addresses, and dates for merging

use oscr_register.dta, clear

// Charity names

// Rename variables

keep charitynumber *_alt name* knownas* formername*

drop firstaddress* postcode*

distinct charitynumber

rename name_2019 name1
rename name_Feb_2021 name2
rename name_Sept_2021 name3
rename name_2023 name4

rename knownas_2019 name5
rename knownas_Feb_2021 name6
rename knownas_Sept_2021 name7
rename knownas_2023 name8

rename formername_2019 name9

rename name_2019_alt name_alt1
rename name_Feb_2021_alt name_alt2
rename name_Sept_2021_alt name_alt3
rename name_2023_alt name_alt4

rename knownas_2019_alt name_alt5
rename knownas_Feb_2021_alt name_alt6
rename knownas_Sept_2021_alt name_alt7
rename knownas_2023_alt name_alt8

rename formername_2019_alt name_alt9


reshape long name name_alt, i(charitynumber) j(count)


// Append names from 2012 file (added in December 2023)

preserve 

import excel using "`datapath'\sc_chars2012.xlsx", firstrow clear


// Keep and rename revelant variables

keep name_unified OSCRname sc_num1

rename OSCRname name0
rename name_unified name1
rename sc_num1 charitynumber


// Reshape data to deduplicate and append to OSCR register

reshape long name, i(charitynumber) j(count)

sort charitynumber count

// Remove references to insolvency from 2012 names

count if strpos(name, "(subject to")
count if strpos(name, "(SUBJECT TO")

gen name_dummy=1 if strpos(name, "(subject to")
replace name_dummy=1 if strpos(name, "(SUBJECT TO")
replace name_dummy=0 if name_dummy==.

list name if name_dummy==1

gen position_name = strpos(name, "(subject to") if name_dummy==1
replace position_name = strpos(name, "(SUBJECT TO") if name_dummy==1 & position_name==0

replace name = substr(name, 1, position_name-1) if name_dummy==1

list name if name_dummy==1

replace name = rtrim(name) if name_dummy==1

drop *_dummy position*


// Standardise name variable

gen name_alt = name
replace name_alt = ltrim(name_alt)
replace name_alt = rtrim(name_alt)

// Convert strings to lower case 

replace name_alt = strlower(name_alt)

// Collapse consecutive internal blanks to one blank 

replace name_alt = itrim(name_alt)

codebook name_alt, problems


// Deduplicate 2012 names

sort charitynumber count

duplicates drop charitynumber name_alt, force

replace count= -1 if count==0
replace count= 0 if count==1

save 2012_names.dta, replace

restore


// Append 2012 names

append using 2012_names.dta

sort charitynumber count


// Keep charity numbers with valid names

distinct charitynumber

merge m:1 charitynumber using valid_names, gen(name_merge)

drop if name_merge==1

distinct charitynumber

count if name_alt=="deleted"

drop if missing(name_alt)

distinct charitynumber


// Create variables to id type and source of different names

rename count source 

label define source_label -1 "2012 Name" 0 "2012 Alt Name" 1 "2019 Name" 2 "Feb 2021 Name" 3 "Sept 2021 Name" 4 "2023 Name" ///
5 "2019 Known As" 6 "Feb 2021 Known As" 7 "Sept 2021 Known As" 8 "2023 Known as" 9 "2019 Former Name"
label values source source_label

gen register=0 if inlist(source, -1, 0)
replace register=1 if inlist(source, 1,5,9)
replace register=2 if inlist(source, 2,6)
replace register=3 if inlist(source, 3,7)
replace register=4 if inlist(source, 4,8)

label define register_label 0 "2012" 1 "2019" 2 "Feb 2021" 3 "Sept 2021" 4 "2023"
label values register register_label

tab register

tab source

// Drop duplicates and names == "deleted"

sort charitynumber register source

duplicates drop charitynumber name_alt, force

distinct charitynumber

drop if name_alt=="deleted"


distinct charitynumber

drop name_merge name_alt

save distinct_names.dta, replace


// Addresses

use oscr_register.dta, clear

// Figure out which charities have more than one unique address

/*
  Going to do this based on first address line + postcode. 
  Using any more than this creates too many permutations, especially
  when we consider the arbitrary way that formatting/ordering of 
  addresses may differ across data iterations.  
*/

gen concat_2019 = firstaddress_2019_alt + " " + postcode_2019_alt

gen concat_Feb_2021 = firstaddress_Feb_2021_alt + " " + postcode_Feb_2021_alt

gen concat_Sept_2021 = firstaddress_Sept_2021_alt + " " + postcode_Sept_2021_alt

gen concat_2023 = firstaddress_2023_alt + " " + postcode_2023_alt

keep charitynumber concat* *address* type_Feb_2021 type_Sept_2021 postcode* localauthority*

drop firstaddress_2019_alt firstaddress_Feb_2021_alt firstaddress_Sept_2021_alt firstaddress_2023_alt


// Rename variables and reshape data

local var "concat firstaddress secondaddress thirdaddress fourthaddress fifthaddress sixthaddress seventhaddress eighthaddress address postcode localauthority"
tokenize "`var'"

foreach i of local var {
rename `i'_2023 `i'4
rename `i'_Sept_2021 `i'3
rename `i'_Feb_2021 `i'2
}

rename type_Sept_2021 type3
rename type_Feb_2021 type2

local var "concat firstaddress secondaddress thirdaddress fourthaddress fifthaddress address postcode localauthority"
tokenize "`var'"

foreach i of local var {
rename `i'_2019 `i'1
}

rename postcode_2023_alt postcode_alt4
rename postcode_Sept_2021_alt postcode_alt3
rename postcode_Feb_2021_alt postcode_alt2
rename postcode_2019_alt postcode_alt1

reshape long concat firstaddress secondaddress thirdaddress fourthaddress fifthaddress sixthaddress /// 
seventhaddress eighthaddress address postcode localauthority type postcode_alt, i(charitynumber) j(count)

distinct charitynumber

// Merge with valid names data to drop names == "deleted"

merge m:1 charitynumber using valid_names, gen(name_merge)

drop if name_merge==1

distinct charitynumber



// Drop missing values for concatenated address and drop duplicate addresses

drop if concat==" "

distinct charitynumber

duplicates drop charitynumber concat, force

distinct charitynumber


preserve

// Check if any of the ar duplicates provide a postcode that doesn't exist elsewhere in the data

bysort charitynumber: gen ar=1 if type=="ar"
bysort charitynumber (ar): replace ar=ar[1] if ar[1]!=.

distinct charitynumber if type=="ar"

keep if ar==1

distinct charitynumber

by charitynumber (postcode_alt), sort: gen diff = postcode_alt[1] != postcode_alt[_N] 

drop if diff==0

sort charitynumber count

by charitynumber: gen count2 = _N

gen ar_postcode=postcode_alt if type=="ar"

sort ar_postcode charitynumber

bysort charitynumber (ar_postcode) : replace ar_postcode = ar_postcode[_N] if ar_postcode[_N]!=""

drop if type=="ar"

gen same=1 if postcode_alt==ar_postcode
bysort charitynumber (same): replace same=same[1] if same[1]!=.

list charitynumber if same!=1

/*
  Look like SC043485 is the only one that has just a postcode and
  isn't replicated in other rows. 

  SC044176 and SC044222 do not have valid duplicates so we can save these too.
*/

restore

distinct charitynumber

drop if type=="ar" & !inlist(charitynumber, "SC044176", "SC044222", "SC043485")

distinct charitynumber


// Drop if address data == "- xx00xx"

drop if concat=="- xx00xx"

distinct charitynumber


// Create variables to link addresses to the list of unique names

rename count source

label define source_label 1 "2019 Name" 2 "Feb 2021 Name" 3 "Sept 2021 Name" 4 "2023 Name"
label values source source_label

tab source

drop name_merge concat postcode_alt

save distinct_addresses.dta, replace



// Registration and removal dates

use oscr_register.dta, clear


// Rename variables

local var "registerdate removeddate"
tokenize "`var'"

foreach i of local var {
rename `i'_2023 `i'4
rename `i'_Sept_2021 `i'3
rename `i'_Feb_2021 `i'2
rename `i'_2019 `i'1
}


// Keep relevant variables and reshape data

keep charitynumber registerdate* removeddate*

reshape long registerdate removeddate, i(charitynumber) j(count)


// Drop charities that have 'deleted' as their only name

distinct charitynumber

merge m:1 charitynumber using valid_names, gen(name_merge)

drop if name_merge==1

distinct charitynumber

drop name_merge


// Drop rows with missing info

distinct charitynumber

drop if registerdate==. & removeddate==.

distinct charitynumber


// Inspect differing registration dates

preserve

drop removeddate

by charitynumber (registerdate), sort: gen diff1 = registerdate[1] != registerdate[_N] & registerdate!=.

duplicates drop charitynumber registerdate, force

keep if diff1==1

sort charitynumber registerdate

tab count if !inlist(charitynumber, "SC038378", "SC024047", "SC025702")

drop count

by charitynumber: gen count=_n

reshape wide registerdate, i(charitynumber) j(count)

gen date_diff = registerdate1-registerdate2
replace date_diff=abs(date_diff)

/*
  For 194 of 197 charities that have conflicting registration dates, the difference is just one day. This seems 
  to be an issue with the 2019 data iteration and how it handled date values that predated the 1900s. For these
  cases, it looks like we get the correct registration date if we keep the date that originates in the data 
  iteration that isn't 2019. Keep non-2019 versions. 

  For SC038378, SC024047, SC025702, the more recent registration date aligns with OSCR
  site while the earlier date is listed under 'Constitutional Form Date' on the OSCR site. 
  Keep both. 
*/

restore


// Inspect differing removal dates


preserve

drop registerdate

drop if removeddate==.

by charitynumber (removeddate), sort: gen diff2 = removeddate[1] != removeddate[_N] & removeddate!=.

/*
  Two charities (SC000025 and SC041371) with conflicting dates of removal so keep both. 
*/

restore



// Create files to merge with other data

preserve

drop removeddate

by charitynumber (registerdate), sort: gen diff1 = registerdate[1] != registerdate[_N] & registerdate!=.

sort charitynumber count

duplicates drop charitynumber registerdate, force

sort charitynumber registerdate

tab count if !inlist(charitynumber, "SC038378", "SC024047", "SC025702") & diff1==1

drop if diff1==1 & count==1 & !inlist(charitynumber, "SC038378", "SC024047", "SC025702")

replace diff1=0 if !inlist(charitynumber, "SC038378", "SC024047", "SC025702")

rename count source

label define source_label 1 "2019 Name" 2 "Feb 2021 Name" 3 "Sept 2021 Name" 4 "2023 Name"
label values source source_label

drop diff1

save reg_date_oscr.dta, replace

restore


preserve

drop registerdate

drop if removeddate==.

by charitynumber (removeddate), sort: gen diff2 = removeddate[1] != removeddate[_N] & removeddate!=.

sort charitynumber count

duplicates drop charitynumber removeddate, force

sort charitynumber removeddate

rename count source

label define source_label 1 "2019 Name" 2 "Feb 2021 Name" 3 "Sept 2021 Name" 4 "2023 Name"
label values source source_label

drop diff2

save rem_date_oscr.dta, replace

restore


// Merge files together into spine

clear all

use distinct_names.dta

merge 1:1 charitynumber source using distinct_addresses, gen(address_merge)

drop count type address_merge

sort charitynumber source

distinct charitynumber


merge 1:1 charitynumber source using reg_date_oscr, gen(reg_merge)

merge 1:1 charitynumber source using rem_date_oscr, gen(rem_merge)

sort charitynumber source

distinct charitynumber

drop *_merge


// Tidy up variables, rename and reorder

gen dummy=1 if register==.

replace register=0 if inlist(source, -1,0) & register==.
replace register=1 if inlist(source, 1,5,9) & register==.
replace register=2 if inlist(source, 2,6) & register==.
replace register=3 if inlist(source, 3,7) & register==.
replace register=4 if inlist(source, 4,8) & register==.

replace source=. if dummy==1
drop dummy


gen uid=.
order uid, before (charitynumber)
gen companyid=.
order companyid, after (name)


rename name organisationname
rename firstaddress addressline1
rename secondaddress addressline2
rename thirdaddress addressline3
rename fourthaddress addressline4
rename fifthaddress addressline5
rename sixthaddress addressline6
rename seventhaddress addressline7
rename eighthaddress addressline8
rename source name_origin

gen source="OSCR"

order localauthority postcode, after(addressline8)
order name_origin register, after(source)

order address, before(addressline1)

sort charitynumber

gen city=""

order city, before(localauthority)

gen normalisedname=""

order normalisedname, after(organisationname)

gen housenumber=""

order housenumber, after(address)

order source, after(register)

rename register iteration


// Merge 2012 charity and company numbers into file

preserve

import excel using "`datapath'\sc_chars2012.xlsx", firstrow clear

keep sc_num1 sc_num2 companynumber1 companynumber2 companynumber3

rename sc_num1 charitynumber
rename sc_num2 charitynumber_2012
rename companynumber1 companyid1_2012
rename companynumber2 companyid2_2012
rename companynumber3 companyid3_2012

drop if charitynumber_2012=="" & companyid1_2012=="" & companyid2_2012=="" & companyid3_2012==""

save oscr_ids_2012.dta, replace

restore

merge m:1 charitynumber using oscr_ids_2012.dta, gen(merge_2012)

drop merge_2012

order source, after(companyid3_2012)

export delimited oscr_spine_public.csv, quote replace



// Add binary variable to indicate cross border or dual registered organisations (Added in March 2024)


// 2019 

use 2019_scr.dta, clear

rename CharityNumber charitynumber
rename Type type
rename RegulatoryForm form

keep charitynumber type form

gen dummy = 1 if type =="CrossBorder"
replace dummy = 1 if form=="DualRegistration"

keep if dummy==1

save crossborder_2019.dta, replace


// February 2021 (Annual returns)

import excel using "`datapath'\oscr_20210203.xlsx", sheet("historical") firstrow clear

rename CharityNumber charitynumber
rename Type type
rename RegulatoryForm form

keep charitynumber type form

gen dummy = 1 if type =="CrossBorder"
replace dummy = 1 if form=="DualRegistration"

keep if dummy==1

duplicates drop charitynumber, force

save crossborder_2021_Feb_ar.dta, replace


// February 2021 (Charity Register)

use 2021_Feb_scr.dta, clear

rename CharityNumber charitynumber
rename RegulatoryType type
rename RegulatoryForm form

keep charitynumber type form

gen dummy = 1 if type =="Cross Border"
replace dummy = 1 if form=="DualRegistration"

keep if dummy==1

save crossborder_2021_Feb_scr.dta, replace

 
// September 2021 (Annual returns)

import excel using "`datapath'\oscr_20210909.xlsx", sheet("historical") firstrow clear

rename CharityNumber charitynumber
rename Type type
rename RegulatoryForm form

keep charitynumber type form

gen dummy = 1 if type =="CrossBorder"
replace dummy = 1 if form=="DualRegistration"

keep if dummy==1

duplicates drop charitynumber, force

save crossborder_2021_Sept_ar.dta, replace


// September 2021 (Charity Register)

use 2021_Sept_scr.dta, clear

rename CharityNumber charitynumber
rename RegulatoryType type
rename RegulatoryForm form

keep charitynumber type form

gen dummy = 1 if type =="Cross Border"
replace dummy = 1 if form=="DualRegistration"

keep if dummy==1

save crossborder_2021_Sept_scr.dta, replace


// April 2023

// Open data

import delimited "`datapath'\CharityExport-Removed-12-Apr-2023.csv", clear

append using 2023_scr.dta, force

rename regulatorytype type

keep charitynumber type

gen dummy = 1 if type =="Cross Border"

keep if dummy==1

save crossborder_2023.dta, replace


// Merge four iterations together

use crossborder_2019.dta, clear

append using crossborder_2021_Feb_scr
append using crossborder_2021_Feb_ar
append using crossborder_2021_Sept_scr
append using crossborder_2021_Sept_ar
append using crossborder_2023.dta

drop type form dummy

duplicates drop charitynumber, force

save crossborder.dta, replace

// Import spine and add cross border variable

clear all

import delimited oscr_spine_public.csv, bindquote(strict)

merge m:1 charitynumber using crossborder.dta, gen(crossborder_merge)

gen crossborder=1 if crossborder_merge==3
replace crossborder=0 if crossborder==.

drop crossborder_merge

export delimited oscr_spine_public.csv, quote replace



// Remove strings from address fields that are not useful (March 2024)

foreach var of varlist addressline1-addressline8 {
foreach str in "Please select a state" ///
               "Please select your State" ///
               "Please select one..." ///
               "Please select county" ///
               "Please select a region" ///
               "Please select county" ///
               "state or province" ///
               "Please select region" ///
               "select region" ///
               "Please select..." ///
               "Please select ..." ///
               "Please select" ///
               "*** Please Select ***" ///
               "Please Select" ///
               "Select a county" ///
               "Select County" ///
               "Select One" ///
               "County (optional)" ///
               "County optional" ///
               "Select a Region" ///
               "Select Region" ///
               "Select county" ///
               "Select..." ///
               "Select a state..." ///
               "Select a state" ///
               "Choose State" ///
               "Choose your County" ///
               "Choose County" ///
               "-- Select --" ///
               "-- Select State (US Only) --" ///
               "-- Select State/Province --" ///
               "State/Province/Region ..." ///
               "Non-US State or province" ///
               "-- Select Country (US Only) --" ///
               "- Select -" ///
               "Select" {
        replace `var' = subinstr(`var', "`str'", "", .) if charitynumber!="SC043410"
    }
}


// Additional processing (Added May 2024)

drop if iteration=="2023" & charitynumber=="SC030153"
drop if iteration=="2023" & charitynumber=="SC036867"
drop if iteration=="2023" & charitynumber=="SC038482"
drop if iteration=="2023" & charitynumber=="SC048129"


export delimited oscr_spine_public.csv, quote replace

END
