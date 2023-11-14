# Getting Started

Use python 3.11

    make setup-pyenv
    pyenv activate ukri-env
    make install-deps
    
## Installing requirements

To install test and runtime requirements use

    pip install -r test-requirements.txt

To only install runtime requirements use:

    pip install -r requirements.txt

## Testing 

    pytest . 

## Running

    python cli.py sub-spine <data-source> <input-csv> <output-csv> 
    python cli.py concat <input-csv-1> <input-csv-2> ... <input-csv-n> -o <output-csv>
    python cli.py match <input-csv> <output-csv> 

example:

    python cli.py sub-spine txt.csv out.csv CompaniesHouse

    use spine_bash_script.sh to see all commands and algorithm

## Adding new data sources

Each datasource should be added as a subclass of `DataHandler` and have a mapping to it defined 
in cli.py 

## Raw data on sharepoint:

    CH: TSOData/Masterlist/CompaniesHouse (use most recent bulk download)
    Care Inspectorate: TSOData/Masterlist/CareInspectorateScotland
    Care Quality Commission: TSOData/Masterlist/careQualityCommission
    CoOps: TSOData/SpineData
    Mutuals: TSOData/SpineData
    Social housing England: TSOData/Masterlist/SocialHousingEngland
    Scottish housing regulator: TSOData/Masterlist/ScottishHousingRegulator
    Charity regulators: TSOData/[NorthernIreland/ccni_spine.csv]|[Scotland/ocsr_spine.csv]|[EW/ccew_spine.csv]












