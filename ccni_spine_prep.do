// File: ccni_spine_prep.do
// Creator: Alan Duggan
// Created: 19/04/2023
// Updated: 28/08/2023

******* Overview *******


/* 
	This DO file outlines the steps taken to transform Northern Irish charity data (charity register and removed 
        charities) into a spine dataset of organisations for linkage with the Business Structure Database. 
	
	This do file performs the following tasks:
		- imports raw dataset from April 2023
		- cleans raw dataset
		- constructs dataset for linakge
		
	The data files used in this script:
		- ccni-charity-register-2023-04-19.xlsx [Scottish Charity Register - 19 April 2023 (Open data)] 
		
		
*/


/* Define path */

local datapath C:\Users\ad92\OneDrive\UKRI Fellowship\ADRUK\Spine data\Data files


// Import data and keep relevant variables

import excel using "`datapath'\ccni-charity-register-2023-04-19.xlsx", firstrow clear

keep Regcharitynumber Charityname Publicaddress Companynumber Dateregistered


// Create address_alt variable and tidy up formatting

gen Publicaddress_alt = subinstr(Publicaddress, ", ,", ",", .)
replace Publicaddress_alt  = subinstr(Publicaddress_alt , ",,", ",", .)
replace Publicaddress_alt  = subinstr(Publicaddress_alt , ",  ,", ",", .)

*split Publicaddress , p(,) // NOT RUN

rename Regcharitynumber charitynumber
rename Charityname organisationname
rename Companynumber companyid
rename Publicaddress address
rename Publicaddress_alt address_alt
rename Dateregistered registerdate


// Inspect data using 'codebook *, problems'
	
	codebook *, problems



// Extract postcode

gen position = strrpos(address_alt, ", ")

gen postcode = substr(address_alt, position+1, position+15)

drop position


// Tidy up some postcode values that aren't postcodes (All NI postcodes begin with 'BT')

gen tag=1 if !strpos(postcode, "BT")

replace tag=. if strpos(postcode, "bt")

replace tag=. if strpos(postcode, "Bt")

list postcode if tag==1

gen no_numeric = !regexm(postcode, "[0-9]") & tag==1

list postcode if no_numeric==1

replace postcode="" if no_numeric==1

drop tag no_numeric address_alt


// Reformat registered date variable 

format registerdate %td


// Extract house number (NOT RUN)

/*

*gen position = strpos(firstaddress, " ")

*gen housenumber = substr(firstaddress, 1, position)

moss firstaddress, match("([0-9^\]+)") regex

rename _match1 housenumber

order housenumber, before(firstaddress)

drop _count* _match* _pos*

*/


// Re-order variables and save

gen uid=.
order uid, before (charitynumber)
order companyid, after (organisationname)

gen source="CCNI"

gen normalisedname=""

order normalisedname, after(organisationname)

gen housenumber=""

order housenumber, before(address)

gen city=""
gen localauthority=""

order city localauthority, before(postcode)

order registerdate, before(source)

export delimited ccni_spine.csv, replace
