#!/bin/bash


##--------------- process sources --------------------------

## companies house files:
python3 cli.py process-source CompaniesHouse ../raw_data/BasicCompanyDataAsOneFile-2023-06-01.csv ../public_spine_data/CH_June_2023.spine.csv
python3 cli.py process-source CompaniesHouse ../raw_data/BasicCompanyDataAsOneFile-2023-10-04.csv ../public_spine_data/CH_Oct_2023.spine.csv
python3 cli.py process-source CompaniesHouse ../raw_data/BasicCompanyDataAsOneFile-2024-03-04.csv ../public_spine_data/CH_Jan_2024.spine.csv
python3 cli.py process-source CompaniesHouse2014 ../raw_data/soton14reduced.csv ../public_spine_data/CH_2014.spine.csv
python3 cli.py process-source CompaniesHouseGapDecade ../raw_data/ch_adv_scrape.csv ../public_spine_data/CH_gap_decade.spine.csv
#
#
## Care Inspectorate Scotland files: 
for i in ../raw_data/CareInspectScot/MDSF_data_*
do
  python3 cli.py process-source CareInspScot "$i" $i.spine.csv
done
mv ../raw_data/CareInspectScot/*spine.csv ../public_spine_data/
#
#
## Care Quality Commission:
python3 cli.py process-source CQC ../raw_data/CareQualityCommission/25_January_2023_CQC_directory__.csv ../public_spine_data/CQC_Jan_2023.spine.csv
#
#
## Co Ops & Mutuals:
python3 cli.py process-source CoOps ../raw_data/co_ops.open_data_orgs_2022_q2.csv ../public_spine_data/CoOps_2022.spine.csv
python3 cli.py process-source Mutuals ../raw_data/mutuals-spine-2023-06-07.csv ../public_spine_data/mutuals.spine.csv
#
## Social Housing England:
python3 cli.py process-source SocialHousingEng ../raw_data/SocialHousingEngland_202301016.csv ../public_spine_data/SocialHousingEngland_2023.spine.csv
#
#
## Scottish Housing Regulator:
for i in ../raw_data/ScotHousingReg/afs-data-all-social-landlords-complete-dataset-20*
do
  python3 cli.py process-source ScotHousingReg $i $i.spine.csv
done
mv ../raw_data/ScotHousingReg/*spine.csv ../public_spine_data/
#
## Charity regulators:
python3 cli.py process-source CCEW ../raw_data/ccew_spine_public.csv ../public_spine_data/ccew.spine.csv
python3 cli.py process-source CCNI ../raw_data/ccni_spine.csv ../public_spine_data/ccni.spine.csv
python3 cli.py process-source OSCR ../raw_data/oscr_spine_public.csv ../public_spine_data/oscr.spine.csv


##-----------------------------

# #concatenate all
python3 cli.py concat ../public_spine_data/*.spine.csv -o ../public_spine_data/all.concat.csv
python3 cli.py permutate ../public_spine_data/all.concat.csv -f False -o ../public_spine_data/all.concat.permutate.csv
 #find matches 
python3 cli.py match ../public_spine_data/all.concat.permutate.csv 'companyid' -o ../public_spine_data/all.matched_companyid.csv
python3 cli.py permutate ../public_spine_data/all.matched_companyid.csv -f False -o ../public_spine_data/all.matched_companyid.permutate.csv

# upsetplot to see matches by companyid only:
#python3 cli.py plot-upset ../public_spine_data/all.matched_companyid.permutate.csv all -o  all.companyid.upsetplot.png

# find matches by normalisedname
python3 cli.py match ../public_spine_data/all.matched_companyid.permutate.csv 'normalisedname' -o ../public_spine_data/all.matched_companyid.matched_normname.csv
# permutate all names and addresses for identical uids
#-f True as final permutation
python3 cli.py permutate ../public_spine_data/all.matched_companyid.matched_normname.csv -f True -o ../public_spine_data/all.matched_companyid.matched_normname.permutate.csv

#counts
python3 visualise/source_plots.py > all_data.matchtypes.out
#plot to see in
python3 cli.py plot-upset ../public_spine_data/all.matched_companyid.matched_normname.permutate.csv all -o  all.matches.upsetplot.png


# just companies house: concat, match by company id. To see overlap between the three datasets

python3 cli.py concat ../public_spine_data/CH_*csv -o ../public_spine_data/all_CH.concat.csv
python3 cli.py plot-ch-venn ../public_spine_data/all_CH.concat.csv -o CH.sources_venn.png

python3 cli.py concat ../public_spine_data/June_data/CH_June_2023.spine.csv ../public_spine_data/CH_2014.spine.csv ../public_spine_data/CH_gap_decade.spine.csv -o ../public_spine_data/all_CH.June.concat.csv

# for June data: 
#n='all_CH.June'  
n='all_CH'


python3 cli.py permutate ../public_spine_data/$n.concat.csv -f False -o ../public_spine_data/$n.concat.permutate.csv
python3 cli.py match ../public_spine_data/$n.concat.permutate.csv 'companyid' -o ../public_spine_data/$n.matched_companyid.csv
python3 cli.py permutate ../public_spine_data/$n.matched_companyid.csv -f False -o ../public_spine_data/$n.matched_companyid.permutate.csv
python3 cli.py plot-ch-venn ../public_spine_data/$n.matched_companyid.permutate.csv -o $n.sources_venn.png