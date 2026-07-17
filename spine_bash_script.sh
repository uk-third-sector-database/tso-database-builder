#!/bin/bash

## --------------- preprocess sources to include iteration -----------
python3 handler/preprocess.py
python3 cli.py preprocess-ch ../raw_data/CH.all.csv
python3 cli.py process-charity-source ccni
python3 cli.py process-charity-source oscr
python3 cli.py process-charity-source ccew

##--------------- process sources --------------------------

## companies house files:
python3 cli.py process-source CompaniesHouse ../raw_data/CH.all.csv ../public_spine_data/CH_all.spine.csv
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
python3 cli.py process-source SocialHousingEng ../raw_data/SocialHousingEng.all.csv ../public_spine_data/SocialHousingEngland.spine.csv
#
#
## Scottish Housing Regulator:
python3 cli.py process-source ScotHousingReg ../raw_data/ScotHousingReg.all.csv ../public_spine_data/ScotHousingReg.spine.csv
#
## Charity regulators:
python3 cli.py process-source CCEW ../raw_data/ccew.all.csv ../public_spine_data/ccew.spine.csv
python3 cli.py process-source CCNI ../raw_data/ccni.all.csv ../public_spine_data/ccni.spine.csv
python3 cli.py process-source OSCR ../raw_data/oscr.all.csv ../public_spine_data/oscr.spine.csv


##-----------------------------

# NOTE: the input order below is part of the linkage method (earlier files
# take precedence and most match rules only fire against already-loaded
# records). Do not reorder without documenting the change.
python3 cli.py build-spine ../public_spine_data/ccew.spine.csv ../public_spine_data/oscr.spine.csv ../public_spine_data/ccni.spine.csv ../public_spine_data/mutuals.spine.csv ../public_spine_data/CH_all.spine.csv ../public_spine_data/CoOps.spine.csv  ../public_spine_data/ScotHousingReg.spine.csv ../public_spine_data/SocialHousingEngland.spine.csv ../public_spine_data/CareInspectScot.spine.csv ../public_spine_data/CQC.spine.csv -o ../public_spine_data/TSCS_spine &> build_spine.out

# Verify every input organisation is accounted for in the outputs
python3 cli.py check-spine ../public_spine_data/ccew.spine.csv ../public_spine_data/oscr.spine.csv ../public_spine_data/ccni.spine.csv ../public_spine_data/mutuals.spine.csv ../public_spine_data/CH_all.spine.csv ../public_spine_data/CoOps.spine.csv  ../public_spine_data/ScotHousingReg.spine.csv ../public_spine_data/SocialHousingEngland.spine.csv ../public_spine_data/CareInspectScot.spine.csv ../public_spine_data/CQC.spine.csv -o ../public_spine_data/TSCS_spine

# SIC codes lookup. Must read the matches file written by build-spine above
# (an earlier version of this script pointed at public_spine.matches.csv,
# which meant the SIC file was built from a stale matches table).
python3 cli.py build-sic-codes-list ../raw_data/CH.all.csv ../public_spine_data/TSCS_spine.matches.csv ../public_spine_data/TSCS_spine.SIC_codes.csv

##-----------------------------

# Final step: append the cso_type / cso_subtype classification columns
# (documented in the Organisation Register guidance). Rewrites the spine
# CSV in place; requires the SIC codes file from the previous step.
python3 cli.py add-cso-type ../public_spine_data/TSCS_spine.spine.csv ../public_spine_data/TSCS_spine.SIC_codes.csv

#counts
#python3 visualise/source_plots.py > all_data.matchtypes.out
