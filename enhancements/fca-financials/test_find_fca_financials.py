"""Checks for the AR30 extraction (modern 4.2, 2014 2.1) and AR41 (no network, no data files). Snippets are
verbatim from cached sample documents (file named in each test) unless marked "made up"."""
import pandas as pd

from find_fca_financials import (AR41_FIELDS, R3_FIELDS, R3_YEAR_END_Q, classify, extract_doc, field_tokens, fields_by_row,
                                 normalise_block, parse_value, select_target, year_end_on_form)


def fields_2014(block: str) -> dict[str, str]:
    return fields_by_row(block, R3_FIELDS)

TITLE = "# **Annual Return (AR30) form** \n\n"
Q21 = "- 2.1 What date did the financial year covered by these accounts end? \n\n"
HEAD = "4.2 Based on the accounts, please provide the information requested below for the financial year covered by this return. \n\n"
END = "\n\n4.3 What Standard Industrial Classification code best describes the society’s main business? \n"


def values(block: str) -> dict[str, str]:
    return field_tokens(normalise_block(block))


def test_picture_text_br():  # 1912RS
    doc = (TITLE + Q21 + "31/03/2021 \n\n" + HEAD + "<!-- Start of picture text -->\nNumber of members 90<br>"
           "Turnover 9221011<br>Assets 7387726<br>Number of Employees 9<br>Share Capital 90<br>Highest rate of "
           "interest 0<br>paid on shares<br><!-- End of picture text -->" + END)
    row = extract_doc(doc)
    assert row["form_type"] == "ar30_modern" and row["layout"] == "online" and row["confidence"] == "high"
    assert row["year_end_on_form"] == "2021-03-31"
    assert [row[f] for f in ("number_of_members", "turnover", "assets", "number_of_employees", "share_capital",
                             "highest_rate_interest_paid_on_shares")] == ["90", "9221011", "7387726", "9", "90", "0"]


def test_bold_inline():  # 4475R
    v = values("**Number of members** 4243 **Turnover** 469,000 **Assets** 30,266,000 **Number of Employees** 5 "
               "**Share Capital** 4,000 **Highest rate of interest** 0 **paid on shares** ")
    assert v["assets"] == "30,266,000" and v["share_capital"] == "4,000"
    assert v["highest_rate_interest_paid_on_shares"] == "0"


def test_two_column_table():  # 7295
    v = values("|**Number of members**|223|\n|---|---|\n|**Turnover**|317,468|\n|**Assets**|284,088|\n"
               "|**Number of Employees**|9|\n|**Share Capital**|270,000|\n"
               "|**Highest rate of interest** **paid on shares**|0|\n")
    assert v["number_of_members"] == "223" and v["share_capital"] == "270,000"
    assert v["highest_rate_interest_paid_on_shares"] == "0"


def test_label_then_value_lines():  # 7527
    v = values("## **4.2 Based...** \n\n**Number of members** \n\n5 \n\n**Turnover** \n\n0 \n\n**Assets** \n\n0 \n\n"
               "**Number of Employees** \n\n0 \n\n**Share Capital** \n\n0 \n\n"
               "## **Highest rate of interest paid on shares** \n\n0 \n\n")
    assert v == {"number_of_members": "5", "turnover": "0", "assets": "0", "number_of_employees": "0",
                 "share_capital": "0", "highest_rate_interest_paid_on_shares": "0"}


def test_single_column_table():  # 7736
    v = values("|---|\n|**Number of members** 114|\n|**Turnover** 93,724|\n|**Assets** 18,941|\n"
               "|**Number of Employees** 2|\n|**Share Capital** 18,940|\n|**Highest rate of interest** **paid on shares** 0|\n")
    assert v["turnover"] == "93,724" and v["highest_rate_interest_paid_on_shares"] == "0"


def test_rate_label_split_around_value():  # 4442
    v = values("Share Capital 0<br>Highest rate of interest paid 0<br>on shares<br>")
    assert v["highest_rate_interest_paid_on_shares"] == "0"


def test_stacked_labels():  # 6365R
    v = values("## **Number of members** \n\n34 \n\n**Turnover** \n\n987 \n\n## **Assets** \n\n"
               "## **Number of Employees** \n\n12741 0 \n\n## **Share Capital** \n\n"
               "**Highest rate of interest paid on shares** \n\n402 0 \n\n")
    assert v == {"number_of_members": "34", "turnover": "987", "assets": "12741", "number_of_employees": "0",
                 "share_capital": "402", "highest_rate_interest_paid_on_shares": "0"}


def test_filled_form_footer_inside_block():  # 7670: tick box, footer splits the table
    doc = (TITLE + "**2.1 What date did the financial year covered by these accounts end?** 3 0 0 4 2 0 2 1 \n\n"
           "All directors are aged 16 or over `☒` \n\n"
           "### **4.2 Based on the accounts, please provide the information requested below for the financial year "
           "covered by this return.** \n\n|Number of members|4|\n|---|---|\n|Turnover|16,395|\n\n\nPage **3** of **15** "
           "\n\n_FCA_  Mutuals Annual Return (AR3)  Release 4  February 2019 \n\n|Assets|127,698|\n|---|---|\n"
           "|Number of employees (if any)|1|\n|Share capital|4|\n|Highest rate of interest paid on shares (if any)|0|\n"
           + END)
    row = extract_doc(doc)
    assert row["layout"] == "filled" and row["confidence"] == "high"
    assert row["year_end_on_form"] == "2021-04-30"
    assert row["turnover"] == "16395" and row["assets"] == "127698" and row["number_of_employees"] == "1"


def test_scanned_form():  # 7251R: OCR bullets ("- e this form") and footer ("FCA @ Mutuals")
    doc = ("## Annual Return (AR30) form \n\n- e this form; \n\n###### 4.2 Based on the accounts, please provide the "
           "information requested below for the financial year covered by this return. \n\n"
           "|Number of members |219 |\n|---|---|\n|Numberofemployees(ifany)|Ce|\n"
           "| Highestrateof interestpaidonshares(ifany)|oo|\n\n\n"
           "FCA @ Mutuals Annual Return (AR3) @ Release 4 @ February 2019 Page 3 of 12 \n\n"
           "4.3 What Standard Industrial Classification code best describes the society’s main business? ")
    row = extract_doc(doc)
    assert row["layout"] == "scanned" and row["confidence"] == "review"
    assert row["number_of_members"] == "219" and row["highest_rate_interest_paid_on_shares_status"] == "review"


def test_ocr_joined_labels():  # 7251R
    v = values("|Number of members |219 |\n|---|---|\n|Numberofemployees(ifany)|Ce|\n"
               "| Highestrateof interestpaidonshares(ifany)|oo|\n")
    assert v == {"number_of_members": "219", "number_of_employees": "Ce", "highest_rate_interest_paid_on_shares": "oo"}


def test_filled_pdf_values():  # 5106R
    v = values("|Turnover|**£125,892**|\n|Share capital|**£70**|\n|Highest rate of interest paid on shares (if any)|**N/A**|\n")
    assert v["turnover"] == "£125,892" and v["highest_rate_interest_paid_on_shares"] == "N/A"
    assert parse_value(v["turnover"], "GBP", False) == ("125892", "parsed")
    assert parse_value(v["highest_rate_interest_paid_on_shares"], "percent", False) == ("-9", "not_applicable")


def test_first_block_only():  # 4253R: online copy, then a scanned copy with a paper footer
    doc = (TITLE + Q21 + "31/12/2023 \n\n" + HEAD + "Number of members 39<br>Turnover 30523<br>Assets 376958<br>"
           "Number of Employees 3<br>Share Capital 16<br>Highest rate of interest 0<br>paid on shares<br>" + END
           + "FCA @ Mutuals Annual Return (AR3) @ Release 5 @ February 2023 \n" + HEAD + "Number of members 99" + END)
    row = extract_doc(doc)
    assert row["layout"] == "online" and row["number_of_members"] == "39" and row["confidence"] == "high"


def test_ar41_not_modern():  # 1097W
    doc = ("###### **Annual Return (AR41) form** \n\n###### **4.2 Based on the accounts, please provide the information "
           "requested below for the financial year covered by this return.** \n\n|**A. Members at end of year**|83|\n")
    assert classify(doc) == "ar41"


def test_other_forms():  # 2382RS, 4SA, 89CU, 1003F
    assert classify("2 Statistics \n- 4.2 Has your society produced accounts to the minimum "
                    "standard required? ") == "ar30_2014"
    assert classify("## FORM A. R. 5A PUBLIC RECORD ") == "ar5"
    assert classify("# **Credit Union Accounts form** ") == "credit_union"
    assert classify("CONTINUOUS DATAPRINT ; FRIENDLY SOCIETY \n\n(Number 1003F) ") == "other"


def test_year_end_variants():
    assert year_end_on_form(Q21 + "31/03/2021 \n") == "2021-03-31"  # 1912RS
    assert year_end_on_form(Q21 + "|29/02/2024|\n|---|\n") == "2024-02-29"  # 8287
    assert year_end_on_form("#### **2.1 What date did the financial year covered by these accounts end?** \n\n"
                            "3 1 1 2 2 0 2 1 \n\n## **Section 3") == "2021-12-31"  # 5106R
    assert year_end_on_form("2.1 What date did the financial year covered by these accounts end? 2 fofais| ") == ""  # 4253R
    assert year_end_on_form("###### 2.4 What date did the financial year covered by these accounts end? \n\n\" ") == ""  # 4881


def test_value_rules():
    assert parse_value("NA", "percent", True) == ("-9", "not_applicable")
    assert parse_value("NONE", "count", True) == ("0", "nil")
    assert parse_value("7647400000", "GBP", True) == ("7647400000", "parsed")
    assert parse_value("10003.22", "GBP", True) == ("10003.22", "parsed")
    assert parse_value("O", "GBP", True) == ("0", "nil")
    assert parse_value("oO", "GBP", False) == ("", "review")
    assert parse_value("£64, 205)", "GBP", False) == ("", "review")
    assert parse_value("Lite", "GBP", False) == ("", "review")
    assert parse_value("1.5", "count", True) == ("", "review")
    assert parse_value("10.123", "GBP", True) == ("", "review")
    assert parse_value("150", "percent", True) == ("", "review")
    assert parse_value("", "GBP", True) == ("", "missing")


def test_scanned_block_and_split_value():  # 5420R: the labels before employees were lost to OCR
    v = values("below for the financial year covered by this return. \n\n£64, 205) \n\n|Number of employees (if any) |\n"
               "|---|\n|Highestrateof interestpaidonshares(ifany)Pe|\n")
    assert v == {"highest_rate_interest_paid_on_shares": "Pe"}
    assert values("Assets £64, 205) ") == {"assets": "£64, 205)"}  # made up: same value under a label


def test_select_target():  # made up: cached rows first, then baseline matches, then a seeded random fill
    cat = pd.DataFrame({"doc_id": list("abcdef"), "matches_baseline": [False, True, False, True, False, False]})
    sel = select_target(cat, [False, False, True, True, False, False], 4)
    assert list(sel["doc_id"][:3]) == ["c", "d", "b"]
    assert list(sel["selected_as"]) == ["cached", "cached", "baseline", "random"]
    assert sel["doc_id"].iloc[3] in {"a", "e", "f"}


def test_label_repeated_after_values():  # 1284RS
    doc = (TITLE + HEAD + "<!-- Start of picture text -->\nNumber of members 13<br>Turnover 23516<br>Assets 622771<br>"
           "Number of Employees 0<br>Share Capital 67<br>Highest rate of interest 0<br><!-- End of picture text -->\n"
           "**Highest rate of interest paid on shares** " + END)
    row = extract_doc(doc)
    assert row["highest_rate_interest_paid_on_shares_raw"] == "0" and row["confidence"] == "high"
    assert all(row[f"{f}_status"] == "parsed" for f in ("number_of_members", "turnover", "assets", "number_of_employees",
                                                         "share_capital", "highest_rate_interest_paid_on_shares"))


def test_garbled_title():  # 4398
    assert classify("# Annual Return (AR3SOQ) form \n\n" + HEAD) == "ar30_modern"


def test_doc_id_and_watermark_stripped():  # 2785RS hash; 1086W watermark
    v = values("Share Capital 0 Demo Version Select.Pdf SDK Highest rate of interest paid on shares (if any) "
               "4.5% Doc ID: 04 b8ac85d0fad350d515f2c5bb5c8eb3c32ec40f")
    assert parse_value(v["share_capital"], "GBP", False) == ("0", "parsed")
    assert parse_value(v["highest_rate_interest_paid_on_shares"], "percent", False) == ("4.5", "parsed")


def test_word_and_letter_zero():
    assert parse_value("Zero", "count", True) == ("0", "nil")
    assert parse_value("zero", "percent", True) == ("0", "nil")
    assert parse_value("O%", "percent", True) == ("0", "nil")
    assert parse_value("Zero", "count", False) == ("", "review")  # scanned


# ---------- older AR30 (Release 3, July 2014) ----------
R3_FOOT = "_FCA_  Mutuals AR 30 – registered societies (F)  Release 3  July 2014 \n\n"  # 7115


def test_2014_form_7115():  # 7115 (2021): clean table; blank J, NIL share capital
    doc = (R3_FOOT + "###### **1.2 Year end date (dd/mm/yyyy)** \n\nSee Note 1.2 \n\n|3 1 / 1 2 / 2 0 2 1|\n|---|\n\n\n"
           + R3_FOOT + "###### **2.1 You must enter the figures below** \n\n"
           "See notes for help on items E-T. Enter NIL where applicable \n\n"
           "|A|Members at beginning of year|113|\n|---|---|---|\n|B|Members ceased during year|2|\n"
           "|C|Members admitted during year|1|\n|D|Members at end of year|112|\n|E|Turnover for year|667.04|\n"
           "|F|Total of income and expenditure (receipts and payments added together)|1239.98|\n"
           "|G|Net surplus/(deficit) for year|94.10|\n|H|Fixed assets||\n|I|Current assets|94.10|\n"
           "|J|Total assets (equal to amount in row O,below)||\n|K|Current liabilities||\n|L|Share capital|nil|\n"
           "|M|Long-term liabilities||\n|N|Reserves|nil|\n"
           "|O|Total liabilities, share capital & reserves (K+L+M+N) (equal to amount in J above)||\n\n\n"
           + R3_FOOT + "- **2.2 Names of subsidiaries as defined in sections 100 and 101 of the Co-operative and "
           "Community Benefit Societies Act 2014** \n")
    row = extract_doc(doc)
    assert row["form_type"] == "ar30_2014" and row["layout"] == "scanned" and row["confidence"] == "review"
    assert row["year_end_on_form"] == "2021-12-31"
    assert (row["number_of_members"], row["number_of_members_status"]) == ("112", "parsed")
    assert (row["turnover"], row["turnover_status"]) == ("667.04", "parsed")
    assert (row["assets"], row["assets_status"]) == ("", "missing")
    assert (row["share_capital"], row["share_capital_status"]) == ("0", "nil")
    assert row["number_of_employees"] == "" and row["number_of_employees_status"] == "not_on_form"
    assert row["highest_rate_interest_paid_on_shares_status"] == "not_on_form"


def test_2014_row_o_not_share_capital():  # 1228RS: L row lost to OCR, only row O mentions share capital
    v = fields_2014("|J|Total assets (equal toamount in row O, below)|55,382,257|\n||Current liabilities|6,809,224|\n"
                    "||Long-term liabilities|20,388,781|\n"
                    "||Total liabilities, share capital & reserves(K+L+M+N) (equal to amount in J above|55,382,257 i :|\n")
    assert v == {"assets": "55,382,257"}


def test_2014_picture_text():  # 4161: rows split at <br>; value inside the J label's bracket
    v = fields_2014("Members at beginning of year 1072<br>D- Members at end of year 1163<br>J Total assets (equal to "
                    "amount in 17139<br>row O, below)<br>Current liabilities 11077<br>Share capital 1163<br>"
                    "Total liabilities, share capital &<br>reserves (K+L+M+N) (equal to 17139<br>amount in J above)<br>")
    assert v == {"number_of_members": "1163", "assets": "17139", "share_capital": "1163"}


def test_2014_repeated_label_and_two_rows():  # 405IP repeats the label in one row; made up: two rows -> review
    assert fields_2014("|[>|[Members atendofyear | Members atend ofyear|6|\n") == {"number_of_members": "6"}
    v = fields_2014("|E|Turnover for year|10|\n|E|Turnover for year|12|\n")
    assert parse_value(v["turnover"], "GBP", True) == ("", "review")


def test_2014_year_end():
    assert year_end_on_form("###### **1.2 Year end date (dd/mm/yyyy)** \n\nSee Note 1.2 \n\n|3 1 / 0|3 /| 2 0 1 8|\n",
                            R3_YEAR_END_Q) == "2018-03-31"  # 7381
    assert year_end_on_form("1.2 Year end date (dd/mm/yyyy)** See Note 1.2 \n\n\n<!-- Start of picture text -->\n"
                            "3 0 6 2 0 1 8<br>/ 0 /<br><!-- End of picture text -->", R3_YEAR_END_Q) == ""  # 2757RS
    assert year_end_on_form("1.2 Year end date (dd/mmlyyyy) \n\nSee Note 1.2 \n\n#### | i|2]o|1|e | \n",
                            R3_YEAR_END_Q) == ""  # 1410RS


def test_2014_garbled_classification():
    assert classify("- 4,2 Has your society produced accounts to the minimum standard required? ") == "ar30_2014"  # 1159R
    assert classify("_FCA_ l Mutuals AR 30 – registered societies (F) l Release 3 l July 2014 ") == "ar30_2014"  # 7192


def test_modern_footer_and_garbled_block_start():  # 122IP: title page lost; 8232: "4,2 Based"
    assert classify("2 FCA @ Mutuals Annual Return (AR3) @ Release 4 @ February 2019 \n\n"
                    "4.2 Based on the accounts, please provide the information") == "ar30_modern"
    assert classify("## Annual Return (AR3O) form \n\n4,2 Based on the accounts, please provide the information "
                    "requested below") == "ar30_modern"


def test_ar41_with_space():  # 422W
    assert classify("FCA e Mutuals AR 41 Working Men's Club (F) e Release 1 April 2013 ") == "ar41"


# ---------- AR41 (working men's clubs) ----------
A41_TITLE = "# **Annual Return (AR41) form** \n\n"
A41_ONLINE_HEAD = HEAD + "Please do not leave any fields blank. Enter ‘0’ where applicable. \n\n"
A41_END = "\n\n- 5.1 Please select the audit option the society has complied with: \n"
FOUR = ("number_of_members", "turnover", "assets", "number_of_employees")


def test_ar41_online_sequence():  # 1001W (2022): labels apart from the values; "(if any)" does not make it paper
    doc = (A41_TITLE + Q21 + "01/01/2022 \n\n" + A41_ONLINE_HEAD + "**A. Members at end of year** \n\n192 \n\n"
           "**B. Turnover for year** \n\n## **C. Total income and expenditure (receipts and payments added together)** "
           "\n\n123594 254634 \n\n**D. Net surplus/(deficit) for year E. Fixed assets F. Current assets** \n\n"
           "**G. Total assets (E+F) (equal to amount in K below) H. Current liabilities I. Loans J. Reserves "
           "K. Total liabilities (H+I+J) (equal to amount in G above) L. Number of employees (if any)** \n\n"
           "7446 74603 22853 97456 10388 0 87068 97456 \n\n4 " + A41_END)
    row = extract_doc(doc)
    assert (row["form_type"], row["layout"], row["ar41_totals_check"], row["confidence"]) == ("ar41", "online", "pass", "high")
    assert row["year_end_on_form"] == "2022-01-01"
    assert [row[f] for f in FOUR] == ["192", "123594", "97456", "4"]
    assert row["share_capital_status"] == row["highest_rate_interest_paid_on_shares_status"] == "not_on_form"


def test_ar41_online_picture_text_duplicate():  # 1097W (2018): picture text repeats the members value
    doc = (A41_TITLE + "###### **4.2 Based on the accounts, please provide the information requested below for the "
           "financial year covered by this return.** \n\nPlease do not leave any fields blank. Enter ‘0’ where applicable. "
           "\n\n\n<!-- Start of picture text -->\n102<br><!-- End of picture text -->\n\n"
           "|**A. Members at end of year**|102|\n|---|---|\n|**B. Turnover for year**|23303|\n"
           "|**C. Total income and** **expenditure (receipts and** **payments added together)**|33934|\n"
           "|**D. Net surplus/(deficit) for** **year**|1533|\n|**E. Fixed assets**|39659|\n|**F. Current assets**|17982|\n"
           "|**G. Total assets (E+F) (equal to** **amount in K below)**|57641|\n|**H. Current liabilities**|552|\n"
           "|**I. Loans**|0|\n|**J. Reserves**|57089|\n|**K. Total liabilities (H+I+J)** **(equal to amount in G above)**|57641|\n"
           "|**L. Number of employees (if** **any)**|0|" + A41_END)
    row = extract_doc(doc)
    assert row["ar41_totals_check"] == "pass" and row["confidence"] == "high"
    assert [row[f] for f in FOUR] == ["102", "23303", "57641", "0"]


def test_ar41_online_totals_fail():  # 1008W (2019): G 703991 but K 704021, so rows are read by label, not high
    doc = (A41_TITLE + A41_ONLINE_HEAD + "|**A. Members at end of year**|362|\n|---|---|\n|**B. Turnover for year**|174848|\n"
           "|**C. Total income and** **expenditure (receipts and** **payments added together)**|102162|\n"
           "|**D. Net surplus/(deficit)** **for year**|17178|\n|**E. Fixed assets**|626024|\n|**F. Current assets**|77967|\n"
           "|**G. Total assets (E+F)** **(equal to amount in K** **below)**|703991|\n|**H. Current liabilities**|23495|\n"
           "|**I. Loans**|30963|\n|**J. Reserves**|649563|\n"
           "|**K. Total liabilities (H+I+J)** **(equal to amount in G** **above)**|704021|\n"
           "|**L. Number of employees** **(if any)**|5|" + A41_END)
    row = extract_doc(doc)
    assert (row["layout"], row["ar41_totals_check"], row["confidence"]) == ("online", "fail", "review")
    assert [row[f] for f in FOUR] == ["362", "174848", "703991", "5"]


def test_ar41_value_under_label():  # 1096W (2019): online value on the line after its label
    assert fields_by_row("**A. Members at end of year** \n\n322 \n\n**B. Turnover for year** 153697 \n\n"
                         "## **C. Total income and expenditure (receipts and payments added together)** \n\n322,194 \n\n",
                         AR41_FIELDS) == {"number_of_members": "322", "turnover": "153697"}


def test_ar41_release2_filled():  # 1038W (2018): Release 2 paper form typed into (tick boxes)
    doc = (A41_TITLE + "### **2.1 What date did the financial year covered by these accounts end?** \n\n\n"
           "<!-- Start of picture text -->\n3  1  1  2  2  0  1  8<br><!-- End of picture text -->\n\n"
           "|accounts are being submitted with this form; and|`☒`|\n|---|---|\n\n"
           "### **4.2 Based on the accounts, please provide the information requested** \n\n**below for the financial year "
           "covered by this return.** Please do not leave any fields blank. Enter ‘NIL’ where applicable. \n\n"
           "|A|Members at end of year|325|\n|---|---|---|\n|B|Turnover for year|£175,797|\n"
           "|C|Total income and expenditure (receipts and payments added together)|£352.735|\n"
           "|D|Net surplus/(deficit) for year|£(1,141)|\n|E|Fixed assets|£75,153|\n|F|Current assets|£8,519|\n"
           "|G|Total assets (E+F) (equal to amount in K below)|£83,672|\n|H|Current liabilities|£13,368|\n|I|Loans|£100|\n"
           "|J|Reserves|£70,204|\n|K|Total liabilities (H+I+J) (equal to amount in G above)|£83,672|\n"
           "|L|Number of employees (if any)|5|\n\n\n_FCA_ ⚫ Mutuals AR41 Working Men’s Club (F) ⚫ Release 2 ⚫ February 2019 "
           "\n\nPage **4** of **7** \n\n## **Section 5 – Audit** \n")
    row = extract_doc(doc)
    assert (row["layout"], row["ar41_totals_check"], row["confidence"]) == ("filled", "", "high")
    assert row["year_end_on_form"] == "2018-12-31"
    assert [row[f] for f in FOUR] == ["325", "175797", "83672", "5"]


def test_ar41_release1_scanned():  # 1004W (2018): Release 1, no employees row; OCR footer bullet "e"
    doc = ("FCA e Mutuals AR 41 Working Men's Club (F) e Release 1 e April 2013 \n\n- 1.2 Year end date \n\n"
           "Please enter year below \n\n\n<!-- Start of picture text -->\ni{2{o|r|s.<br><!-- End of picture text -->\n\n"
           "- 2.1 You must enter the figures below \n\n###### Enter NIL where applicable \n\n"
           "||Members at end ofyear|1586|\n|---|---|---|\n"
           "|C |Total ofincome and expenditure |(receipts and payments added together |£N/A |\n"
           "|Dp||Netsurplus/(deficit) foryear|£(27826)|\n|G|Total assets (E+F) (equal to amount in Kbelow)|£621646|\n"
           "||Current liabilities|£ 96722|\n|K|Total liabilities (H+I+J) (equal to amountinGabove)|£621646|\n\n\nee \n\n"
           "FCA e Mutuals AR 41 Working Men's Club (F) e Release 1 e April 2013 \n\npage 6 \n\n3 The audit ")
    row = extract_doc(doc)
    assert (row["form_type"], row["layout"], row["confidence"], row["year_end_on_form"]) == ("ar41", "scanned", "review", "")
    assert (row["number_of_members"], row["assets"]) == ("1586", "621646")
    assert row["turnover_status"] == "missing" and row["number_of_employees_status"] == "not_on_form"


def test_ar41_row_c_is_not_turnover():  # 2587W (2020) Release 1: of rows B/C only C survives OCR; 1038W row C
    v = fields_by_row("|C_ |Total ofincomeand expenditure |(receipts and payments added together |£ 135666 |\n|---|---|---|\n"
                      "|D|oNetsurplus/(deficit)foryear|£(2,230)|\n|G|Total assets(E+F)(equal to amount in K below|£ 157042|\n",
                      AR41_FIELDS)
    assert v == {"assets": "£ 157042"}
    assert fields_by_row("|C|Total income and expenditure (receipts and payments added together)|£352.735|\n",
                         AR41_FIELDS) == {}


def test_ar41_paper_without_footer_is_scanned():  # 1023W (2022): "Enter 'NIL'" and no footer survived OCR
    doc = ("## Annual Return (AR41) form \n\n4.2 Based on the accounts, please provide the information requested below for "
           "the financial year covered by this return. Please do not leave any fields blank. Enter ‘NIL’ where applicable. "
           "\n\n|peewee gta|\n|---|\n|[2|netsumrenanieryer—«(E2URSS |\n| Pefmwiens«0|\n\n\n##### Section 5 — ")
    row = extract_doc(doc)
    assert (row["layout"], row["confidence"], row["number_of_members_status"]) == ("scanned", "review", "missing")


def test_box_border_read_as_one():  # "1£179,522" in AR41 paper tables
    assert parse_value("1£179,522", "GBP", False) == ("", "review")
