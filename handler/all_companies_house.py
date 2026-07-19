## preprocess companies house data from the various sources, adding an iteration tag for later sorting.
## then use companies_house.py for datahandler and base constructs to sort into primary and secondary for the subspine contributions from CH.

from .base_definitions import sub_spine_entry_creator,SUB_SPINE_CSV_FIELDS
import os
import csv
import glob
import re
from .companies_house import CompaniesHouseDataHandler
from .companies_house_API_scrape import CH_APIScrape_DataHandler
#from .companies_house_2014 import CompaniesHouse2014DataHandler
import pandas as pd


from .base import iter_csv_rows

def api_scrape_iteration(file):
    # ch_adv_scrape_api_refresh_2026-07-18.csv -> '18/07/2026'. Daily
    # precision makes this refresh newer than the July bulk snapshot, whose
    # iteration is the first of the month. Dateless files are historical 2022.
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', os.path.basename(file))
    return f'{m.group(3)}/{m.group(2)}/{m.group(1)}' if m else '2022'

def process_api_scrape(file,ofile):
    print(file)
    data_handler = CH_APIScrape_DataHandler()
    data_handler.iteration_tag = api_scrape_iteration(file)
    for new_row in filter(
        data_handler.all_filters, iter_csv_rows(file,data_handler)):
        ofile.writerows(data_handler.transform_row(new_row))


#def process_2014_data(file,ofile):
#    print(file)
#    data_handler = CompaniesHouse2014DataHandler()
#    for new_row in filter(
#        data_handler.all_filters, iter_csv_rows(file,data_handler)):
#        ofile.writerows(data_handler.transform_row(new_row))

def process_bulk_download(file,ofile,datahandler):
    # extract date from filename, eg. BasicCompanyDataAsOneFile-2023-06-01.csv
    print(file)
    year,month = os.path.basename(file).split('-')[1:3]
    date = '%s/%s'%(month,year)
    data_handler = datahandler()
#    print('data_handler = ',data_handler)
    for new_row in filter(
        data_handler.all_filters, iter_csv_rows(file,data_handler)):
        rows =  data_handler.transform_row(new_row)
        for r in rows:
            if r['extraname'] == 1:
                r['iteration'] = '2000'
            else:
                r['iteration'] = date
            r.pop('extraname')

        filtered_rows = [{key: row[key] for key in ofile.fieldnames if key in row} for row in rows]

        ofile.writerows(filtered_rows)

    # halt the run if the file contained any CompanyCategory on neither the
    # include nor the exclude list (needs a human decision before the register is built)
    if hasattr(data_handler, 'raise_for_unknown_categories'):
        data_handler.raise_for_unknown_categories()

def find_CIC_uids(file,companytype_field,cic_search,encode):
    print(f'Opening {file} to find CICs, using encoding {encode}')
    with open(file, 'r', newline='', encoding=encode) as infile:
        reader = csv.DictReader(infile)
        CIC_uids = []
        for row in reader:
            if row[companytype_field] == cic_search:
                if companytype_field == 'companycategory':
                    CIC_uids.append('GB-COH-'+ row['companynumber'])
                elif companytype_field == 'company_subtype':
                    CIC_uids.append('GB-COH-'+ row['company_number'])
                else:
                    try:
                        CIC_uids.append('GB-COH-'+ row['CompanyNumber'])
                    except:
                        CIC_uids.append('GB-COH-'+ row[' CompanyNumber'])

    return CIC_uids

def main_process(ofilename):
    api_scrape_files = sorted(glob.glob('../raw_data/CompaniesHouse/ch_adv_scrape*csv'))
    #historic_data = '../raw_data/CompaniesHouse/soton14reduced.csv'
    bulk_downloads = sorted(glob.glob('../raw_data/CompaniesHouse/BasicCompanyDataAsOneFile*csv'))

    with open(ofilename, 'w+', newline='', encoding='UTF8') as outfile:
        datahandler =  CompaniesHouseDataHandler
        fields = SUB_SPINE_CSV_FIELDS + ['iteration'] + ['companytype'] + ['SIC']

        csv_writer = csv.DictWriter(outfile, fieldnames=fields)  # possibly change field list to a CH specific one?
        csv_writer.writeheader()  
        for file in api_scrape_files:
            process_api_scrape(file,csv_writer)
        #process_2014_data(historic_data,csv_writer)
        for file in bulk_downloads:
            process_bulk_download(file,csv_writer,datahandler)

SIC_CODE_RE = re.compile(r'(?<!\d)(\d{4,5})(?!\d)')


def extract_sic_codes(value):
    """Return individual four- or five-digit SIC tokens in source order."""
    if value is None:
        return []
    return SIC_CODE_RE.findall(str(value))


def iteration_rank(value):
    """Chronological rank for CH tags (YYYY, MM/YYYY or DD/MM/YYYY)."""
    value = str(value or '').strip()
    if re.fullmatch(r'\d{4}', value):
        # A bare year is the oldest point in that year.
        return int(value) * 10000 + 101
    match = re.fullmatch(r'(\d{1,2})/(\d{1,2})/(\d{4})', value)
    if match:
        day, month, year = map(int, match.groups())
        try:
            parsed = pd.Timestamp(year=year, month=month, day=day)
        except ValueError:
            return -1
        return parsed.year * 10000 + parsed.month * 100 + parsed.day
    match = re.fullmatch(r'(\d{1,2})/(\d{4})', value)
    if match:
        month, year = map(int, match.groups())
        if 1 <= month <= 12:
            return year * 10000 + month * 100 + 1
    return -1


def sic_codes_lookup(ch_file,matches_file,ofile):
    """Create a deterministic spine uid/SIC lookup from the latest CH rows.

    Only match rows with one unambiguous, nonblank absorbing uid remap a
    Companies House uid. SIC strings are split into individual four- or
    five-digit codes, with one output row per unique uid/code pair.
    """
    try:
        matches_df = pd.read_csv(
            matches_file,
            usecols=['uid','orgB_uid'],
            dtype=str,
            keep_default_na=False,
        )
    except ValueError as e:
        raise RuntimeError(
            f'Error loading matches data from {matches_file}: {e}'
        ) from e

    matches_df['uid'] = matches_df['uid'].str.strip()
    matches_df['orgB_uid'] = matches_df['orgB_uid'].str.strip()
    mapped_rows = matches_df[
        matches_df['uid'].ne('')
        & matches_df['orgB_uid'].str.startswith('GB-COH-')
    ]

    parent_sets = mapped_rows.groupby('orgB_uid', sort=True)['uid'].agg(
        lambda values: tuple(sorted(set(values)))
    )
    conflicts = parent_sets[parent_sets.map(len) > 1]
    if not conflicts.empty:
        sample = '; '.join(
            f'{child} -> {", ".join(parents)}'
            for child, parents in conflicts.head(10).items()
        )
        raise RuntimeError(
            'Companies House SIC remapping is ambiguous: one absorbed CH uid '
            f'maps to multiple nonblank spine parents ({sample})'
        )
    match_dict = {
        child: parents[0]
        for child, parents in parent_sets.items()
        if parents
    }

    try:
        ch_data = pd.read_csv(
            ch_file,
            usecols=['uid','SIC','iteration'],
            dtype=str,
            keep_default_na=False,
        )
    except ValueError as e:
        raise RuntimeError(
            f'Error loading Companies House data from {ch_file}: {e}'
        ) from e

    ch_data['uid'] = ch_data['uid'].str.strip()
    ch_data['_row_order'] = range(len(ch_data))
    ch_data['_iteration_rank'] = ch_data['iteration'].map(iteration_rank)
    latest_rank = ch_data.groupby('uid', sort=False)['_iteration_rank'].transform('max')
    latest_rows = ch_data[
        ch_data['uid'].ne('')
        & ch_data['_iteration_rank'].eq(latest_rank)
    ].sort_values('_row_order', kind='stable')

    code_records = []
    for row in latest_rows.to_dict('records'):
        source_uid = row['uid']
        final_uid = match_dict.get(source_uid, source_uid)
        for token_order, code in enumerate(extract_sic_codes(row['SIC'])):
            code_records.append({
                'uid': final_uid,
                'source_uid': source_uid,
                'SIC': code,
                'own_code': source_uid == final_uid,
                'row_order': row['_row_order'],
                'token_order': token_order,
            })

    # Group output by final uid. If that uid is itself a Companies House
    # organisation, its own codes precede codes inherited from absorbed CH
    # partners; source/token order is otherwise retained.
    code_records.sort(key=lambda row: (
        row['uid'],
        not row['own_code'],
        row['row_order'],
        row['source_uid'],
        row['token_order'],
        row['SIC'],
    ))

    seen_pairs = set()
    output_rows = []
    for row in code_records:
        pair = (row['uid'], row['SIC'])
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        output_rows.append({'uid': row['uid'], 'SIC': row['SIC']})

    pd.DataFrame(output_rows, columns=['uid','SIC']).to_csv(ofile,index=False)





