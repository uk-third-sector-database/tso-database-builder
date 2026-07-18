

from datetime import datetime

from .base import DataHandler,sort_encoding_issue

exclude_filters = {
    "": []
}

PROVIDER_ID_FIELD = 'CQC Provider ID (for office use only)'


def normalise_company_number(value):
    '''Normalise a Companies House number as reported by the CQC API: strip and
    uppercase; digit-only values lose any excess leading zeros and are then
    zero-padded to 8 characters (the Companies House bulk-file format, so the
    value lines up with GB-COH uids); digit-only values longer than 8 are not
    valid company numbers and are dropped. Alpha-prefixed numbers (SC..., NI...,
    IP..., OC..., ...) are kept as-is.'''
    if not value:
        return ''
    v = str(value).strip().upper()
    if v.isdigit():
        v = v.lstrip('0') or '0'
        return v.zfill(8) if len(v) <= 8 else ''
    return v


class CQCDataHandler(DataHandler):
    fileencoding='UTF8'
    tmp_fields =['iteration','charitynumber']#,'namefield']

    def __init__(self):
        # instance-level copy: compress_org_details removes 'iteration' from the
        # list it is given, and must not mutate the class attribute
        self.tmp_fields = list(type(self).tmp_fields)

    def all_filters(self, row: dict) -> bool:

        # API-derived files carry their header twice (line 1 for this handler,
        # line 5 for handler/preprocess.fix_CQC_files, which skips 4 preamble
        # lines - see acquire/cqc_api.py). The repeated header reaches this
        # handler as a data row whose values equal the column names: drop it.
        if row.get(PROVIDER_ID_FIELD) == PROVIDER_ID_FIELD:
            return False

        # other filters?
        for fieldname, exclude_values in exclude_filters.items():
            if row.get(fieldname) in exclude_values:
                return False
        return True

    def map_date(self, datestr):
        '''API files carry ISO dates (YYYY-MM-DD): convert to the spine's
        dd/mm/yyyy. Anything else (including blank) passes through unchanged.'''
        if not datestr:
            return ''
        try:
            return datetime.strptime(datestr, '%Y-%m-%d').strftime('%d/%m/%Y')
        except ValueError:
            return datestr

    def find_names(self, fieldnames) -> list:
        ''' returns name keys which have non-null values'''
        #
        v = ['Provider name', 'Name', 'Also known as']
        return [i for i in v if i in fieldnames]


    def format_row(self,namefield,row) -> dict:
        '''format a row into Spine format, for given namefield.
        Works for both the old care-directory files (no identifier or date
        columns) and the CQC API files written by acquire/cqc_api.py, which add
        Companies House Number, Charity Number, City and registration dates.'''
        new_row={}

        new_row["uid"] = 'GB-CQC-'+ row[PROVIDER_ID_FIELD]
        new_row["organisationname"] = row[namefield]
        new_row["normalisedname"] = ''
        new_row["fulladdress"] = row['Address']
        new_row["city"] = (row.get('City') or '')
        new_row["postcode"] = row['Postcode']
        new_row["source"] = 'carequalitycommission'
        new_row['source_register'] = 'Care Quality Commission'
        new_row["id_in_source"] = row[PROVIDER_ID_FIELD]
        new_row["registerdate"] = self.map_date(row.get('Registration Date') or '')
        new_row["removeddate"] = self.map_date(row.get('Deregistration Date') or '')
        new_row['companyid'] = normalise_company_number(row.get('Companies House Number') or '')
        new_row['charitynumber'] = (row.get('Charity Number') or '').strip()
        #new_row['namefield'] = namefield
        if namefield == 'Also known as' or namefield == 'Name':
            new_row['iteration'] = '2000' # force AKA names into extra details by giving an early iteration year.
        else:
            new_row['iteration'] = row['Iteration']

        super().sort_address_fields(new_row)
        return new_row


    def find_primary_info(self, details_list):
        return super().find_primary_info(details_list)

    def combine_org_details_per_source(self, rows: list):
        # the base consolidation keeps companyid but knows nothing about
        # charitynumber: carry both through from any constituent row that has
        # them (rows derived from old care-directory files leave them blank)
        result = super().combine_org_details_per_source(rows)
        if not result:
            return result
        new_sub_spine_row, new_extras_rows = result
        for field in ('companyid', 'charitynumber'):
            if not new_sub_spine_row.get(field):
                for r in rows:
                    if r.get(field):
                        new_sub_spine_row[field] = r[field]
                        break
        return new_sub_spine_row, new_extras_rows



'''
CQC care-directory data fields (old download)

Name,
Also known as,
Address,
Postcode,
Phone number,
Service's website (if available),
Service types,
Date of latest check,
Specialisms/services,
Provider name,
Local authority,
Region,
Location URL,
CQC Location ID (for office use only),
CQC Provider ID (for office use only)

CQC API data fields (acquire/cqc_api.py)

CQC Provider ID (for office use only),
Provider name,
Also known as,
Brand ID,
Brand Name,
Ownership Type,
Companies House Number,
Charity Number,
Address,
City,
Postcode,
Local authority,
Region,
Registration Status,
Registration Date,
Deregistration Date,
Iteration
'''
