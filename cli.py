import click
import os

from handler.base import do_csv_processing
from handler.base_definitions import NEW_SPINE_CSV_FORMAT

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

from spine.wrangling import concat as concatenate
from spine.wrangling import permutate as write_permutations
from spine.wrangling import final_processing
from spine.matching import deduplicate

from visualise.venn_diagrams import venn_diagram_info_using_pandas,venn3_by_source_list
from visualise.source_plots import sources, source_codes
from visualise.source_plots import plot_upset_by_code, match_type_counts



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
    intermediate_ofile = outfile.split('.csv')[0] + '.tmp.csv'
    do_csv_processing(infile, intermediate_ofile, handler_map[source]())

    #consolidate all details for each org, and add geography lookup fields
    write_permutations(open(intermediate_ofile,'r'),open(outfile,'w+'),False)
    try:
        os.remove(intermediate_ofile)
    except OSError as e:
        print(f'error attempting to remove {intermediate_ofile}')


@cli.command()
@click.argument("src", type=click.File("r", encoding='UTF8'), nargs = -1) 
@click.option(
    "-o", "--output", default="concat.out.csv", show_default=True, type=click.File("w", encoding='UTF8')
)
def concat(src, output):
    """
    Concatenate SPINE files into a single SPINE file.
    """
    print(src)
    print(output)
    concatenate(src, output)




@cli.command()
@click.argument("src", type=click.File("r"), nargs=1)
@click.argument("field", type=click.Choice(NEW_SPINE_CSV_FORMAT), nargs=1)
@click.option("-t", "--threshold", default=4, show_default=True, type=click.INT)
@click.option("-o", "--output", default="direct_matches.out.csv", show_default=True, type=click.File("w"))
def match(src, output, field, threshold):
    """
    For a given input csv file (in SPINE format), find direct matches between records
    Charities with company ids: direct lookup
    100% match between name and postcode
    (later: this will also call deduplicate to find close matches for human checking)
    """
    deduplicate(src,output,field,threshold)



@cli.command()
@click.argument("src", type=click.File("r", encoding='UTF8'), nargs=1)
@click.option("-o", "--output", default="permutate.out.csv", show_default=True, type=click.File("w"))
@click.option("-f", "--final", default=False, type=click.BOOL)
def permutate(src, output,final):
    """
    For a given input csv file (in SPINE format), find all with the same uid and create rows for all
    permutations of names and addresses associated
    Use option -f if final permutation - consolidates all companies house source info to 'CH' only
    """
    write_permutations(src,output,final)
    print('Permutations complete. Output written to %s'%output)

    if final:
        # add rowid field, and remove charitynumber field

        final_filename = final_processing(output)
        print('Final processing complete. Output written to %s'%final_filename)



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
