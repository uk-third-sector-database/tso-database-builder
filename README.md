# The Third Sector and Civil Society dataset

Welcome to the project repo for the UK's dataset of not-for-profit organisations, funded by the ESRC.
Please see project website at https://uk-third-sector-database.github.io/ for more information.

# Getting Started

Use python 3.11

    make setup-pyenv
    make setup-venv
    make install-deps
    
## Installing requirements

To install test and runtime requirements use

    pip install -r test-requirements.txt

To only install runtime requirements use:

    pip install -r requirements.txt

## Running

    To run the builder, download the data you wish to compile into a dataset, and follow the commands and algorithm
    shown in spine_bash_script.sh, altering paths. If file formats have changed in any source registers you will need to edit
    the relevant preprocess script, found in folder handler/.

Basic running syntax:

    python cli.py process-source <data-source> <input-csv> <output-csv> 
    python cli.py build-spine <processed-data-a> <processed-data-b> -o <base-output-filename>

example:

    python cli.py process-source  CompaniesHouse txt.csv out.csv


## Adding new data sources

Each datasource should be added as a subclass of `DataHandler` and have a mapping to it defined 
in cli.py 













