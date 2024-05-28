#!/bin/bash

## --------------- preprocess sources to include iteration -----------
python3 handler/preprocess.py
python3 cli.py preprocess-ch ../raw_data/CH.all.preprocess.csv
##--------------- process sources --------------------------

## companies house files:
python3 cli.py process-source CompaniesHouse ../raw_data/CH.all.preprocess.csv ../public_spine_data/CH_all.spine.csv
#
#
## Care Inspectorate Scotland files: 
python3 cli.py process-source CareInspScot ../raw_data/CareInspectScot.all.csv ../public_spine_data/CareInspectScot.spine.csv
#
#
## Care Quality Commission:
python3 cli.py process-source CQC ../raw_data/CareQualityCommission.all.csv ../public_spine_data/CQC.spine.csv
#
#
## Co Ops & Mutuals:
python3 cli.py process-source CoOps ../raw_data/co_ops.all.csv ../public_spine_data/CoOps.spine.csv
python3 cli.py process-source Mutuals ../raw_data/mutuals.all.csv ../public_spine_data/mutuals.spine.csv
#
## Social Housing England:
python3 cli.py process-source SocialHousingEng ../raw_data/SocialHousingEngland_202301016.csv ../public_spine_data/SocialHousingEngland.spine.csv
#
#
## Scottish Housing Regulator:
python3 cli.py process-source ScotHousingReg ../raw_data/ScotHousingReg.all.csv ../public_spine_data/ScotHousingReg.spine.csv
#
## Charity regulators:
python3 cli.py process-source CCEW ../raw_data/ccew_spine_public.csv ../public_spine_data/ccew.spine.csv
python3 cli.py process-source CCNI ../raw_data/ccni_spine.csv ../public_spine_data/ccni.spine.csv
python3 cli.py process-source OSCR ../raw_data/oscr_spine_public.csv ../public_spine_data/oscr.spine.csv


##-----------------------------

python3 cli.py build-spine ../public_spine_data/ccew.spine.csv ../public_spine_data/oscr.spine.csv ../public_spine_data/ccni.spine.csv ../public_spine_data/CH_all.spine.csv ../public_spine_data/CoOps.spine.csv ../public_spine_data/mutuals.spine.csv ../public_spine_data/ScotHousingReg.spine.csv ../public_spine_data/SocialHousingEngland.spine.csv ../public_spine_data/CareInspectScot.spine.csv ../public_spine_data/CQC.spine.csv -o ../public_spine_data/public_spine &> build_spine.out


##-----------------------------


#counts
python3 visualise/source_plots.py > all_data.matchtypes.out
