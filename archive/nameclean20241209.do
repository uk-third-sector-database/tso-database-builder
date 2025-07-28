*Stata 'name-normaliser' / 'cleanname' do-file, evolved over
*several years by elements of TSRC.

*This update 9 Dec 2024, in light of experience in Procurement Data project.

*No significant changes in purpose or output format
*minor tidying/improvement of coding of two loops (improving runtime)
*and additional adjustments of common typoes, incl 'grammer' and 'consruction'.

*If adampting all or part to other applications / software packages, note:
*	1. presence or absence of leading/trailing in substitutions is critical to correct operation
*	2. sequencing is also critical in large part.


* the 'supplier' variable name in the first command line should be substituted with that of
* the string variable whose contents are required to be 'cleaned' / 'normalised'. The source
* variable is not changed.

capture gen cleanname=upper(organisationname)

replace cleanname = subinstr(cleanname, "ST.", "ST ", .)
replace cleanname = subinstr(cleanname, "ASSOC.", "ASSOC ", .)
replace cleanname = subinstr(cleanname, "..", " ", .)
replace cleanname = subinstr(cleanname, ".", "", .)
replace cleanname = subinstr(cleanname, "(", " ", .)
replace cleanname = subinstr(cleanname, ")", " ", .)
replace cleanname = subinstr(cleanname, ",", " ", .)
replace cleanname = subinstr(cleanname, ";", " ", .)
replace cleanname = subinstr(cleanname, ":", " ", .)
replace cleanname = subinstr(cleanname, "-", " ", .)
replace cleanname = subinstr(cleanname, "/", " ", .)

replace cleanname = subinstr(cleanname, "@", " ", .)
replace cleanname = subinstr(cleanname, "+", " ", .)

replace cleanname = subinstr(cleanname, "*", " ", .)
replace cleanname = subinstr(cleanname, "[", " ", .)
replace cleanname = subinstr(cleanname, "]", " ", .)
replace cleanname = subinstr(cleanname, "!", " ", .)
replace cleanname = subinstr(cleanname, "|", " ", .)
replace cleanname = subinstr(cleanname, "`", " ", .)
replace cleanname = subinstr(cleanname, "=", " ", .)
replace cleanname = subinstr(cleanname, "\", " ", .)
replace cleanname = subinstr(cleanname, "_", " ", .)
replace cleanname = subinstr(cleanname, "{", " ", .)
replace cleanname = subinstr(cleanname, "}", " ", .)
replace cleanname = subinstr(cleanname, "%", " ", .)
replace cleanname = subinstr(cleanname, "�", " ", .)
replace cleanname = subinstr(cleanname, "�", " ", .)
replace cleanname = subinstr(cleanname, "&", " ", .)
replace cleanname = subinstr(cleanname, "#", " ", .)

replace cleanname = subinstr(cleanname, "�", "A", .)
replace cleanname = subinstr(cleanname, "�", "E", .)
replace cleanname = subinstr(cleanname, "�", "E", .)

replace cleanname=" "+trim(cleanname)+" "

replace cleanname = subinstr(cleanname," 'S ","S ",.)
replace cleanname = subinstr(cleanname, "'S ","S ",.)

replace cleanname=subinstr( cleanname, "' "," ",.)
replace cleanname=subinstr( cleanname, " '"," ",.)
replace cleanname=subinstr( cleanname, "S'","S ",.)
replace cleanname=subinstr( cleanname, "'N'"," N ",.)
replace cleanname=subinstr( cleanname, "'","",.)

*Reduce multiple spaces to singles
replace cleanname=itrim(cleanname)

*correct various misspellings and typoes
replace cleanname = subinstr(cleanname, "FREIND","FRIEND",.)
replace cleanname = subinstr(cleanname, " ASSOCATION", " ASSOCIATION", .)
replace cleanname = subinstr(cleanname, " ASSOCIATON", " ASSOCIATION", .)
replace cleanname = subinstr(cleanname, " ASOCIATION", " ASSOCIATION", .)
replace cleanname = subinstr(cleanname, " ASSOCAITION", " ASSOCIATION", .)
replace cleanname = subinstr(cleanname, " ASSOCIAION "," ASSOCIATION ",.)
replace cleanname = subinstr(cleanname, " ASSOCAITION", " ASSOCIATION", .)
replace cleanname = subinstr(cleanname, " ASSOCIATOPM", " ASSOCIATION", .)
replace cleanname = subinstr(cleanname, " ASS ", " ASSOCIATION ", .)
replace cleanname = subinstr(cleanname, " ASSOCN ", " ASSOCIATION ", .)
replace cleanname = subinstr(cleanname, " ASSOCIATIONSACDA ", " ASSOCIATION SACDA ", .)
replace cleanname = subinstr(cleanname," CENTER"," CENTRE",.)
replace cleanname = subinstr(cleanname,"GIUDE","GUIDE",.)
replace cleanname = subinstr(cleanname," CONGEGATION "," CONGREGATION ",.)
replace cleanname = subinstr(cleanname," ORGANIZAT"," ORGANISAT",.)
replace cleanname = subinstr(cleanname," DISTICT "," DISTRICT ",.)
replace cleanname = subinstr(cleanname," DISRICT "," DISTRICT ",.)
replace cleanname = subinstr(cleanname," DISABILLI"," DISABILI",.)
replace cleanname = subinstr(cleanname," AMATUER "," AMATEUR ",.)
replace cleanname = subinstr(cleanname," BUSISNESS "," BUSINESS ",.)
replace cleanname = subinstr(cleanname," VICARIGE "," VICARAGE ",.)
replace cleanname = subinstr(cleanname," REHABILITAION "," REHABILITATION ",.)
replace cleanname = subinstr(cleanname," PANAL"," PANEL",.)
replace cleanname = subinstr(cleanname," BRITAN "," BRITAIN ",.)
replace cleanname = subinstr(cleanname," BRITANIA "," BRITANNIA ",.)
replace cleanname = subinstr(cleanname," CUMBRA "," CUMBRIA ",.)
replace cleanname = subinstr(cleanname," NEIGHBOR"," NEIGHBOUR",.)
replace cleanname = subinstr(cleanname," CNCL "," COUNCIL ",.)
replace cleanname = subinstr(cleanname," BORO "," BOROUGH ",.)
replace cleanname = subinstr(cleanname," COUNCILOR "," COUNCILLOR ",.)
replace cleanname = subinstr(cleanname," MATHEW"," MATTHEW",.)
replace cleanname = subinstr(cleanname," VILLIAGE"," VILLAGE",.)
replace cleanname = subinstr(cleanname," HERATAGE "," HERITAGE ",.)
replace cleanname = subinstr(cleanname," SHEILD"," SHIELD",.)
replace cleanname = subinstr(cleanname," COMUNITY "," COMMUNITY ",.)
replace cleanname = subinstr(cleanname," COMUNITIES "," COMMUNITIES ",.)
replace cleanname = subinstr(cleanname," COMMMUNITY "," COMMUNITY ",.)
replace cleanname = subinstr(cleanname," COMITTEE"," COMMITTEE",.)
replace cleanname = subinstr(cleanname," COMMITEE"," COMMITTEE",.)
replace cleanname = subinstr(cleanname," INDEPENDANT "," INDEPENDENT ",.)
replace cleanname = subinstr(cleanname," ENDOWNMENT "," ENDOWMENT ",.)
replace cleanname = subinstr(cleanname," GRAMMER "," GRAMMAR ",.)
replace cleanname = subinstr(cleanname," CONSRUCT"," CONSTRUCT",.)
replace cleanname = subinstr(cleanname," SYNDROMAE "," SYNDROME ",.)
replace cleanname = subinstr(cleanname," WILDLIFW "," WILDLIFE ",.)
replace cleanname = subinstr(cleanname," CENRE "," CENTRE ",.)
replace cleanname = subinstr(cleanname," COMMUNITYYOUTH "," COMMUNITY YOUTH ",.)
replace cleanname = subinstr(cleanname," AUTISMWEST "," AUTISM WEST ",.)
replace cleanname = subinstr(cleanname," OFGOD "," OF GOD ",.)
replace cleanname = subinstr(cleanname," INFORMARION "," INFORMATION ",.)
replace cleanname = subinstr(cleanname," DEVELOPEMENT "," DEVELOPMENT ",.)
replace cleanname = subinstr(cleanname," CHRITIAN "," CHRISTIAN ",.)
replace cleanname = subinstr(cleanname," ROYALM "," ROYAL ",.)
replace cleanname = subinstr(cleanname," LARYNGECOMY "," LARYNGECTOMY ",.)
replace cleanname = subinstr(cleanname," ALCHOL "," ALCOHOL ",.)
replace cleanname = subinstr(cleanname," RESARCH "," RESEARCH ",.)
replace cleanname = subinstr(cleanname," REASEARCH "," RESEARCH ",.)
replace cleanname = subinstr(cleanname," BEATY "," BEAUTY ",.)
replace cleanname = subinstr(cleanname," CENTR "," CENTRE ",.)


*standardise certain abbreviations, ensuring all spaces are singled-up first:
replace cleanname=itrim(cleanname)

replace cleanname = subinstr(cleanname," PUBLIC LIMITED COMPANY "," PLC ",.)

replace cleanname = subinstr(cleanname, " LIMITED ", " LTD ", .)
replace cleanname=subinstr(cleanname, " LIMITE ", " LTD ",.) if substr(rtrim(cleanname),-7,7)==" LIMITE"
replace cleanname=subinstr(cleanname, " LIMIT ", " LTD ",.) if substr(rtrim(cleanname),-6,6)==" LIMIT"
replace cleanname=subinstr(cleanname, " LIMI ", " LTD ",.) if substr(rtrim(cleanname),-5,5)==" LIMI"
replace cleanname=subinstr(cleanname, " LIM ", " LTD ",.) if substr(rtrim(cleanname),-4,4)==" LIM"

replace cleanname = subinstr(cleanname, " C I C ", " CIC ", .)
replace cleanname = subinstr(cleanname, "COMMUNITY INTEREST COMPANY", " CIC ", .)
replace cleanname = subinstr(cleanname, "COMMUNITY INTEREST COMPAN ", " CIC ", .)
replace cleanname = subinstr(cleanname, "COMMUNITY INTEREST COMPA ", " CIC ", .)
replace cleanname = subinstr(cleanname, "COMMUNITY INTEREST COMP ", " CIC ", .)
replace cleanname = subinstr(cleanname, "COMMUNITY INTEREST COM ", " CIC ", .)
replace cleanname = subinstr(cleanname, "COMMUNITY INTEREST CO ", " CIC ", .)

replace cleanname = subinstr(cleanname, " COUNCIL FOR VOLUNTARY SERVICES ", " CVS ", .)
replace cleanname = subinstr(cleanname, " COUNCIL FOR VOLUNTARY SERVICE ", " CVS ", .)

replace cleanname = subinstr(cleanname, " UNITED REFORMED CHURCH ", " URC ", .)
replace cleanname = subinstr(cleanname, " URC CHURCH ", " URC ", .)
replace cleanname = subinstr(cleanname, " UR CHURCH ", " URC ", .)

replace cleanname = subinstr(cleanname, " ALSO KNOWN AS ", " AKA ", .)

replace cleanname = subinstr(cleanname, " ROYAL ANTEDILUVIAN ORDER OF BUFFALOES ", " RAOB ", .)
replace cleanname = subinstr(cleanname, " ROYAL ANTIDILUVIAN ORDER OF BUFALLOES ", " RAOB ", .)
replace cleanname = subinstr(cleanname, " ROYAL ANTEDILUVIAN ORDER OF BUFFALOS ", " RAOB ", .)

replace cleanname = subinstr(cleanname, " CO OP ", " COOPERATIVE ", .)
replace cleanname = subinstr(cleanname, " CO OPS ", " COOPERATIVE ", .)
replace cleanname = subinstr(cleanname, " CO OPERATIVE ", " COOPERATIVE ", .)
replace cleanname = subinstr(cleanname, " CO OPERATIVES ", " COOPERATIVE ", .)
replace cleanname = subinstr(cleanname, " COOP ", " COOPERATIVE ", .)
replace cleanname = subinstr(cleanname, " COOPS ", " COOPERATIVE ", .)
replace cleanname = subinstr(cleanname, " COOPERATIVES ", " COOPERATIVE ", .)

replace cleanname = subinstr(cleanname, " DEPARTMENT ", " DEPT ", .)
replace cleanname = subinstr(cleanname, " DEPARTMENTS ", " DEPT ", .)
replace cleanname = subinstr(cleanname, " DEPTS ", " DEPT ", .)

replace cleanname = subinstr(cleanname, " PROG ", " PROGRAMME ", .)
replace cleanname = subinstr(cleanname, " PROGRAM ", " PROGRAMME ", .)

replace cleanname = subinstr(cleanname, " SCH "," SCHOOL ",.)
replace cleanname = subinstr(cleanname, " SCHS "," SCHOOLS ",.)

replace cleanname = subinstr(cleanname, " ASSOCIATION ", " ASSOC ", .)
replace cleanname = subinstr(cleanname, " ASSN ", " ASSOC ", .)

replace cleanname = subinstr(cleanname," COMM "," COMMUNITY ",.)

replace cleanname = subinstr(cleanname," SOCIETY "," SOC ",.)
replace cleanname = subinstr(cleanname," SOCY "," SOC ",.)

replace cleanname = subinstr(cleanname," VILL "," VILLAGE ",.)

replace cleanname = subinstr(cleanname," SHEFF "," SHEFFIELD ",.)
replace cleanname = subinstr(cleanname," SERV "," SERVICE ",.)

replace cleanname = subinstr(cleanname," RD "," ROAD ",.)

replace cleanname = subinstr(cleanname," GT "," GREAT ",.)

replace cleanname = subinstr(cleanname," REGT "," REGIMENT ",.)

replace cleanname = subinstr(cleanname," INFO "," INFORMATION ",.)

replace cleanname = subinstr(cleanname," AVE "," AVENUE ",.)
replace cleanname = subinstr(cleanname," CRES "," CRESCENT ",.)
replace cleanname = subinstr(cleanname," GDNS "," GARDENS ",.)
replace cleanname = subinstr(cleanname," SQ "," SQUARE ",.)
replace cleanname = subinstr(cleanname," TCE "," TERRACE ",.)

replace cleanname = subinstr(cleanname," THEATRE CO "," THEATRE COMPANY ",.)
replace cleanname = subinstr(cleanname," AND CO "," AND COMPANY ",.)
replace cleanname = subinstr(cleanname," CO LTD "," COMPANY LTD ",.)
replace cleanname=subinstr(subinstr(cleanname+"#"," CO #"," COMPANY #",.),"#","",.) if substr(cleanname,-4,4)==" CO "
*this last turns CO into COMPANY at the end of cleanname.

*remove conjunctions
replace cleanname = subinstr(cleanname, " THE ", " ", .)
replace cleanname = subinstr(cleanname, " AND ", " ", .)
replace cleanname = subinstr(cleanname, " OF ",  " ", .)
replace cleanname = subinstr(cleanname, " FOR ", " ", .)
replace cleanname = subinstr(cleanname, " WITH "," ", .)
replace cleanname = subinstr(cleanname, " AT ",  " ", .)
replace cleanname = subinstr(cleanname, " TO ",  " ", .)
replace cleanname = subinstr(cleanname, " IN ",  " ", .)
replace cleanname = subinstr(cleanname, " ON ",  " ", .)
replace cleanname = subinstr(cleanname, " AN ",  " ", .)
*can't drop " A " yet, since it might be part of a spaced-out abbreviation (eg, " R A O B ")

*Reduce multiple spaces to singles
replace cleanname=itrim(cleanname)

*the next bit compresses abbreviations(initialisms, acronyms)
*and does it more quickly than it used to.
replace cleanname=trim(cleanname)

capture gen clen=strlen(cleanname)
replace clen=strlen(cleanname)

capture gen cn=" "+cleanname+" "
replace cn=" "+cleanname+" "

set more off

tempvar ml cnx
gen `cnx'=cn
egen `ml'=max(strlen(cn))
forvalues spos=3/`=`ml'-2' {
   replace `cnx'=substr(`cnx',1,`spos'-1)+"@"+substr(`cnx',`spos'+1,.) if (substr(`cnx',`spos'-2,1)==" " | substr(`cnx',`spos'-2,1)=="@") & substr(`cnx',`spos'-1,1)!=" " & substr(`cnx',`spos',1)==" " & substr(`cnx',`spos'+1,1)!=" " & substr(`cnx',`spos'+2,1)==" "
}

set more on

replace cn=subinstr(`cnx',"@","",.)

replace cleanname = trim(cn) if cleanname != trim(cn)
*this last is just to shew a count on screen indicating how many changes the preceding code made.


*and now the rest of the standardising substitutions, knowing that abbr format's no longer a problem

replace cleanname = " "+cleanname+" "

replace cleanname = subinstr(cleanname," PTFA "," PTA ",.)
replace cleanname = subinstr(cleanname," PSA "," PTA ",.)

replace cleanname = cleanname+" PTA " if (regexm(cleanname, " PARENT") & regexm(cleanname, " TEACHER") & regexm(cleanname, "ASSOC "))

replace cleanname = cleanname+" PTA " if (regexm(cleanname, " PARENT") & regexm(cleanname, " STAFF") & regexm(cleanname, "ASSOC "))

replace cleanname = subinstr(cleanname," PARENTS "," ",.) if regexm(cleanname, " PTA ")
replace cleanname = subinstr(cleanname," PARENT "," ",.) if regexm(cleanname, " PTA ")
replace cleanname = subinstr(cleanname," TEACHERS "," ",.) if regexm(cleanname, " PTA ")
replace cleanname = subinstr(cleanname," TEACHER "," ",.) if regexm(cleanname, " PTA ")
replace cleanname = subinstr(cleanname," FRIENDS "," ",.) if regexm(cleanname, " PTA ")
replace cleanname = subinstr(cleanname," FRIEND "," ",.) if regexm(cleanname, " PTA ")
replace cleanname = subinstr(cleanname," STAFF "," ",.) if regexm(cleanname, " PTA ")
replace cleanname = subinstr(cleanname," ASSOC "," ",.) if regexm(cleanname, " PTA ")

replace cleanname = subinstr(cleanname," CA "," COMMUNITY ASSOC ",.)

*reduce all multi-spaces to singles yet again
replace cleanname=itrim(cleanname)

replace cleanname = subinstr(cleanname," SCOUT GROUP "," SCOUTS ",.)

replace cleanname = subinstr(cleanname," SCOUT ASSOC "," SCOUTS ",.)
replace cleanname = subinstr(cleanname," SCOUTS ASSOC "," SCOUTS ",.)

replace cleanname = subinstr(cleanname," SCOUT UNIT "," SCOUTS ",.)
replace cleanname = subinstr(cleanname," SCOUT UNITS "," SCOUTS ",.)
replace cleanname = subinstr(cleanname," SCOUTS UNIT "," SCOUTS ",.)
replace cleanname = subinstr(cleanname," SCOUTS UNITS "," SCOUTS ",.)

replace cleanname = subinstr(cleanname," SCOUT GROUP "," SCOUTS ",.)
replace cleanname = subinstr(cleanname," SCOUT GROUPS "," SCOUTS ",.)
replace cleanname = subinstr(cleanname," SCOUTS GROUP "," SCOUTS ",.)
replace cleanname = subinstr(cleanname," SCOUTS GROUPS "," SCOUTS ",.)

replace cleanname = subinstr(cleanname," SCOUT PACK "," SCOUTS ",.)
replace cleanname = subinstr(cleanname," SCOUT PACKS "," SCOUTS ",.)
replace cleanname = subinstr(cleanname," SCOUTS PACK "," SCOUTS ",.)
replace cleanname = subinstr(cleanname," SCOUTS PACKS "," SCOUTS ",.)

replace cleanname = subinstr(cleanname," BOY SCOUTS "," SCOUTS ",.)

replace cleanname = subinstr(cleanname," GIRL GUIDE "," GIRL GUIDES ",.)
replace cleanname = subinstr(cleanname," GIRL GUIDING "," GIRL GUIDES ",.)
replace cleanname = subinstr(cleanname," GIRLGUIDING "," GIRL GUIDES ",.)
replace cleanname = subinstr(cleanname," GIRL GUIDES "," GUIDES ",.)
replace cleanname = subinstr(cleanname," GUIDE ASSOC "," GUIDES ",.)
replace cleanname = subinstr(cleanname," GUIDES ASSOC "," GUIDES ",.)

replace cleanname = subinstr(cleanname," GUIDE UNIT "," GUIDES ",.)
replace cleanname = subinstr(cleanname," GUIDE UNITS "," GUIDES ",.)
replace cleanname = subinstr(cleanname," GUIDES UNIT "," GUIDES ",.)
replace cleanname = subinstr(cleanname," GUIDES UNITS "," GUIDES ",.)

replace cleanname = subinstr(cleanname," GUIDE GROUP "," GUIDES ",.)
replace cleanname = subinstr(cleanname," GUIDE GROUPS "," GUIDES ",.)
replace cleanname = subinstr(cleanname," GUIDES GROUP "," GUIDES ",.)
replace cleanname = subinstr(cleanname," GUIDES GROUPS "," GUIDES ",.)

replace cleanname = subinstr(cleanname," GUIDE PACK "," GUIDES ",.)
replace cleanname = subinstr(cleanname," GUIDE PACKS "," GUIDES ",.)
replace cleanname = subinstr(cleanname," GUIDES PACK "," GUIDES ",.)
replace cleanname = subinstr(cleanname," GUIDES PACKS "," GUIDES ",.)

replace cleanname = subinstr(cleanname," BROWNIE ASSOC "," BROWNIES ",.)
replace cleanname = subinstr(cleanname," BROWNIES ASSOC "," BROWNIES ",.)

replace cleanname = subinstr(cleanname," BROWNIE UNIT "," BROWNIES ",.)
replace cleanname = subinstr(cleanname," BROWNIE UNITS "," BROWNIES ",.)
replace cleanname = subinstr(cleanname," BROWNIES UNIT "," BROWNIES ",.)
replace cleanname = subinstr(cleanname," BROWNIES UNITS "," BROWNIES ",.)

replace cleanname = subinstr(cleanname," BROWNIE GROUP "," BROWNIES ",.)
replace cleanname = subinstr(cleanname," BROWNIE GROUPS "," BROWNIES ",.)
replace cleanname = subinstr(cleanname," BROWNIES GROUP "," BROWNIES ",.)
replace cleanname = subinstr(cleanname," BROWNIES GROUPS "," BROWNIES ",.)

replace cleanname = subinstr(cleanname," BROWNIE PACK "," BROWNIES ",.)
replace cleanname = subinstr(cleanname," BROWNIE PACKS "," BROWNIES ",.)
replace cleanname = subinstr(cleanname," BROWNIES PACK "," BROWNIES ",.)
replace cleanname = subinstr(cleanname," BROWNIES PACKS "," BROWNIES ",.)

replace cleanname = subinstr(cleanname," BROWNIE "," BROWNIES ",.) if regexm(cleanname,"GUIDE")
replace cleanname = subinstr(cleanname," SCOUT "," SCOUTS ",.) if regexm(cleanname,"GUIDE")

replace cleanname = subinstr(cleanname," CUB "," CUBS ",.) if regexm(cleanname,"SCOUT")
replace cleanname = subinstr(cleanname," CUBS "," CUBS SCOUTS ",.) if !regexm(cleanname,"SCOUT")
replace cleanname = subinstr(cleanname," SCOUT "," SCOUTS ",.) if regexm(cleanname," CUBS ")

replace cleanname = subinstr(cleanname," BEAVER GROUP "," BEAVERS ",.)
replace cleanname = subinstr(cleanname," BEAVER GROUPS "," BEAVERS ",.)
replace cleanname = subinstr(cleanname," BEAVERS GROUP "," BEAVERS ",.)
replace cleanname = subinstr(cleanname," BEAVERS GROUPS "," BEAVERS ",.)

replace cleanname = subinstr(cleanname," BEAVER COLONY "," BEAVERS ",.)
replace cleanname = subinstr(cleanname," BEAVERS COLONY "," BEAVERS ",.)

replace cleanname = subinstr(cleanname," BEAVER "," BEAVERS ",.) if regexm(cleanname," SCOUTS ")
replace cleanname = subinstr(cleanname," BEAVER "," BEAVERS ",.) if regexm(cleanname," CUBS ")

*can't force in 'scouts' with all cases of 'beavers' in case it's a 'save the beavers' charity.

replace cleanname = subinstr(cleanname," CESCHOOL "," CE SCHOOL ",.)
replace cleanname = subinstr(cleanname," CPSCHOOL "," CP SCHOOL ",.)
replace cleanname = subinstr(cleanname," RCSCHOOL "," RC SCHOOL ",.)

replace cleanname = subinstr(cleanname," ROMAN CATHOLIC "," RC ",.) if regexm(cleanname,"SCHOOL")
replace cleanname = subinstr(cleanname," CATHOLIC "," RC ",.) if regexm(cleanname,"SCHOOL")

replace cleanname = subinstr(cleanname," CHURCH ENGLAND "," CE ",.) if regexm(cleanname,"SCHOOL")

replace cleanname = subinstr(cleanname," JUNIOR INFANT "," JI ",.) if regexm(cleanname,"SCHOOL")

replace cleanname = subinstr(cleanname," PRE SCHOOL "," PRESCHOOL ",.)
replace cleanname = subinstr(cleanname," PLAY SCHOOL "," PLAYSCHOOL ",.)

replace cleanname = subinstr(cleanname," WOMENS INSTITUTE "," WI ",.)
replace cleanname = subinstr(cleanname," WOMEN INSTITUTE "," WI ",.)

replace cleanname = subinstr(cleanname," WORKINGMENS "," WORKING MENS ",.)
replace cleanname = subinstr(cleanname," WORKING MENS SOCIAL CLUB "," WMC ",.)
replace cleanname = subinstr(cleanname," WORKING MENS CLUB "," WMC ",.)
replace cleanname = subinstr(cleanname," WORKMENS CLUB "," WMC ",.)
replace cleanname = subinstr(cleanname," WMC INSTITUTE "," WMC ",.)

replace cleanname = subinstr(cleanname," SAINT "," ST ",.)

replace cleanname = subinstr(cleanname," NORTH EAST "," NE ",.)
replace cleanname = subinstr(cleanname," NORTH WEST "," NW ",.)
replace cleanname = subinstr(cleanname," SOUTH EAST "," SE ",.)
replace cleanname = subinstr(cleanname," SOUTH WEST "," SW ",.)
replace cleanname = subinstr(cleanname," NORTHEAST "," NE ",.)
replace cleanname = subinstr(cleanname," NORTHWEST "," NW ",.)
replace cleanname = subinstr(cleanname," SOUTHEAST "," SE ",.)
replace cleanname = subinstr(cleanname," SOUTHWEST "," SW ",.)
replace cleanname = subinstr(cleanname," STH "," SOUTH ",.)

replace cleanname = subinstr(cleanname," COF E "," CE ",.)
replace cleanname = subinstr(cleanname," C OFE "," CE ",.)
replace cleanname = subinstr(cleanname," COFE "," CE ",.)

replace cleanname = subinstr(cleanname," MIDDLESEX "," MIDDX ",.)
replace cleanname = subinstr(cleanname," BEDFORDSHIRE "," BEDS ",.)
replace cleanname = subinstr(cleanname," BERKSHIRE "," BERKS ",.)
replace cleanname = subinstr(cleanname," BUCKINGHAMSHIRE "," BUCKS ",.)
replace cleanname = subinstr(cleanname," CAMBRIDGESHIRE "," CAMBS ",.)
replace cleanname = subinstr(cleanname," HUNTINGDONSHIRE "," HUNTS ",.)
replace cleanname = subinstr(cleanname," CHESHIRE "," CHES ",.)
replace cleanname = subinstr(cleanname," DERBYSHIRE "," DERBYS ",.)
replace cleanname = subinstr(cleanname," CO DURHAM "," COUNTY DURHAM ",.)
replace cleanname = subinstr(cleanname," GLOUCESTERSHIRE "," GLOS ",.)
replace cleanname = subinstr(cleanname," HAMPSHIRE "," HANTS ",.)
replace cleanname = subinstr(cleanname," HAMPS "," HANTS ",.)
replace cleanname = subinstr(cleanname," HEREFORDSHIRE "," HEREFS ",.)
replace cleanname = subinstr(cleanname," HERTFORDSHIRE "," HERTS ",.)
replace cleanname = subinstr(cleanname," ISLE OF WIGHT "," IOW ",.)
replace cleanname = subinstr(cleanname," ISLE WIGHT "," IOW ",.)
replace cleanname = subinstr(cleanname," LANCASHIRE "," LANCS ",.)
replace cleanname = subinstr(cleanname," LEICESTERSHIRE "," LEICS ",.)
replace cleanname = subinstr(cleanname," LINCOLNSHIRE "," LINCS ",.)
replace cleanname = subinstr(cleanname," NORTHAMPTONSHIRE "," NORTHANTS ",.)
replace cleanname = subinstr(cleanname," NLAND "," NORTHUMBERLAND ",.)
replace cleanname = subinstr(cleanname," NOTTINGHAMSHIRE "," NOTTS ",.)
replace cleanname = subinstr(cleanname," OXFORDSHIRE "," OXON ",.)
replace cleanname = subinstr(cleanname," SHROPSHIRE "," SALOP ",.)
replace cleanname = subinstr(cleanname," SHROPS "," SALOP ",.)
replace cleanname = subinstr(cleanname," STAFFORDSHIRE "," STAFFS ",.)
replace cleanname = subinstr(cleanname," WARWICKSHIRE "," WARKS ",.)
replace cleanname = subinstr(cleanname," WILTSHIRE "," WILTS ",.)
replace cleanname = subinstr(cleanname," WORCESTERSHIRE "," WORCS ",.)
replace cleanname = subinstr(cleanname," YORKSHIRE "," YORKS ",.)

replace cleanname = subinstr(cleanname," SOUTHAMPTION "," SOUTHAMPTON ",.)
replace cleanname = subinstr(cleanname," SOTHAMPTON "," SOUTHAMPTON ",.)
replace cleanname = subinstr(cleanname," BRIMINGHAM "," BIRMINGHAM ",.)
replace cleanname = subinstr(cleanname," BHAM "," BIRMINGHAM ",.)
replace cleanname = subinstr(cleanname," BIRMINGAHM "," BIRMINGHAM ",.)
replace cleanname = subinstr(cleanname," PERY BARR "," PERRY BARR ",.)
replace cleanname = subinstr(cleanname," GLAGOW "," GLASGOW ",.)


replace cleanname = subinstr(cleanname," FOOTBALL CLUB "," FC ",.)

replace cleanname = subinstr(cleanname," YOUNG MENS CHRISTIAN ASSOC "," YMCA ",.)
replace cleanname = subinstr(cleanname," YOUNG WOMENS CHRISTIAN ASSOC "," YWCA ",.)

replace cleanname = subinstr(cleanname," INCORPORATED "," INC ",.)

replace cleanname = subinstr(cleanname," AFC "," FC ",.)

replace cleanname = subinstr(cleanname," JUNIORS FC "," JUNIOR FC ",.)
replace cleanname = subinstr(cleanname," JFC "," JUNIOR FC ",.)
replace cleanname = subinstr(cleanname," ARLFC "," AMATEUR RUGBY LEAGUE FC ",.)
replace cleanname = subinstr(cleanname," RUFC "," RUGBY UNION FC ",.)
replace cleanname = subinstr(cleanname," RLFC "," RUGBY LEAGUE FC ",.)
replace cleanname = subinstr(cleanname," RFC "," RUGBY FC ",.)
replace cleanname = subinstr(cleanname," YFC "," YOUTH FC ",.)

replace cleanname = subinstr(cleanname," NEWCASTLE UPON TYNE "," NEWCASTLE ",.)
replace cleanname = subinstr(cleanname," NEWCASTLE TYNE "," NEWCASTLE ",.)

replace cleanname = subinstr(cleanname," HOLME UPON SPALDING MOOR "," HOLME SPALDING MOOR ",.)

replace cleanname = subinstr(cleanname," UPON "," ",.)

**The next bit ensures all numeric references are in an ugly but matchable form

replace cleanname = subinstr(cleanname," 1ST "," FIRST ",.)
replace cleanname = subinstr(cleanname," IST "," FIRST ",.)
replace cleanname = subinstr(cleanname," 2ND "," SECOND ",.)
replace cleanname = subinstr(cleanname," 3RD "," THIRD ",.)
replace cleanname = subinstr(cleanname," FOURTH "," 4 ",.)
replace cleanname = subinstr(cleanname," FIFTH "," 5 ",.)
replace cleanname = subinstr(cleanname," SIXTH "," 6 ",.)
replace cleanname = subinstr(cleanname," SEVENTH "," 7 ",.)
replace cleanname = subinstr(cleanname," EIGHTH "," 8 ",.)
replace cleanname = subinstr(cleanname," NINTH "," 9 ",.)
replace cleanname = subinstr(cleanname," TENTH "," 10 ",.)
replace cleanname = subinstr(cleanname," ELEVENTH "," 11 ",.)
replace cleanname = subinstr(cleanname," TWELFTH "," 12 ",.)
replace cleanname = subinstr(cleanname," THIRTEENTH "," 13 ",.)
replace cleanname = subinstr(cleanname," FOURTEENTH "," 14 ",.)
replace cleanname = subinstr(cleanname," FIFTEENTH "," 15 ",.)
replace cleanname = subinstr(cleanname," SIXTEENTH "," 16 ",.)
replace cleanname = subinstr(cleanname," SEVENTEENTH "," 17 ",.)
replace cleanname = subinstr(cleanname," EIGHTEENTH "," 18 ",.)
replace cleanname = subinstr(cleanname," NINETEENTH "," 19 ",.)
replace cleanname = subinstr(cleanname," TWENTIETH "," 20 ",.)

replace cleanname = cleanname + " 1 " if regexm(cleanname," FIRST ")
replace cleanname = cleanname + " 2 " if regexm(cleanname," SECOND ")
replace cleanname = cleanname + " 3 " if regexm(cleanname," THIRD ")

replace cn = cleanname

*and now elimination of remaining suffices, eg 100th &c
forvalues tdigit = 0/9 {
   scalar ststr = string(`tdigit')+"ST "
   scalar ndstr = string(`tdigit')+"ND "
   scalar rdstr = string(`tdigit')+"RD "
   scalar thstr = string(`tdigit')+"TH "
   scalar newstr = string(`tdigit')+" "
   quietly replace cn = subinstr(cn,ststr,newstr,.)
   quietly replace cn = subinstr(cn,ndstr,newstr,.)
   quietly replace cn = subinstr(cn,rdstr,newstr,.)
   quietly replace cn = subinstr(cn,thstr,newstr,.)
}

replace cleanname = cn
*just to show how many were changed
*that's the end of the numeric references

replace cleanname = subinstr(cleanname," CO OPERAT"," COOPERAT",.)
replace cleanname = subinstr(cleanname," CO ORDINAT"," COORDINAT",.)

replace cleanname = subinstr(cleanname," PRIMARY CARE TRUST"," PCT",.)
replace cleanname = subinstr(cleanname," NATIONAL HEALTH SERVICE "," NHS ",.)

*can only drop the indefinite article now, after abbreviations have been compacted.
replace cleanname = subinstr(cleanname," A "," ",.)

*reduce all multi-spaces to singles again
replace cleanname=itrim(cleanname)

replace cn=trim(lower(cleanname))

compress


**That's the end of basic name-processing.

