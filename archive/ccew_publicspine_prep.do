// File: ccew_publicspine_prep.do
// Creator: Alan Duggan
// Created: 07/11/2023
// Updated: 16/04/2024

******* Overview *******



/* 
	This DO file outlines the steps taken to transform English and Welsh charity data 
        (charity register and removed charities) into a spine dataset of organisations. 
	
	This do file performs the following tasks:
	- imports dataset from March 2023
	- cleans dataset
        - uses historical snapshots to capture additional names, addresses, and company numbers
        - constructs dataset for linkage
		
	The data files used in this script:
	- CC_appended_March23.dta [English and Welsh Charity Register - March 2023]
        - CC_charity_other_names.dta [File containing additional names for English and Welsh charities]
	- ccr2001_repaired.dta [Historical file from 2001, used to extract charity names, addresses, company numbers, dates of registration and removal]
        - 24 historical snapshots from June 2011, March 2012–2019, April 2020–21, and March 2022 [Used to extract charity names, addresses, 
          dates of registration and removal]

*/


/* Define path */

local datapath C:\Users\ad92\Desktop\CCEW


// Import data

use "`datapath'\CC_appended_March23.dta"


// Keep relevant variables

keep registered_charity_number charity_company_registration_num charity_name charity_contact_address1 charity_contact_address2 ///
charity_contact_address3 charity_contact_address4 charity_contact_address5 charity_contact_postcode

// Rename variables

rename registered_charity_number charitynumber
rename charity_name name
rename charity_company_registration_num coyno
rename charity_contact_address1 firstaddress
rename charity_contact_address2 secondaddress
rename charity_contact_address3 thirdaddress
rename charity_contact_address4 fourthaddress
rename charity_contact_address5 fifthaddress
rename charity_contact_postcode postcode

// Look for duplicate charity numbers

duplicates tag _all, gen(dupall)

tab dupall

/*
  Looks like three genuine exact duplicates, can drop these.
*/

duplicates drop charitynumber, force

drop dupall


// Create name_alt variable to use in de-duplicating process
	
	codebook *, problems


// Remove leading blanks from name variable

	gen name_alt = ltrim(name)


// Convert name_alt to lower case 

replace name_alt = strlower(name_alt)


// Collapse consecutive internal blanks in name_alt to one blank 

replace name_alt = itrim(name_alt)


// Create binary variable to indicate observations came from main 2023 data file

gen name_origin=13

save ccew_register_public.dta, replace



// Import additional names data, keep and rename relevant variables

use "`datapath'\CC_charity_other_names.dta", clear

keep registered_charity_number charity_name

rename registered_charity_number charitynumber
rename charity_name name


// Create name_alt variable, remove leading and trailing blanks
	
	codebook *, problems

	gen name_alt = ltrim(name)
        replace name_alt = rtrim(name_alt)


// Convert name_alt to lower case 

replace name_alt = strlower(name_alt)


// Collapse consecutive internal blanks in name_alt to one blank 

replace name_alt = itrim(name_alt)


// Drop observation with missing value for name

drop if charitynumber==1138073


// Drop duplicate names

duplicates tag charitynumber name_alt, gen(name_dup)

tab name_dup

duplicates drop charitynumber name_alt, force

drop name_dup


// Create binary variable to indicate observations came from other names data file

gen name_origin=14

save othernames_public.dta, replace



// Import register data to merge with other names data

use ccew_register_public.dta, clear

append using othernames_public.dta

sort charitynumber


// Drop duplicate names

duplicates tag charitynumber name_alt, gen(name_dup)

tab name_dup

// Keep duplicates originating in main 2023 file, drop those from other names file

drop if name_dup==1 & name_origin==14

drop name_dup

save ccew_register_public.dta, replace


// Import 2001–2022 historical data to check for additional names not in other files 


// 2001

use "`datapath'\ccr2001_repaired.dta", clear

// Create variable to tag primary info

sort cc_num sub_num

bysort cc_num: gen rank=_n

gen primary=1 if rank==1

// Keep and rename relevant variables

keep name cc_num primary rank

rename cc_num charitynumber

gen name_origin=0

save 2001_snapshot_name.dta, replace


// March 2022

import delimited "`datapath'\March22_snapshot.txt", varnames(1) bindquotes(nobind) delimiter("\t") clear

// Keep and rename relevant variables

keep registered_charity_number linked_charity_number charity_name

rename registered_charity_number charitynumber
rename charity_name name
rename linked_charity_number subno


// Create variable to tag primary info

sort charitynumber subno

bysort charitynumber: gen rank=_n

gen primary=1 if rank==1

keep name charitynumber primary rank

gen name_origin=12

save March22_snapshot_name.dta, replace


// June 2011

import delimited "`datapath'\June11_snapshot.txt", varnames(1) bindquotes(strict) delimiter(",") maxquotedrows(200) clear


// Create variable to keep track of data iterations, fill in using loop below

gen name_origin=1


// March 2012-2019

// Append data from 2012–2019 and fill in iteration variable

local counter=2

forval year=12(1)19 {
append using "`datapath'\March`year'_snapshot.dta", force
replace name_origin=`counter' if name_origin==.
local counter = `counter' + 1
}

// Append data from 2020–2021 and fill in iteration variable

forval year=20(1)21 {
append using "`datapath'\April`year'_snapshot.dta", force
replace name_origin=`counter' if name_origin==.
local counter = `counter' + 1
}

// Keep relevant variables

keep regno subno name name_origin

rename regno charitynumber


// Create variable to tag primary info

sort charitynumber subno

egen panel = group(charitynumber name_origin)

sort panel subno

bysort panel: gen rank=_n

gen primary=1 if rank==1

drop panel subno

// Append data from 2001 and 2022

append using 2001_snapshot_name.dta

append using March22_snapshot_name.dta

sort charitynumber name_origin rank


// / Create name_alt variable with leading and trailing spaces removed
	
	codebook *, problems

	gen name_alt = ltrim(name)
        replace name_alt = rtrim(name_alt)


// Convert name_alt to lower case 

replace name_alt = strlower(name_alt)


// Collapse consecutive internal blanks in name_alt to one blank 

replace name_alt = itrim(name_alt)


// Drop missing values

mdesc

drop if missing(name_alt)


// Drop duplicate names, keeping earliest appearance of a unique name

duplicates tag charitynumber name_alt, gen(name_dup)

tab name_dup

sort charitynumber name_origin

duplicates drop charitynumber name_alt, force

drop name_dup


save historical_names_public.dta, replace



// Import 2023 register data to merge with historical names data

use ccew_register_public.dta, clear

append using historical_names_public.dta

sort charitynumber


// Label iteration variable

label define iteration_label 0 "2001" 1 "2011" 2 "2012" 3 "2013" 4 "2014" 5 "2015" 6 "2016" 7 "2017" 8 "2018" ///
9 "2019" 10 "2020" 11 "2021" 12 "2022" 13 "2023" 14 "Other"
label values name_origin iteration_label 

tab name_origin


// Fill out company number variable within charitynumber (for later linkage)

replace coyno="" if coyno=="."

bysort charitynumber (coyno): replace coyno = coyno[_N]


replace primary=1 if name_origin==13


// Drop duplicate names, keeping earliest appearance of a unique name 

sort charitynumber name_origin

duplicates drop charitynumber name_alt, force

drop name_alt


// Amend primary variable so it tags only one name per charity

by charitynumber: egen primary_year = max(name_origin) if primary==1

gen primary_name = 1 if primary==1 & name_origin==primary_year

drop rank primary primary_year

save ccew_spine_public.dta, replace

distinct charitynumber



// Import 2001 data to see if it improves coverage of company numbers

use "`datapath'\ccr2001_repaired.dta", clear

// Keep and rename relevant variables

keep name cc_num comp_num

rename cc_num charitynumber
rename comp_num coyno_2001

// Drop observations with missing values for company number

drop if missing(coyno_2001)

drop name

save ccew_2001_coyno_public.dta, replace



// Merge register data with ccew_2001_coyno to check for additional coverage of company numbers


use ccew_spine_public.dta, clear

merge m:1 charitynumber using ccew_2001_coyno_public.dta, gen(merge_coyno)


// Keep observations that matched from the 2001 data

keep if merge_coyno==3

// Keep relevant variables

keep charitynumber coyno coyno_2001


// Drop duplicates

duplicates drop charitynumber coyno, force


// Remove trailing blanks from coyno variable

codebook*, problems

replace coyno = rtrim(coyno)



// Create new variables to compare the two coyno variables 

/*
  Need to do a few iterations below to account for different formatting
  and root out company numbers that match in 2001 and 2023. 
*/

tostring coyno_2001, gen(coyno_2001_test)

gen coyno_2001_string = "0000" + coyno_2001_test

gen same=1 if coyno==coyno_2001_string

drop if same==1

drop same


replace coyno_2001_string = "000" + coyno_2001_test

gen same=1 if coyno==coyno_2001_string

drop if same==1

drop same


replace coyno_2001_string = "00" + coyno_2001_test

gen same=1 if coyno==coyno_2001_string

drop if same==1

drop same 


replace coyno_2001_string = "0" + coyno_2001_test

gen same=1 if coyno==coyno_2001_string

drop if same==1

drop same 


gen same=1 if coyno==coyno_2001_test

drop if same==1

drop same coyno_2001 coyno_2001_string


rename coyno_2001_test coyno_2001



// Save subset of observations where coyno doesn't match 2001 version and is not missing (143 in total)

preserve

drop if missing(coyno)

save coyno_diff_2001.dta, replace

restore


// Save subset of observations where 2001 provides additional company numbers (4,700 in total)

keep if missing(coyno)

keep charitynumber coyno_2001

save ccew_2001_coyno_public.dta, replace


// Merge additional company numbers from 2001 to the charity register data 

use ccew_spine_public, clear

merge m:1 charitynumber using ccew_2001_coyno_public, gen(coyno_merge)

replace coyno=coyno_2001 if coyno_merge==3

drop coyno_2001 coyno_merge

save ccew_spine_public, replace


// Rename/reorder variables and save

drop firstaddress-postcode

gen uid=.
order uid, before (charitynumber)
order name, before (coyno)

gen source="CCEW"

rename name organisationname
rename coyno companyid

// Clone name_origin variable as iteration, for use in later compiled data

clonevar iteration=name_origin

save ccew_spine_public.dta, replace



// Import snapshots (2001–2022) to find historical addresses (Note: This historical address syntax was added after the first spine iteration was complete)

// 2001

use "`datapath'\ccr2001_repaired.dta", clear

// Create variable to tag primary info

sort cc_num sub_num

bysort cc_num: gen rank=_n

gen primary=1 if rank==1

// Align postcode variables

replace pcode=pcd2 if pcode==" " & pcd2!=""

// Keep and rename relevant variables

keep cc_num address1 address2 address3 address4 address5 pcode rank primary

rename cc_num charitynumber
rename address1 add1
rename address2 add2
rename address3 add3 
rename address4 add4
rename address5 add5
rename pcode postcode

// Drop rows without useful address info

foreach var of varlist add1-postcode {
replace `var'="" if `var'=="."
replace `var'="" if `var'==","
replace `var'="" if `var'=="?"
replace `var'="" if `var'=="??"
replace `var'="" if `var'=="-"
replace `var'="" if `var'==" "
}

gen address_origin=0

save 2001_snapshot_address.dta, replace


// March 2022

import delimited "`datapath'\March22_snapshot.txt", varnames(1) bindquotes(nobind) delimiter("\t") clear

// Keep and rename relevant variables

keep registered_charity_number linked_charity_number charity_contact_address* charity_contact_postcode

rename registered_charity_number charitynumber
rename charity_contact_address1 add1
rename charity_contact_address2 add2
rename charity_contact_address3 add3 
rename charity_contact_address4 add4
rename charity_contact_address5 add5
rename charity_contact_postcode postcode
rename linked_charity_number subno

// Create variable to tag primary info

sort charitynumber subno

bysort charitynumber: gen rank=_n

gen primary=1 if rank==1

drop subno

gen address_origin=12

save March22_snapshot_address.dta, replace


// March 2023

use "`datapath'\CC_appended_March23.dta"

// Keep and rename relevant variables

keep registered_charity_number charity_contact_address* charity_contact_postcode

rename registered_charity_number charitynumber
rename charity_contact_address1 add1
rename charity_contact_address2 add2
rename charity_contact_address3 add3 
rename charity_contact_address4 add4
rename charity_contact_address5 add5
rename charity_contact_postcode postcode

// Create variable to tag 2023 data as primary

gen primary=1

gen address_origin=13

save March23_snapshot_address.dta, replace


// June 2011

import delimited "`datapath'\June11_snapshot.txt", varnames(1) bindquotes(strict) delimiter(",") maxquotedrows(200) clear


// Create variable to keep track of data iterations, fill in using loop below

gen address_origin=1


// March 2012-2019

// Append data from 2012–2019 and fill in iteration variable

local counter=2

forval year=12(1)19 {
append using "`datapath'\March`year'_snapshot.dta", force
replace address_origin=`counter' if address_origin==.
local counter = `counter' + 1
}

// Append data from 2020–2021 and fill in iteration variable

forval year=20(1)21 {
append using "`datapath'\April`year'_snapshot.dta", force
replace address_origin=`counter' if address_origin==.
local counter = `counter' + 1
}

// Keep relevant variables

keep regno subno add* postcode address_origin

rename regno charitynumber


// Create variable to tag primary info

sort charitynumber subno

egen panel = group(charitynumber address_origin)

drop if charitynumber==.

sort panel subno

bysort panel: gen rank=_n

gen primary=1 if rank==1

drop panel subno


// Append data from 2001, 2022, and 2023

append using 2001_snapshot_address.dta

append using March22_snapshot_address.dta

append using March23_snapshot_address.dta

sort charitynumber address_origin


// Label address origin variable

label define iteration_label 0 "2001" 1 "2011" 2 "2012" 3 "2013" 4 "2014" 5 "2015" 6 "2016" 7 "2017" 8 "2018" ///
9 "2019" 10 "2020" 11 "2021" 12 "2022" 13 "2023"
label values address_origin iteration_label 

tab address_origin


// Drop rows without useful address info

drop if missing(add1) & missing(add2) & missing(add3) & missing(add4) & missing(add5) & missing(postcode)

drop if charitynumber==1159114 & inlist(address_origin, 8, 13)

foreach var of varlist add1-postcode {
replace `var'="" if `var'=="."
}

drop if missing(add1) & missing(add2) & missing(add3) & missing(add4) & missing(add5) & missing(postcode)



// Create new variables and reformat to check for differences

// Remove leading spaces from string variables identified through 'codebook *, problems
	
	codebook *, problems

	foreach var of varlist add1-postcode {
		gen `var'_alt = `var'
	}

	foreach var of varlist *_alt {
		replace `var' = ltrim(`var')
	}

	foreach var of varlist *_alt {
		replace `var' = rtrim(`var')
	}

// Remove all spaces from postcode variables

replace postcode_alt=subinstr(postcode_alt," ","",.)


// Remove punctuations from postcode variables

replace postcode_alt=subinstr(postcode_alt,".","",.)

replace postcode_alt=subinstr(postcode_alt,",","",.)

replace postcode_alt=subinstr(postcode_alt,"?","",.)

replace postcode_alt=subinstr(postcode_alt,":","",.)


// Convert strings to lower case 

foreach var of varlist *_alt {
replace `var' = strlower(`var')
}

// Collapse consecutive internal blanks to one blank 

foreach var of varlist *_alt {
replace `var' = itrim(`var')
}

codebook *_alt, problems



// Figure out which charities have more than one unique address

/*
  Going to do this based on first address line + postcode. 
  Using any more than this creates too many permutations, especially
  when we consider the arbitrary way that formatting/ordering of 
  addresses may differ across data iterations.  
*/

// Create concatenated variable of first address line + postcode

gen concat = add1_alt + " " + postcode_alt

// Drop duplicates based on concatenated address field, keeping earliest appearance of a given address

sort charitynumber address_origin rank

duplicates drop charitynumber concat, force


// Amend primary variable so it tags only one name per charity

by charitynumber: egen primary_year = max(address_origin) if primary==1

gen primary_address = 1 if primary==1 & address_origin==primary_year

drop rank primary primary_year

distinct charitynumber


// Rename variables to append to CCEW spine data file

rename add1 addressline1
rename add2 addressline2
rename add3 addressline3
rename add4 addressline4
rename add5 addressline5

// Drop variables

drop *_alt concat

// Clone address_origin variable as iteration, for use in later compiled data

clonevar iteration=address_origin

save ccew_distinct_addresses_public.dta, replace



// Split data so charities with one unique address per iteration can be merged and the remainder appended

egen panel = group (charitynumber iteration)

bysort panel: gen count = _N


preserve

keep if count==1

drop count panel

save ccew_distinct_addresses_public_merge.dta, replace

restore


preserve

drop if count==1

drop count panel

save ccew_distinct_addresses_public_append.dta, replace

restore


// Merge addresses file to spine data file

use ccew_spine_public.dta, clear

merge m:1 charitynumber iteration using ccew_distinct_addresses_public_merge.dta


egen panel = group (charitynumber iteration) if _merge==3

bysort panel: gen count = _N

foreach var of varlist addressline1-primary_address {
by panel : gen `var'_first = `var'[_n == 1] if count>1 & count!=488708
replace `var'=`var'_first if count>1 & count!=488708
}

// Append remaining addresses 

append using ccew_distinct_addresses_public_append.dta


// Final tidy up of variables

drop _merge-primary_address_first

replace source="CCEW"

gen normalisedname=""

order normalisedname, after(organisationname)

gen housenumber=""

order housenumber, before(addressline1)

gen city=""
gen localauthority=""

order city localauthority, before(postcode)
order name_origin, before(address_origin)
order iteration, after(address_origin)
order source, after(iteration)
order primary_name, after(name_origin)
order primary_address, after(address_origin)

sort charitynumber iteration

save ccew_spine_public.dta, replace



// Add data for registration and removal dates (this syntax was added in August 2023)

clear all

// March 2023

use "`datapath'\CC_appended_March23.dta"

// Keep and rename relevant variables

keep registered_charity_number date_of_registration date_of_removal reg_date diss_date

rename registered_charity_number regno
rename date_of_registration regdate1
rename reg_date regdate2
rename date_of_removal remdate1
rename diss_date remdate2

// Drop duplicates

duplicates drop regno, force

// Drop duplicate values for dates and move distinct values to top row within charitynumber

replace regdate2=. if regdate1==regdate2

replace remdate2=. if remdate1==remdate2

replace remdate1=remdate2 if remdate1==.

replace remdate2=. if remdate1==remdate2

// Reshape data

reshape long regdate remdate, i(regno) j(count)

// Drop empty rows

drop if regdate==. & remdate==.


// Tidy up data and save

distinct regno

drop count

rename regdate regdate_datetime
rename remdate remdate_datetime

save regrem_March2023.dta, replace



// Use historical files to add registration and removal dates (Added in November 2023)

/* 
  Date formatting differs significantly across iterations. Import string versions first, 
  convert to new datetime variable and drop strings. Then append numeric variables and 
  replace datetime variable values using them.

  Formatting: 
  2011 - 08/06/1961 00:00:00 (str)
  2012 - 08jun1961 00:00:00 (double %tc)
  2013 - 8/6/1961 00:00:00 (str)
  2014 - 08jun1961 00:00:00 (double %tc)
  2015 - 08jun1961 00:00:00 (double %tc)
  2016 - 08jun1961 00:00:00 (double %tc)
  2017 - 1961-06-08 00:00:00 (str)
  2018 - 1961-06-08 00:00:00 (str)
  2019 - 1961-06-08 00:00:00 (str)
  2020 - 1961-06-08 00:00:00 (str)
  2021 - 1961-10-19 00:00:00.0000000 (str)
  2022 - 1962-05-17 00:00:00.0000000 (str)
*/

// March 2013

import delimited "`datapath'\RegRemdates\regrem_March2013.txt", varnames(1) bindquotes(strict) delimiter(",") maxquotedrows(200) clear

// Keep relevant variables

keep regno regdate remdate

save "`datapath'\RegRemdates\regrem_March2013.dta", replace


// March 2017

import delimited "`datapath'\RegRemdates\regrem_March2017.csv", varnames(1) bindquotes(strict) delimiter(",") clear

// Keep relevant variables

keep regno regdate remdate

save "`datapath'\RegRemdates\regrem_March2017.dta", replace


// March 2019

import delimited "`datapath'\RegRemdates\regrem_March2019.csv", varnames(1) bindquotes(strict) delimiter(",") clear

// Keep relevant variables

keep regno regdate remdate

save "`datapath'\RegRemdates\regrem_March2019.dta", replace


// April 2021

import delimited "`datapath'\RegRemdates\regrem_April2021.txt", varnames(1) bindquotes(nobind) delimiter("\t") clear

// Keep and rename relevant variables

keep registered_charity_number date_of_registration date_of_removal

rename registered_charity_number regno
rename date_of_registration regdate
rename date_of_removal remdate

save "`datapath'\RegRemdates\regrem_April2021.dta", replace


// March 2022

import delimited "`datapath'\RegRemdates\regrem_March2022.txt", varnames(1) bindquotes(nobind) delimiter("\t") clear

// Keep and rename relevant variables

keep registered_charity_number date_of_registration date_of_removal

rename registered_charity_number regno
rename date_of_registration regdate
rename date_of_removal remdate

save "`datapath'\RegRemdates\regrem_March2022.dta", replace


// June 2011

import delimited "`datapath'\RegRemdates\regrem_June2011.txt", varnames(1) bindquotes(strict) delimiter(",") maxquotedrows(200) clear


// Create variable to keep track of data iterations, fill in using loop below

gen iteration=1


// March 2013

append using "`datapath'\RegRemdates\regrem_March2013.dta", force
replace iteration=3 if iteration==.

// March 2017–2019

local counter=7

forval year=2017(1)2019 {
append using "`datapath'\RegRemdates\regrem_March`year'.dta", force
replace iteration=`counter' if iteration==.
local counter = `counter' + 1
}

// April 2020–2021

local counter=10

forval year=2020(1)2021 {
append using "`datapath'\RegRemdates\regrem_April`year'.dta", force
replace iteration=`counter' if iteration==.
local counter = `counter' + 1
}


// March 2022

append using "`datapath'\RegRemdates\regrem_March2022.dta", force
replace iteration=12 if iteration==.


// Reformat string variables before importing other iterations

foreach var in regdate remdate {
replace `var'=subinstr(`var', "00:00:00.0000000", "", .) if inlist(iteration, 11, 12)
replace `var'=subinstr(`var'," ","",.) if inlist(iteration, 11, 12)
}


foreach var in regdate remdate {
generate `var'_datetime = date(`var', "DMY hms") if inlist(iteration, 1, 3)
replace `var'_datetime = date(`var', "YMD hms") if inlist(iteration, 7, 8, 9, 10)
replace `var'_datetime = date(`var', "YMD") if inlist(iteration, 11, 12)
format `var'_datetime %td
}

drop regdate remdate


// March 2012

append using "`datapath'\RegRemdates\regrem_March2012.dta", force

replace iteration=2 if iteration==.

// March 2014–2016 

local counter=4

forval year=2014(1)2016 {
append using "`datapath'\RegRemdates\regrem_March`year'.dta", force
replace iteration=`counter' if iteration==.
local counter = `counter' + 1
}


// Reformat numeric variables

foreach var in regdate remdate {
replace `var'_datetime = dofc(`var') if inlist(iteration, 2, 4, 5, 6)
format `var'_datetime %td if inlist(iteration, 2, 4, 5, 6)
}

drop regdate remdate remcode subno


// March 2023

append using regrem_March2023.dta

replace iteration=13 if iteration==.


// Rename variables

rename regno charitynumber
rename regdate_datetime registerdate
rename remdate_datetime removeddate

// Keep relevant variables

keep charitynumber registerdate removeddate iteration


// 2001 data iteration 

append using "`datapath'\ccr2001_repaired.dta", force

replace iteration=0 if iteration==.

keep charitynumber registerdate removeddate iteration cc_num reg_date rem_date


// Reformat string variables

replace registerdate = date(reg_date , "MDY hm") if iteration==0
replace removeddate = date(rem_date , "MDY hm") if iteration==0

replace charitynumber=cc_num if iteration==0

drop cc_num reg_date rem_date


// Label iteration variable

label define iteration_label 0 "2001" 1 "2011" 2 "2012" 3 "2013" 4 "2014" 5 "2015" 6 "2016" 7 "2017" 8 "2018" ///
9 "2019" 10 "2020" 11 "2021" 12 "2022" 13 "2023"
label values iteration iteration_label 

tab iteration


// Drop duplicates

duplicates drop charitynumber registerdate removeddate iteration, force

sort charitynumber iteration


// Split data into registration and removal dates

preserve

drop removeddate

keep if registerdate!=.

sort charitynumber iteration

duplicates drop charitynumber registerdate, force

clonevar regdate_origin=iteration

save regdate_ccew_public.dta, replace

restore


preserve

drop registerdate

keep if removeddate!=.

duplicates drop charitynumber removeddate, force

clonevar remdate_origin=iteration

save remdate_ccew_public.dta, replace

restore


// Split data so charities with one unique date per iteration can be merged and the remainder appended

// Registration date

clear all

use regdate_ccew_public.dta

egen panel = group(charitynumber iteration)

bysort panel: gen count = _N


preserve

keep if count==1

drop panel count

save regdate_ccew_public_merge.dta, replace

restore


preserve

drop if count==1

drop panel count

save regdate_ccew_public_append.dta, replace

restore



// Removal date

clear all

use remdate_ccew_public.dta

egen panel = group(charitynumber iteration)

bysort panel: gen count = _N


preserve

keep if count==1

drop panel count

save remdate_ccew_public_merge.dta, replace

restore


preserve

drop if count==1

drop panel count

save remdate_ccew_public_append.dta, replace

restore




// Merge these files back into the spine

// Merge registration dates 

clear all 

use ccew_spine_public.dta

merge m:1 charitynumber iteration using regdate_ccew_public_merge.dta, gen(regdate_merge)

egen panel = group (charitynumber iteration) if regdate_merge==3

bysort panel: gen count = _N

gsort panel -postcode

foreach var of varlist registerdate-regdate_origin {
by panel : gen `var'_first = `var'[_n == 1] if count>1 & count!=546912
replace `var'=`var'_first if count>1 & count!=546912
}

// Append remaining registration dates

append using regdate_ccew_public_append.dta

// Drop variables

drop regdate_merge-regdate_origin_first


// Merge removal dates 

merge m:1 charitynumber iteration using remdate_ccew_public_merge.dta, gen(remdate_merge)

egen panel = group (charitynumber iteration) if remdate_merge==3

bysort panel: gen count = _N

gsort panel -postcode

foreach var of varlist removeddate-remdate_origin {
by panel : gen `var'_first = `var'[_n == 1] if count>1 & count!=856379
replace `var'=`var'_first if count>1 & count!=856379
}

// Append removal dates

append using remdate_ccew_public_append.dta

// Drop variables

drop remdate_merge-remdate_origin_first


// Fill in company numbers using charitynumber as grouping variable

bysort charitynumber (companyid): replace companyid = companyid[_N]


// Final tidy up and reordering of variables

order registerdate removeddate, after(postcode)
order regdate_origin remdate_origin, after(primary_address)

replace source="CCEW"

sort charitynumber iteration

export delimited ccew_spine_public.csv, replace



// Add binary variable to tag organisations also registered with Care Quality Commission (Added in March 2024)

clear all

use "`datapath'\CC_appended_March23.dta"

// Keep relevant variables

keep registered_charity_number reg_CQC

// Rename variables

rename registered_charity_number charitynumber

keep if reg_CQC==1

keep charitynumber

save cqc.dta, replace


// Import spine and add CQC variable

clear all

import delimited ccew_spine_public.csv

merge m:1 charitynumber using cqc.dta, gen(cqc_merge)

gen cqc_reg=1 if cqc_merge==3
replace cqc_reg=0 if cqc_reg==.

drop cqc_merge

export delimited ccew_spine_public.csv, replace



// Additional pre-processing to remove placeholder address info and re-assign primary addresses where possible (April 2024)

import delimited "C:\Users\ad92\University of Stirling\ADRUKResearchReadyData - August 2023\ccew_spine_public.csv"

// Clean up some info that was manually checked

replace postcode="ST17" if strpos(postcode, "STXX XXX")
replace postcode="B37" if strpos(postcode, "B37 XXX")
replace postcode="SP4 9HP" if charitynumber==269638 & address_origin==2001

// Reassign primary addresses after manual checking

replace primary_address=1 if charitynumber==1133325 & address_origin==2011
replace primary_address=. if charitynumber==1133325 & address_origin==2018

replace primary_address=1 if charitynumber==281610 & address_origin==2001
replace primary_address=. if charitynumber==281610 & address_origin==2015

replace primary_address=1 if charitynumber==298386 & address_origin==2001
replace primary_address=. if charitynumber==298386 & address_origin==2014


// Create dummy variable to tag rows where there are placeholder values

gen dummy=.

foreach var of varlist addressline1 addressline2 addressline3 addressline4 addressline5 postcode { 
replace dummy=1 if `var'=="XX"
replace dummy=1 if `var'=="xx"
replace dummy=1 if `var'=="XX XX"
replace dummy=1 if `var'=="xx xx"
replace dummy=1 if strpos(`var', "XXX")
replace dummy=1 if strpos(`var', "xxx")
replace dummy=1 if strpos(`var', "***")
replace dummy=1 if strpos(`var', "NO UNSOLICITED MAIL")
replace dummy=1 if strpos(`var', "UNKNOWN")
replace dummy=1 if strpos(`var', "Unknown")
replace dummy=1 if strpos(`var', "CHARITY NO LONGER OPERATES")
replace dummy=1 if strpos(`var', "CORRESPONDENT UNKNOWN")
replace dummy=1 if strpos(`var', "AT PRESENT")
replace dummy=1 if `var'=="?"
}

tab dummy 

// Remove placeholder values

foreach var of varlist addressline1 addressline2 addressline3 addressline4 addressline5 postcode { 
replace `var'="" if strpos(`var', "NO UNSOLICITED MAIL")
replace `var'="" if strpos(`var', "UNKNOWN") & !strpos(`var', "MARSH GIBBON")
replace `var'="" if strpos(`var', "Unknown")
replace `var'="" if strpos(`var', "CHARITY NO LONGER OPERATES")
replace `var'="" if strpos(`var', "CORRESPONDENT UNKNOWN")
replace `var'="" if strpos(`var', "AT PRESENT")
replace `var'="" if `var'=="XX"
replace `var'="" if `var'=="xx"
replace `var'="" if `var'=="XX XX"
replace `var'="" if `var'=="xx xx"
replace `var'="" if strpos(`var', "XXX")
replace `var'="" if strpos(`var', "xxx")
replace `var'="" if strpos(`var', "***")
replace `var'="" if `var'=="?"
}

// Manually change dummy coding for rows that do not require reassignment of primary address

replace dummy=. if dummy==1 & charitynumber==1102332
replace dummy=. if dummy==1 & charitynumber==1175837
replace dummy=. if dummy==1 & charitynumber==1106156
replace dummy=. if dummy==1 & charitynumber==1168183
replace dummy=. if dummy==1 & charitynumber==202148


// Clean up parsing errors related to '?' and '!' symbols 

gen test=.

foreach var of varlist addressline1 addressline2 addressline3 addressline4 addressline5 postcode  {
gen match_pattern = 1 if regexm(`var', "([0-9]+) \? ([0-9]+)")
replace `var' = subinstr(`var', " ? ", " - ", .) if match_pattern==1
replace test=1 if match_pattern==1
drop match_pattern
}

foreach var of varlist addressline1 addressline2 addressline3 addressline4 addressline5 postcode  {
gen match_pattern = 1 if regexm(`var', "([0-9]+)\?([0-9]+)")
replace `var' = subinstr(`var', "?", " - ", .) if match_pattern==1
replace test=1 if match_pattern==1
drop match_pattern
}

drop test

replace postcode="CB3 0RN" if strpos(postcode, "CB? 0RN")
replace postcode="NR13 6SF" if strpos(postcode, "NR!?6SF")
replace postcode="LU7 3HT" if strpos(postcode, "LU7 ?HT")
replace postcode="CF83 3ET" if strpos(postcode, "CF*? ?ET")
replace postcode="WS3 3LT" if strpos(postcode, "WS? 3LT")

replace addressline1="" if strpos(addressline1, "THIS IS NOT THE BIRMINGHAM CHARITY!")
replace addressline1="1st Ferring Sea Scout Hut" if strpos(addressline1, "!st Ferring Sea Scout Hut")
replace addressline1="FLAT 1" if strpos(addressline1, "FLAT !")
replace addressline3="LISKEARD" if strpos(addressline3, "LISKEARDPL!$")

foreach var of varlist addressline1-addressline5 {
replace `var' = subinstr(`var', "!0", "10", .) 
replace `var' = subinstr(`var', "!1", "11", .) 
replace `var' = subinstr(`var', "!2", "12", .) 
replace `var' = subinstr(`var', "!3", "13", .) 
replace `var' = subinstr(`var', "!4", "14", .) 
replace `var' = subinstr(`var', "!5", "15", .) 
replace `var' = subinstr(`var', "!6", "16", .) 
replace `var' = subinstr(`var', "!7", "17", .) 
replace `var' = subinstr(`var', "!8", "18", .) 
replace `var' = subinstr(`var', "!9", "19", .) 
}

replace postcode = subinstr(postcode, "!", "1", .) 

// Tidy up coding for address_origin and primary_address

replace address_origin=. if addressline1=="" & addressline2=="" & addressline3=="" & addressline4=="" & addressline5=="" & postcode==""
replace primary_address=. if addressline1=="" & addressline2=="" & addressline3=="" & addressline4=="" & addressline5=="" & postcode=="" 

drop if name_origin=="" & address_origin==. & regdate_origin==. & remdate_origin==. & dummy==1

export delimited ccew_spine_public.csv, replace



// More pre-processing to remove placeholder address info and re-assign primary addresses where possible (28 April 2024)

import delimited "C:\Users\ad92\University of Stirling\ADRUKResearchReadyData - August 2023\ccew_spine_public.csv"


// Reassign primary addresses after manual checking

replace primary_address=1 if charitynumber==1169311 & address_origin==2017
replace primary_address=. if charitynumber==1169311 & address_origin==2022

replace primary_address=1 if charitynumber==1098607 & address_origin==2015
replace primary_address=. if charitynumber==1098607 & address_origin==2021

replace primary_address=1 if charitynumber==1068298 & address_origin==2011
replace primary_address=. if charitynumber==1068298 & address_origin==2016

replace primary_address=1 if charitynumber==266120 & address_origin==2016
replace primary_address=. if charitynumber==266120 & address_origin==2023

/*
  4 above are re-assigned but original will be kept as it has a valid postcode. 
  Number of distinct addresses doesn't change.
*/

replace primary_address=1 if charitynumber==227626 & address_origin==2011
replace primary_address=. if charitynumber==227626 & address_origin==2023

replace primary_address=1 if charitynumber==523767 & address_origin==2011
replace primary_address=. if charitynumber==523767 & address_origin==2016

replace primary_address=1 if charitynumber==1006954 & address_origin==2011
replace primary_address=. if charitynumber==1006954 & address_origin==2023

replace primary_address=1 if charitynumber==1048478 & address_origin==2001
replace primary_address=. if charitynumber==1048478 & address_origin==2011

replace primary_address=1 if charitynumber==1089704 & address_origin==2014
replace primary_address=. if charitynumber==1089704 & address_origin==2015

replace primary_address=1 if charitynumber==1132191 & address_origin==2017
replace primary_address=. if charitynumber==1132191 & address_origin==2018

/*
  6 above are re-assigned because the primary address is missing after
  placeholder info is removed. Number of distinct addresses drops by 6. 
*/



gen dummy2=.

foreach var of varlist addressline1 addressline2 addressline3 addressline4 addressline5 postcode { 
replace dummy2=1 if `var'=="X"
replace dummy2=1 if `var'=="N"
replace dummy2=1 if `var'=="UN KNOWN"
replace dummy2=1 if `var'=="UNK"
replace dummy2=1 if `var'=="ERROR"
replace dummy2=1 if `var'=="TEST"
replace dummy2=1 if `var'=="NO NONE"
replace dummy2=1 if `var'=="NONE"
replace dummy2=1 if `var'=="ACCOUNT"
replace dummy2=1 if `var'=="NOT KNOW"
replace dummy2=1 if `var'=="NONE (INTERNATIONAL)"
replace dummy2=1 if `var'=="."

replace dummy2=1 if strpos(`var', "NOT AVAILABLE")
replace dummy2=1 if strpos(`var', "ACCOUNT CLOSED")
replace dummy2=1 if strpos(`var', "NOT KNOWN")
replace dummy2=1 if strpos(`var', "NONE (INTERNATIONAL)")
replace dummy2=1 if strpos(`var', "- NONE -")
replace dummy2=1 if strpos(`var', "NONE AVAILABLE")
replace dummy2=1 if strpos(`var', "--NONE--")
replace dummy2=1 if strpos(`var', ".....                              ")
replace dummy2=1 if strpos(`var', "nil                                ")
replace dummy2=1 if strpos(`var', "NIL     ")
replace dummy2=1 if strpos(`var', "Please select")
replace dummy2=1 if strpos(`var', "Please Select")
replace dummy2=1 if strpos(`var', "...")
replace dummy2=1 if `var'=="Type"
replace dummy2=1 if strpos(`var', "N/A")
replace dummy2=1 if strpos(`var', "nil                                ")
replace dummy2=1 if strpos(`var', "TBC") & charitynumber!=1124917
replace dummy2=1 if strpos(`var', "NIL     ")
replace dummy2=1 if strpos(`var', "---")
replace dummy2=1 if strpos(`var', "PLEASE")
replace dummy2=1 if strpos(`var', "UNAVAILABLE")
}

replace dummy2=1 if charitynumber==1159646 & address_origin==2016
replace dummy2=1 if charitynumber==266120 & address_origin==2023

tab dummy2


foreach var of varlist addressline1 addressline2 addressline3 addressline4 addressline5 postcode { 
replace `var'="" if charitynumber==1031170 & address_origin==2011
replace `var'="" if charitynumber==1159646 & address_origin==2016
}

foreach var of varlist addressline1 addressline2 addressline3 addressline4 addressline5 { 
replace `var'="" if charitynumber==1182830 & address_origin==2020
replace `var'="" if charitynumber==266120 & address_origin==2023
}

replace addressline2 = subinstr(addressline2, "(PLEASE USE EMAIL", "", .) if charitynumber==1031170 & address_origin==2014
replace addressline3 = subinstr(addressline3, "NOT POSTAL ADDRESS)", "", .) if charitynumber==1031170 & address_origin==2014
replace addressline5 = subinstr(addressline5, "(PLEASE USE EMAIL ADDRESS)", "", .) if charitynumber==1031170 & address_origin==2016
replace addressline1 = "" if charitynumber==1089704 & address_origin==2015
replace addressline2 = "" if charitynumber==1089704 & address_origin==2015

foreach var of varlist addressline1 addressline2 addressline3 addressline4 addressline5 postcode { 
replace `var'="" if strpos(`var', "PLEASE")
}

foreach var of varlist addressline1 addressline2 addressline3 addressline4 addressline5 postcode { 
replace `var'="" if strpos(`var', "AT THE CHARITY COMMISSIONE")
}

foreach var of varlist addressline1 addressline2 addressline3 addressline4 addressline5 postcode { 
replace `var'="" if strpos(`var', "UNAVAILABLE")
}

foreach var of varlist addressline1 addressline2 addressline3 addressline4 addressline5 postcode { 
replace `var'="" if strpos(`var', "NO APPLICATIONS TO THIS ADDRESS")
}

foreach var of varlist addressline1 addressline2 addressline3 addressline4 addressline5 postcode { 
replace `var'="" if strpos(`var', "LIVERPOOL OFFICE")
}

foreach var of varlist addressline1 addressline2 addressline3 addressline4 addressline5 postcode { 
replace `var'="" if `var'=="X"
replace `var'="" if `var'=="N"
replace `var'="" if `var'=="UN KNOWN"
replace `var'="" if `var'=="UNK"
replace `var'="" if `var'=="ERROR"
replace `var'="" if `var'=="TEST"
replace `var'="" if `var'=="NO NONE"
replace `var'="" if `var'=="NONE"
replace `var'="" if `var'=="ACCOUNT"
replace `var'="" if `var'=="NOT KNOW"
replace `var'="" if `var'=="NONE (INTERNATIONAL)"
replace `var'="" if `var'=="."

replace `var'="" if strpos(`var', "NOT AVAILABLE")
replace `var'="" if strpos(`var', "ACCOUNT CLOSED")
replace `var'="" if strpos(`var', "NOT KNOWN")
replace `var'="" if strpos(`var', "NONE (INTERNATIONAL)")
replace `var'="" if strpos(`var', "- NONE -")
replace `var'="" if strpos(`var', "NONE AVAILABLE")
replace `var'="" if strpos(`var', "--NONE--")
replace `var'="" if strpos(`var', ".....                              ")
replace `var'="" if strpos(`var', "nil                                ")
replace `var'="" if strpos(`var', "NIL     ")
replace `var'="" if strpos(`var', "Please select")
replace `var'="" if strpos(`var', "Please Select")
replace `var'="" if strpos(`var', "...")
replace `var'="" if `var'=="Type"
replace `var'="" if strpos(`var', "N/A")
replace `var'="" if strpos(`var', "nil                                ")
replace `var'="" if strpos(`var', "TBC") & charitynumber!=1124917
replace `var'="" if strpos(`var', "NIL     ")
replace `var'="" if strpos(`var', "---")
replace `var'="" if strpos(`var', "PLEASE")
replace `var'="" if strpos(`var', "UNAVAILABLE")
}

// Change dummy coding for rows that do not require reassignment of primary address

gen dummy3=1 if addressline1=="" & addressline2=="" & addressline3=="" & addressline4=="" & addressline5=="" & postcode=="" & dummy2==1

replace dummy2=. if dummy2==1 & dummy3==.

drop dummy3


// Tidy up coding for address_origin and primary_address

replace address_origin=. if addressline1=="" & addressline2=="" & addressline3=="" & addressline4=="" & addressline5=="" & postcode=="" // 79
replace primary_address=. if addressline1=="" & addressline2=="" & addressline3=="" & addressline4=="" & addressline5=="" & postcode=="" // 64

drop if name_origin=="" & address_origin==. & regdate_origin==. & remdate_origin==. & dummy2==1 // 11

distinct charitynumber // 341,990

tab primary_address // 328,683 (13,307 with no address info)

tab address_origin // 668,625 (339,942 supplementary addresses)

export delimited ccew_spine_public.csv, replace


// More pre-processing to remove placeholder address info and re-assign primary addresses where possible (16 May 2024)

import delimited "C:\Users\ad92\University of Stirling\ADRUKResearchReadyData - August 2023\ccew_spine_public.csv"

// Remove incorrect and placeholder info

replace addressline1 = subinstr(addressline1, "WV5 7ET", "", .) if charitynumber==232734 & primary_address==1


replace addressline1 = addressline2 if charitynumber==313660 & primary_address==1
replace addressline2 = addressline3 if charitynumber==313660 & primary_address==1
replace addressline3 = addressline4 if charitynumber==313660 & primary_address==1
replace addressline4 = "" if charitynumber==313660 & primary_address==1
replace addressline5 = "" if charitynumber==313660 & primary_address==1


replace postcode="CF62 9TE" if charitynumber==519465 & primary_address==1


foreach var of varlist addressline1-addressline5 postcode {
replace `var'="" if charitynumber==1036371 & address_origin==2014
}

replace primary_address=. if charitynumber==1036371 & address_origin==2014
replace primary_address=1 if charitynumber==1036371 & address_origin==2012


foreach var of varlist addressline1-addressline5 postcode {
replace `var'="" if charitynumber==1069264 & address_origin==2011
}

replace primary_address=. if charitynumber==1069264 & address_origin==2011
replace primary_address=1 if charitynumber==1069264 & address_origin==2001


foreach var of varlist addressline1-addressline5 postcode {
replace `var'="" if charitynumber==1105304 & address_origin==2012
}

replace primary_address=. if charitynumber==1105304 & address_origin==2012
replace primary_address=1 if charitynumber==1105304 & address_origin==2011


replace addressline1 = addressline2 if charitynumber==1163446 & primary_address==1
replace addressline2 = addressline3 if charitynumber==1163446 & primary_address==1
replace addressline3 = addressline4 if charitynumber==1163446 & primary_address==1
replace addressline4 = "" if charitynumber==1163446 & primary_address==1
replace addressline5 = "" if charitynumber==1163446 & primary_address==1


replace addressline1 = addressline2 if charitynumber==1191619 & primary_address==1
replace addressline2 = addressline3 if charitynumber==1191619 & primary_address==1
replace addressline3 = "" if charitynumber==1191619 & primary_address==1


// Tidy up coding for address_origin and primary_address

replace address_origin=. if addressline1=="" & addressline2=="" & addressline3=="" & addressline4=="" & addressline5=="" & postcode=="" // 3

drop if name_origin=="" & address_origin==. & regdate_origin==. & remdate_origin==. // 2

distinct charitynumber // 341,990

tab primary_address // 328,683 (13,307 with no address info)

tab address_origin // 668,622 (339,939 supplementary addresses)

export delimited ccew_spine_public.csv, replace






