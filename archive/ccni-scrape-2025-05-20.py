#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import certifi
print(certifi.where())


# In[ ]:


# Import packages #

from datetime import datetime as dt
from bs4 import BeautifulSoup as soup
from time import sleep
import requests
import zipfile, io
import os
import argparse
import json
import random
import csv
import re
import pandas as pd

# Test #

def test():
    """
        Function that is used to test whether virtual environment is configured correctly.

        Dependencies:
            - NONE

        Issues:
    """

    print("\r")
    print("Welcome to this data collection script.") 
    print("\r")
    with open("./test.txt", "a") as f:
        f.write("Successfully executed script")


def prelim():
    """
        Get the current date and create a folder to store the download.
    """

    ddate = dt.now().strftime("%Y-%m-%d")
    download = "data/" + ddate
    log = "data/" + ddate + "/log"
    print(download)

    if not os.path.isdir("data"):
        os.mkdir("data")
    else:
        print("Folder already exists")

    if not os.path.isdir(download):
        os.mkdir(download)
    else:
        print("Folder already exists")

    if not os.path.isdir(log):
        os.mkdir(log)
    else:
        print("Folder already exists")    

    return download, log, ddate


# In[ ]:


test()


# In[ ]:


prelim()


# In[ ]:


# Northern Ireland

def ni_roc(basefolder, logfolder, ddate):
    """
        Downloads latest copy of the Register of Charities

        Dependencies:
            - NONE

        Issues: 
    """  

    print("Downloading Northern Ireland Charity Register")
    print("\r")


    # Create data folder

    dfolder = basefolder + "/ni"
    if not os.path.isdir(dfolder):
        os.mkdir(dfolder)
    else:
        print("{} already exists".format(dfolder)) 


    # Define output files

    mfile = logfolder + "/ni-roc-metadata-" + ddate + ".json"
    outfile = dfolder + "/ni-roc-" + ddate + ".csv" # Charity Register


    # Request file from API
    
    webadd = "https://www.charitycommissionni.org.uk/umbraco/api/charityApi/ExportSearchResultsToCsv/?include=Removed"
    response = requests.get(webadd, verify=False)
    print(response.status_code, response.headers)


    # Write metadata to file

    mdata = dict(response.headers)
    mdata["file"] = "Register of Charities"
    mdata["url"] = str(webadd)

    with open(mfile, "w") as f:
        json.dump(mdata, f)


    # Save data file

    if response.status_code==200: # if the web page was successfully requested

        if os.path.isfile(outfile): # do not overwrite existing file
            print("File already exists, no need to overwrite")
        else: # file does not currently exist, therefore create
            with open(outfile, "wb") as f:
                f.write(response.content)
        
        print("\r")    
        print("Successfully downloaded Charity Register")
        print("Check log file for metadata about the download: {}".format(mfile))

    else: # file was not successfully requested
        print("\r")    
        print("Unable to download Charity Register")
        print("Check log file for metadata about the download: {}".format(mfile))


    print("\r")
    print("Charity Register: '{}'".format(outfile))

    return outfile, dfolder


def ni_webpage(regid, webpagefolder, logfolder, ddate):
    """
        Downloads a charity's web page from the CCNI website, which can be parsed at a later date.

        Takes one mandatory argumnent:
            - Registered Charity Number of a charity

        Dependencies:
            - roc_download (for source of charity numbers)

        Issues: 
    """  
    
    
    # Request web page

    session = requests.Session()

    webadd = "https://www.charitycommissionni.org.uk/charity-details/?regId=" + str(regid) + "&subId=0"
    response = session.get(webadd, verify=False)

    
    # Capture metadata

    mdata = dict(response.headers)
    mdata["registered_charity_number"] = str(regid)
    mdata["url"] = str(webadd)
    mfile = logfolder + "/ni-webpages-metadata-" + str(regid) + "-" + ddate + ".json"

    with open(mfile, "w") as f:
        json.dump(mdata, f)
    
    
    # Save web page

    if response.status_code==200:

        outfile = webpagefolder + "/ni-charity-" + str(regid)  + "-" + ddate + ".txt"

        with open(outfile, "w") as f:
            f.write(response.text) 

        print("Downloaded web page of charity: {}".format(regid))    
        print("\r")
        print("Web page file is here: '{}'".format(outfile))

    else:
        print("\r")
        print("Could not download web page of charity: {}".format(regid))


def ni_webpage_from_file(infile, dfolder, logfolder, ddate):
    """
        Takes a file containing Registered Charity Numbers (RCN) for Northern Irish charities and
        downloads a charity's web page from the regulator's website.

        Takes one mandatory and one optional argument:
            - CSV file containing a list of rcns for Northern Irish charities [mandatory]
            - Proportion of charities to download details for; default is all (1.0) [optional]

        Dependencies:
            - webpage_download

        Issues:
            - 
    """

    # Create data folder

    webpagefolder = dfolder + "/webpages"
    if not os.path.isdir(webpagefolder):
        os.mkdir(webpagefolder)
    else:
        print("{} already exists".format(webpagefolder)) 

            
    # Read in data

    df = pd.read_csv(infile, encoding="ISO-8859-1", index_col=False) # import file
    regid_list = df["Reg charity number"].tolist()

    # Request web pages

    for regid in regid_list:
        ni_webpage(regid, webpagefolder, logfolder, ddate)

    print("\r")
    print("Finished downloading web pages for charities in file: {}".format(infile))
    print("Check log files for metadata about the download")

    return webpagefolder


def ni_removed(register, dfolder, webpagefolder, ddate):
    """
        Takes a charity's webpage (.txt file) downloaded from the CCNI website and
        extracts the removal date of deregistered organisations.

        Takes one mandatory argument:
            - A directory with .txt files containing HTML code of a charity's CCNI web page

        Dependencies:
            - webpage_download | webpage_download_from_file 

        Issues:       
    """    

    # Define output file

    rfile = dfolder + "/ni-removals-" + ddate + ".csv"    
    rvarnames = ["regid", "removed", "removed_date"]


    # Write headers to the output files

    with open(rfile, "w", newline="") as f:
        writer = csv.writer(f, rvarnames)
        writer.writerow(rvarnames)

    
    # Get list of removed organisations

    roc = pd.read_csv(register, encoding = "ISO-8859-1", index_col=False)
    removed = roc.loc[roc["Status"]=="Removed"]
    removed_set = set(removed["Reg charity number"])


    # Read data

    for file in os.listdir(webpagefolder):
        if file.endswith(".txt"):
            regid = file[11:17]
            if int(regid) in removed_set:
                f = os.path.join(webpagefolder, file)
                print(regid, f)
                with open(f, "r", encoding = "ISO-8859-1") as f:
                    data = f.read()
                    soup_org = soup(data, "html.parser") # Parse the text as a BS object.
            
                # Locate and extract annual report information
                
                removed = 1
                removed_date_sentence = soup_org.find("div", class_="pcg-charity-details__purpose pcg-charity-details__purpose--removed pcg-contrast__color-main").text
                removed_date_str = removed_date_sentence.replace(" ", "")[-10:].strip()
                #if removed_date_str[0].isalpha():
                #    removed_date_str = "0" + removed_date_str[1:]
                try:
                    removed_date = dt.strptime(removed_date_str, "%d%b%Y").date()
                except:
                    removed_date = ""
                row = regid, removed, removed_date
                with open(rfile, "a", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(row)
                

            else: # charity is not removed from register
                removed = 0
                removed_date = ""
                row = regid, removed, removed_date
                with open(rfile, "a", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(row)    

    print("/r")
    print("Finished extracting removal data from charity web pages found in: {}".format(webpagefolder))


def ni_download(basefolder, logfolder, ddate):
    register, dfolder = ni_roc(basefolder, logfolder, ddate)
    print("Finished downloading Register of Charities")

    webpagefolder = ni_webpage_from_file(register, dfolder, logfolder, ddate)
    print("Finished downloading webpages")

    ni_removed(register, dfolder, webpagefolder, ddate)
    print("Finished extracting information for removed charities")


# In[ ]:


download, log, ddate = prelim()


# In[ ]:


ni_download(download, log, ddate)


# In[ ]:




