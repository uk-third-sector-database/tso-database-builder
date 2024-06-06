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

    python cli.py process-source <data-source> <input-csv> <output-csv> 
    python cli.py concat <input-csv-1> <input-csv-2> ... <input-csv-n> -o <output-csv>
    python cli.py match <input-csv> <output-csv> 

example:

    python cli.py process-source  CompaniesHouse txt.csv out.csv

    use spine_bash_script.sh to see all commands and algorithm

## Adding new data sources

Each datasource should be added as a subclass of `DataHandler` and have a mapping to it defined 
in cli.py 













