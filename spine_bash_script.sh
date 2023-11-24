#!/bin/bash


##--------------- process sources --------------------------

## companies house files:
#python3 cli.py process-source CompaniesHouse ../TSO_project/raw_data/BasicCompanyDataAsOneFile-2023-06-01.csv spine_data/CH_June_2023.spine.csv
python3 cli.py process-source CompaniesHouse ../TSO_project/raw_data/BasicCompanyDataAsOneFile-2023-10-04.csv spine_data/CH_Oct_2023.spine.csv
python3 cli.py process-source CompaniesHouse2014 ../TSO_project/raw_data/soton14reduced.csv spine_data/CH_2014.spine.csv
python3 cli.py process-source CompaniesHouseGapDecade ../TSO_project/raw_data/ch_adv_scrape.csv spine_data/CH_gap_decade.spine.csv
#
#
## Care Inspectorate Scotland files: 
for i in ../TSO_project/raw_data/CareInspectScot/MDSF_data_*
do
  python3 cli.py process-source CareInspScot "$i" $i.spine.csv
done
mv ../TSO_project/raw_data/CareInspectScot/*spine.csv spine_data/
#
#
## Care Quality Commission:
python3 cli.py process-source CQC ../TSO_project/raw_data/CareQualityCommission/25_January_2023_CQC_directory__.csv spine_data/CQC_Jan_2023.spine.csv
#
#
## Co Ops & Mutuals:
python3 cli.py process-source CoOps ../TSO_project/raw_data/co_ops.open_data_orgs_2022_q2.csv spine_data/CoOps_2022.spine.csv
python3 cli.py process-source Mutuals ../TSO_project/raw_data/mutuals-spine-2023-06-07.csv spine_data/mutuals.spine.csv
#
## Social Housing England:
python3 cli.py process-source SocialHousingEng ../TSO_project/raw_data/SocialHousingEngland_202301016.csv spine_data/SocialHousingEngland_2023.spine.csv
#
#
## Scottish Housing Regulator:
for i in ../TSO_project/raw_data/ScotHousingReg/afs-data-all-social-landlords-complete-dataset-20*
do
  python3 cli.py process-source ScotHousingReg $i $i.spine.csv
done
mv ../TSO_project/raw_data/ScotHousingReg/*spine.csv spine_data/
#
## Charity regulators:
python3 cli.py process-source CCEW ../TSO_project/raw_data/ccew_spine.csv spine_data/ccew.spine.csv
python3 cli.py process-source CCNI ../TSO_project/raw_data/ccni_spine.csv spine_data/ccni.spine.csv
python3 cli.py process-source OSCR ../TSO_project/raw_data/oscr_spine.csv spine_data/oscr.spine.csv


##-----------------------------

# #concatenate all
python3 cli.py concat spine_data/*csv -o processed_data/all.concat.csv
python3 cli.py permutate processed_data/all.concat.csv -f False -o processed_data/all.concat.permutate.csv
 #find matches 
python3 cli.py match processed_data/all.concat.permutate.csv 'companyid' -o processed_data/all.matched_companyid.csv
python3 cli.py permutate processed_data/all.matched_companyid.csv -f False -o processed_data/all.matched_companyid.permutate.csv

# upsetplot to see matches by companyid only:
#python3 cli.py plot-upset processed_data/all.matched_companyid.permutate.csv all -o  all.companyid.upsetplot.png

# find matches by normalisedname
python3 cli.py match processed_data/all.matched_companyid.permutate.csv 'normalisedname' -o processed_data/all.matched_companyid.matched_normname.csv
# permutate all names and addresses for identical uids
#-f True as final permutation
python3 cli.py permutate processed_data/all.matched_companyid.matched_normname.csv -f True -o processed_data/all.matched_companyid.matched_normname.permutate.csv

#counts
python3 visualise/source_plots.py > all_data.matchtypes.out
#plot to see in
python3 cli.py plot-upset processed_data/all.matched_companyid.matched_normname.permutate.csv all -o  all.matches.upsetplot.png


# just companies house: concat, match by company id. To see overlap between the three datasets

python3 cli.py concat spine_data/CH_*csv -o processed_data/all_CH.concat.csv

python3 cli.py concat spine_data/June_data/CH_June_2023.spine.csv spine_data/CH_2014.spine.csv spine_data/CH_gap_decade.spine.csv -o processed_data/all_CH.June.concat.csv

# for June data: 
n='all_CH.June'  # else make n = 'all_CH'


python3 cli.py permutate processed_data/$n.concat.csv -f False -o processed_data/$n.concat.permutate.csv
python3 cli.py match processed_data/$n.concat.permutate.csv 'companyid' -o processed_data/$n.matched_companyid.csv
python3 cli.py permutate processed_data/$n.matched_companyid.csv -f False -o processed_data/$n.matched_companyid.permutate.csv
python3 cli.py plot-ch-venn processed_data/$n.matched_companyid.permutate.csv -o $n.sources_venn.png