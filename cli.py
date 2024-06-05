import click

from handler.base import do_csv_processing,compress_org_details

from handler.companies_house import CompaniesHouseDataHandler
from handler.companies_house_2014 import CompaniesHouse2014DataHandler
from handler.companies_house_gap_decade import CompaniesHouseGapDataHandler
from handler.co_ops import CoOpsDataHandler
from handler.careInspectScot import CareInspScotDataHandler
from handler.careQC import CQCDataHandler
from handler.socialHousingEng import SocialHousingEngDataHandler
from handler.ScotHousingReg import ScotHousingRegDataHandler
from handler.mutuals import MutualsDataHandler
from handler.ccew import CCEWDataHandler
from handler.ccni import CCNIDataHandler
from handler.oscr import OSCRDataHandler

from spine.build_public_spine import process_csvs_to_build_spine

from visualise.venn_diagrams import venn_diagram_info_using_pandas,venn3_by_source_list
from visualise.source_plots import sources, source_codes
from visualise.source_plots import plot_upset_by_code, match_type_counts

from handler.all_companies_house import main_process



# Add entries here of handler name to handler type for use by the command line
handler_map = {"CompaniesHouse": CompaniesHouseDataHandler,
               "CoOps": CoOpsDataHandler,
               "CompaniesHouse2014":CompaniesHouse2014DataHandler,
               "CompaniesHouseGapDecade":CompaniesHouseGapDataHandler,
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



@cli.command()
@click.argument('ofile',default = 'CH.all.preprocess.csv')
def preprocess_CH(ofile):
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
    MainOrgs.write_out(outfile_base+'.spine.csv', 
                       outfile_base+'.supplementary.csv', 
                       outfile_base+'.matches.csv')
    


@cli.command()
@click.argument("src", type=click.File("r", encoding='UTF8'), nargs=1)
@click.option(
    "-o", "--output", default="COH_venn.png", show_default=True, type=str
)
def plot_CH_venn(src, output):
    """
    For a given input csv file (in SPINE format), plot a venn diagram of the sources for unique uids (used after matching and permutating)
    Currently only coded for companies house sources, since matplotlib_venn has a limit of 3 circles.
    """
    venn_diagram_info_using_pandas(src,output)
    print('Plotting of %s COH sources complete. Output written to %s'%(src,output))


@cli.command()
@click.argument("src", type=click.File("r", encoding='UTF8'), nargs=1)
@click.argument("venn_sets", type=str, nargs=-1)
@click.option("-o", "--output", type=str)
def plot_venn(src, venn_sets, output):
    """
    For a given input csv file (in SPINE format), plot a venn diagram of the sources for unique uids (used after matching and permutating)
    Since matplotlib_venn has a limit of 3 circles, venn_sets must be size 3
    """
    print(venn_sets)
    venn3_by_source_list(src,output,venn_sets)
    print('Plotting of %s, sources %s, complete. Output written to %s'%(src,', '.join(venn_sets),output))



@cli.command()
@click.argument("src", type=str, nargs=1)
def match_counts(src):
    print(f'\n\nProcessing counts of match types found in file {src}:\n')
    match_type_counts(src)





@cli.command()
@click.argument("src", type=click.File("r", encoding='UTF8'), nargs=1)
@click.argument("sets_list", type=str, nargs=-1)#click.Choice(choices=tuple(sources)), nargs=-1)
@click.option("-o", "--output", type=str)
def plot_upset(src, sets_list, output):
    """
    For a given input csv file (in SPINE format), plot a venn diagram of the sources for unique uids (used after matching and permutating)
    Since matplotlib_venn has a limit of 3 circles, venn_sets must be size 3
    """
    if sets_list[0] =='all':
        sets_list = sources
    print(sets_list)
    ofile = '%s.by_source.png'%output.split('.png')[0]
    print(ofile)

    sets_list = source_codes
    print(sets_list)
    ofile = '%s.by_uid_code.png'%output.strip('.png')
    plot_upset_by_code(src,ofile,sets_list)
    print('Plotting of %s, sources %s, complete. Output written to %s'%(src,', '.join(sets_list),ofile))



if __name__ == "__main__":
    cli()
