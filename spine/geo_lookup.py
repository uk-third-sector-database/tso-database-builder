# ingest geographical information from various sources for postcode lookup

import csv
import pandas

NSPL_data = 'geo_data/NSPL21_AUG_2023_UK/Data/NSPL21_AUG_2023_UK.csv'



def postcode_dict(datafile,postcode_field,fields):

    d={}
    d['FIELDS'] = fields
    print(fields)

    print('loading file ',datafile,' into dictionary format')
    with datafile as csvfile:
        csvreader = csv.DictReader(datafile)
    
        if not postcode_field in csvreader.fieldnames:
            print(f'Error with file {datafile} - cannot find postcode field {postcode_field}')
            return

        for row in csvreader:
            print(row)
            print(row.keys())
            pc = row[postcode_field]
            data = []
            for f in fields:
                print(f,row[f])
                data.append(row[f])
            d[pc] = data

    return d
