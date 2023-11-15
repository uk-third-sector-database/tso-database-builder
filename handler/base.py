import csv

SPINE_CSV_FORMAT = [
    "uid",
    "organisationname",
    "normalisedname",
    "companyid",
    "charitynumber",
    "housenumber",
    "addressline1",
    "addressline2",
    "addressline3",
    "addressline4",
    "addressline5",
    "city",
    "localauthority",
    "postcode",
    "source",
    "registrationdate",
    "dissolutiondate",
]

NEW_SPINE_CSV_FORMAT = [
    "uid",
    "organisationname",
    "normalisedname",
    "companyid",
    "charitynumber",
    "fulladdress",
    "city",
    "postcode",
    "source",
    "registrationdate",
    "dissolutiondate",
]



FINAL_SPINE_CSV_FORMAT = [
    "rowid",
    "uid",
    "organisationname",
    "normalisedname",
    "companyid",
    "fulladdress",
    "city",
    "postcode",
    "source",
    "registrationdate",
    "dissolutiondate",
]



class DataHandler:
    fileencoding = None
        
    def all_filters(self, row: dict) -> bool:
        raise NotImplementedError()

    def transform_row(self, row: dict) -> list[dict]:
        raise NotImplementedError()
    
    def map_date(self,datestr):
        raise NotImplementedError()
        


def iter_csv_rows(filename,DataHandler):
    encoding=DataHandler.fileencoding
    with open(filename, newline="", encoding=encoding) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            yield row



def do_csv_processing(
    input_csv_filename, output_csv_filename, data_handler: DataHandler
):
    
    processed_rows = 0
    print('Processing file %s .......\n'%input_csv_filename)
    with open(output_csv_filename, "w+", encoding='UTF8', newline="") as csvfile:
        writer = csv.DictWriter(
            csvfile, fieldnames=SPINE_CSV_FORMAT, extrasaction="ignore"
        )
        writer.writeheader()
        for new_row in filter(
            data_handler.all_filters, iter_csv_rows(input_csv_filename,data_handler)
        ):
            print(new_row)
            processed_rows += 1
            writer.writerows(data_handler.transform_row(new_row))

    print(".......... processed, %d lines written to %s\n"%(processed_rows,output_csv_filename))