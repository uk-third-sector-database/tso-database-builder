from pathlib import Path

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
from spine.bootstrap_base_files import write_base_files, AS_OF_ITERATION
from spine.bootstrap_ch_scrape import write_ch_scrape_bootstrap
from spine.bootstrap_lost_registers import write_lost_register_files
from spine.seed_supplementary import seed_supplementary as run_seed_supplementary
from spine.suppress_echo_matches import suppress_echo_matches as run_suppress_echo_matches
from spine.build_public_spine import process_csvs_to_build_spine
from spine.verify_build import (
    RepresentationError,
    create_tex_table,
    verify_representation,
)
from spine.add_cso_type import add_cso_type_to_spine
from spine.release import (
    ReleasePackagingError,
    ReleaseValidationError,
    format_package_report,
    format_validation_report,
    prepare_release as run_prepare_release,
    validate_release as run_validate_release,
)


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
@click.argument("spine_csv")
@click.argument("supplementary_csv")
@click.argument("matches_csv")
@click.option("-o", "raw_data_root", default="../raw_data",
              help="Folder to write the reconstructed base files under (default ../raw_data).")
@click.option("--as-of", "as_of", default=AS_OF_ITERATION,
              help="Currency of the published release being read, as mm/yyyy "
                   "(default %s, the published v1.0 = January 2026 build)." % AS_OF_ITERATION)
def bootstrap_base_files(spine_csv, supplementary_csv, matches_csv, raw_data_root, as_of):
    """
    Reconstruct the three historical charity-regulator base files
    (ccew/ccew_spine_public.csv, oscr/oscr_spine_public.csv, ccni/ccni_spine.csv)
    from a published Spine release (its spine, supplementary and matches CSVs).
    Run this ONCE before process-charity-source when the original base files
    are unavailable - see RUNBOOK.md section 3.1.
    """
    write_base_files(spine_csv, supplementary_csv, matches_csv, raw_data_root, as_of=as_of)


@cli.command()
@click.argument("spine_csv")
@click.argument("supplementary_csv")
@click.argument("matches_csv")
@click.argument("sic_csv")
@click.option("-o", "raw_data_root", default="../raw_data",
              help="Folder to write the reconstructed scrape file under (default ../raw_data).")
def bootstrap_ch_scrape(spine_csv, supplementary_csv, matches_csv, sic_csv, raw_data_root):
    """
    Reconstruct the lost 2022 Companies House advanced-search scrape file
    (CompaniesHouse/ch_adv_scrape_bootstrap.csv) from a published Spine
    release (its spine, supplementary, matches and SIC_codes CSVs).
    Run this ONCE before preprocess-CH when the 2022 file is unavailable -
    without it a from-raw rebuild silently drops companies dissolved
    before the bulk downloads began. See RUNBOOK.md section 3.
    """
    write_ch_scrape_bootstrap(spine_csv, supplementary_csv, matches_csv,
                              sic_csv, raw_data_root)


@cli.command()
@click.argument("spine_csv")
@click.argument("supplementary_csv")
@click.argument("matches_csv")
@click.option("-o", "raw_data_root", default="../raw_data",
              help="Folder holding the register download folders (default ../raw_data).")
@click.option("--as-of", "as_of", default=AS_OF_ITERATION,
              help="Currency of the published release being read, as mm/yyyy "
                   "(default %s, the published v1.0 = January 2026 build)." % AS_OF_ITERATION)
def bootstrap_lost_registers(spine_csv, supplementary_csv, matches_csv,
                             raw_data_root, as_of):
    """
    Reconstruct the lost co-op / housing / care register history from a
    published Spine release: one historical snapshot file per register
    (Co-operatives, Social Housing England, Scottish Housing Regulator,
    Care Inspectorate Scotland) containing the organisations present in the
    release but absent from the fresh downloads on disk. Run ONCE, after the
    fresh register downloads are in place and BEFORE handler/preprocess.py -
    see RUNBOOK.md section 3.1.3. Refuses to overwrite its outputs.
    """
    write_lost_register_files(spine_csv, supplementary_csv, matches_csv,
                              raw_data_root, as_of=as_of)


@cli.command()
@click.argument("built_supplementary_csv")
@click.argument("built_spine_csv")
@click.argument("built_matches_csv")
@click.argument("prior_supplementary_csv")
def seed_supplementary(built_supplementary_csv, built_spine_csv,
                       built_matches_csv, prior_supplementary_csv):
    """
    Union a published release's supplementary rows into a freshly built
    supplementary file, so historical name/address variants that only exist
    in the published release are not lost by a from-raw rebuild. Keeps only
    rows whose organisation is represented in the freshly built release
    (spine uids plus matches uids - absorbed organisations keep their own
    uid in the supplementary file); skips rows the rebuild already produced.
    Run AFTER build-spine, before packaging. The pre-seed file is kept as
    <name>.preseed.csv.
    """
    run_seed_supplementary(built_supplementary_csv, built_spine_csv,
                           built_matches_csv, prior_supplementary_csv)


@cli.command()
@click.argument("built_matches_csv")
@click.argument("prior_matches_csv")
def suppress_echo_matches(built_matches_csv, prior_matches_csv):
    """
    Remove bootstrap-echo 'companyid - id_in_source' rows from a freshly
    built matches file: rows that re-fire on company numbers the bootstrap
    back-filled from the prior release's own links, restating an existing
    pair as if it were independent identifier evidence. A row is suppressed
    only if the prior release did not publish it, the prior release already
    linked the pair another way, and the pair keeps other evidence in the
    built file (so no pair is ever disconnected). Run AFTER build-spine.
    Keeps the original as <name>.preecho.csv and the removed rows as
    <name>.suppressed-echo.csv.
    """
    run_suppress_echo_matches(built_matches_csv, prior_matches_csv)


@cli.command()
@click.argument('ofile',default = 'CH.all.preprocess.csv',nargs=1)
def preprocess_CH(ofile):
    print(f'Running preprocess CH. ')
    main_process(ofile)
    print(f'file {ofile} written')


@cli.command()
@click.argument("infiles", nargs =-1)
@click.option("-o", "outfile_base", default="public_spine")
@click.option("--allow-missing-linkage", is_flag=True, default=False,
              help="Proceed even if the external linkage files (Find that Charity same-as, OSCR linkage) are missing. Without this flag a missing file stops the build, because those files supply the majority of cross-register links.")
def build_spine(infiles, outfile_base, allow_missing_linkage):
    """
    Generate organisational spine, plus matches, plus supplementary files, for all given inputs (in format {source}.spine.csv with {source}.supplementary.csv in the same folder)
    """
    MainOrgs = process_csvs_to_build_spine(infiles, allow_missing_linkage=allow_missing_linkage)
    print('PROGRESS: process_csvs_to_build_spine complete. Now to write to files...\n')
    print(MainOrgs)
    MainOrgs.write_out(outfile_base+'.spine.csv', 
                       outfile_base+'.supplementary.csv', 
                       outfile_base+'.matches.csv')
    


@cli.command()
@click.argument("infiles", nargs =-1)
@click.option("-o", "outfile_base", default="public_spine")
def check_spine(infiles, outfile_base):
    """Fail unless every non-care input UID is represented in the outputs."""

    if not infiles:
        raise click.ClickException("at least one source spine input is required")
    try:
        verify_representation(infiles, outfile_base)
    except RepresentationError as exc:
        raise click.ClickException(str(exc)) from exc
    

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


@cli.command()
@click.argument('spine_csv')
@click.argument('sic_csv')
@click.option("-o", "outfile", default=None,
              help="Output path. If omitted the spine CSV is rewritten in place (as in the published release).")
def add_cso_type(spine_csv, sic_csv, outfile):
    """
    Append the cso_type and cso_subtype classification columns to a built
    spine CSV, using the SIC codes lookup. This is the final step of the
    build and must run after build-sic-codes-list.
    """
    add_cso_type_to_spine(spine_csv, sic_csv, outfile)


@cli.command("validate-release")
@click.argument(
    "data_dir",
    type=click.Path(
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        path_type=Path,
    ),
)
def validate_release_command(data_dir):
    """Validate the four canonical release CSV files in DATA_DIR.

    Checks file names, exact schemas, logical CSV rows, UIDs, dates, match
    references and SIC-code structure. Prints logical counts and SHA-256
    hashes. Any failed check exits nonzero.
    """
    try:
        result = run_validate_release(data_dir)
    except ReleaseValidationError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(format_validation_report(result))


@cli.command("prepare-release")
@click.argument(
    "data_dir",
    type=click.Path(
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        path_type=Path,
    ),
)
@click.argument(
    "guidance_html",
    type=click.Path(
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        path_type=Path,
    ),
)
@click.argument(
    "guidance_pdf",
    type=click.Path(
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        path_type=Path,
    ),
)
@click.argument(
    "licence_file",
    type=click.Path(
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        path_type=Path,
    ),
)
@click.argument(
    "output_dir",
    type=click.Path(
        exists=False,
        file_okay=False,
        dir_okay=True,
        writable=True,
        path_type=Path,
    ),
)
@click.option(
    "--zip/--no-zip",
    "create_zip",
    default=True,
    show_default=True,
    help="Also create a deterministic transport ZIP of the seven payload files.",
)
def prepare_release_command(
    data_dir,
    guidance_html,
    guidance_pdf,
    licence_file,
    output_dir,
    create_zip,
):
    """Validate and create a new, exact-whitelist public release directory.

    DATA_DIR supplies the four canonical TSCS CSVs. GUIDANCE_HTML,
    GUIDANCE_PDF and LICENCE_FILE must use their canonical published names.
    OUTPUT_DIR must not exist. This command only copies files; it never runs
    Git, commits, pushes or deploys.
    """
    try:
        result = run_prepare_release(
            data_dir,
            guidance_html,
            guidance_pdf,
            licence_file,
            output_dir,
            create_zip=create_zip,
        )
    except (ReleaseValidationError, ReleasePackagingError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(format_validation_report(result.validation))
    click.echo("")
    click.echo(format_package_report(result))


if __name__ == "__main__":
    cli()















