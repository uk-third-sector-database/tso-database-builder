import click

from handler.base import do_csv_processing,compress_org_details,sort_csv_by_field

from handler.companies_house import CompaniesHouseDataHandler
#from handler.companies_house_2014 import CompaniesHouse2014DataHandler
from handler.companies_house_API_scrape import CH_APIScrape_DataHandler
from handler.co_ops import CoOpsDataHandler
from handler.careInspectScot import CareInspScotDataHandler
from handler.careQC import CQCDataHandler
from handler.socialHousingEng import SocialHousingEngDataHandler
from handler.ScotHousingReg import ScotHousingRegDataHandler
from handler.mutuals import MutualsDataHandler
from handler.ccew import CCEWDataHandler
from handler.ccni import CCNIDataHandler
from handler.oscr import OSCRDataHandler
from handler.preprocess_charity_regulators import process_ccew,process_ccni,process_oscr
#from spine.build_public_spine_copy import process_csvs_to_build_spine
from spine.build_public_spine import process_csvs_to_build_spine
from spine.verify_build import verify_representation,create_tex_table


from handler.all_companies_house import main_process, sic_codes_lookup

import subprocess


# Add entries here of handler name to handler type for use by the command line
handler_map = {"CompaniesHouse": CompaniesHouseDataHandler,
               "CoOps": CoOpsDataHandler,
#               "CompaniesHouse2014":CompaniesHouse2014DataHandler,
               "CompaniesHouseGapDecade":CH_APIScrape_DataHandler,
               "CareInspScot":CareInspScotDataHandler,
               "CQC":CQCDataHandler,
               "SocialHousingEng":SocialHousingEngDataHandler,
               "ScotHousingReg":ScotHousingRegDataHandler,
               "Mutuals":MutualsDataHandler,
               "CCEW":CCEWDataHandler,
               "OSCR":OSCRDataHandler,
               "CCNI":CCNIDataHandler}


@click.group()
def cli():
    ...


@cli.command()
@click.argument("source", type=click.Choice(handler_map.keys()))
@click.argument("infile")
@click.argument("outfile")
def process_source(source, infile, outfile):
    """
    Generate a SPINE format file using data pulled from a source
    """
    if 'CompaniesHouse' in source:
        # companies house data preprocessed to concatenate prior to creating spine and supplementary tables (in all_companies_house.py)
        compress_org_details(infile,outfile,CompaniesHouseDataHandler())
    else:
        do_csv_processing(infile, outfile, handler_map[source]())

    # create sorted csv file from spine.csv
    sort_csv_by_field(outfile,'removeddate', 'registerdate')


@cli.command()
@click.argument("charity_source", type=click.Choice(['ccew','oscr','ccni']))
def process_charity_source(charity_source):
    """
    Generate a SPINE format file using data pulled from a charity source
    """
    if charity_source == 'ccew':
        process_ccew()
    elif charity_source == 'oscr':
        process_oscr()
    elif charity_source == 'ccni':
        process_ccni()

@cli.command()
@click.argument('ofile',default = 'CH.all.preprocess.csv',nargs=1)
def preprocess_CH(ofile):
    print(f'Running preprocess CH. ')
    main_process(ofile)
    print(f'file {ofile} written')


@cli.command()
@click.argument("infiles", nargs =-1)
@click.option("-o", "outfile_base", default="public_spine")
def build_spine(infiles, outfile_base):
    """
    Generate organisational spine, plus matches, plus supplementary files, for all given inputs (in format {source}.spine.csv with {source}.supplementary.csv in the same folder)
    """
    MainOrgs = process_csvs_to_build_spine(infiles)
    print('PROGRESS: process_csvs_to_build_spine complete. Now to write to files...\n')
    print(MainOrgs)
    MainOrgs.write_out(outfile_base+'.spine.csv', 
                       outfile_base+'.supplementary.csv', 
                       outfile_base+'.matches.csv')
    


@cli.command()
@click.argument("infiles", nargs =-1)
@click.option("-o", "outfile_base", default="public_spine")
def check_spine(infiles, outfile_base):
    verify_representation(infiles,outfile_base)
    

@cli.command()
@click.argument("outfile_base", default="public_spine", nargs = 1)
def tex_table_spine(outfile_base):
    create_tex_table(outfile_base)


@cli.command()
@click.argument('ch_prepared_file')
@click.argument('spine_matches_file')
@click.argument('ofile')
def build_sic_codes_list(ch_prepared_file,spine_matches_file,ofile):
    sic_codes_lookup(ch_prepared_file,spine_matches_file,ofile)

if __name__ == "__main__":
    cli()















