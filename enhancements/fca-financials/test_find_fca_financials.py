"""Checks for the AR30 section 4.2 extraction (no network, no data files). Snippets are verbatim
from cached sample documents (file named in each test) unless marked "made up"."""
from find_fca_financials import classify, extract_doc, field_tokens, normalise_block, parse_value, year_end_on_form

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


def test_paper_footer_inside_block():  # 7670
    doc = (TITLE + "**2.1 What date did the financial year covered by these accounts end?** 3 0 0 4 2 0 2 1 \n\n"
           "### **4.2 Based on the accounts, please provide the information requested below for the financial year "
           "covered by this return.** \n\n|Number of members|4|\n|---|---|\n|Turnover|16,395|\n\n\nPage **3** of **15** "
           "\n\n_FCA_  Mutuals Annual Return (AR3)  Release 4  February 2019 \n\n|Assets|127,698|\n|---|---|\n"
           "|Number of employees (if any)|1|\n|Share capital|4|\n|Highest rate of interest paid on shares (if any)|0|\n"
           + END)
    row = extract_doc(doc)
    assert row["layout"] == "paper" and row["confidence"] == "review"
    assert row["year_end_on_form"] == "2021-04-30"
    assert row["turnover"] == "16395" and row["assets"] == "127698" and row["number_of_employees"] == "1"


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


def test_ar41_excluded():  # 1097W
    doc = ("###### **Annual Return (AR41) form** \n\n###### **4.2 Based on the accounts, please provide the information "
           "requested below for the financial year covered by this return.** \n\n|**A. Members at end of year**|83|\n")
    assert classify(doc) == "ar41"
    assert extract_doc(doc)["number_of_members"] == "" and extract_doc(doc)["confidence"] == ""


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
