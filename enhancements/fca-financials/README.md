# FCA society financials from annual returns (AR30, AR41)

Standalone enhancement (not part of the builder). Reads the six figures in **section 4.2** of the
modern FCA annual return (AR30) for co-operative and community benefit societies (`GB-MPR-`
uids), four of the same figures from **section 2.1** of the older AR30 (Release 3, July 2014),
four from the working men's club return (**AR41**), six rows of the credit union annual return
(**CY**), plus the financial year-end written on the form, from the Braw corpus API's text of each
return.
Regex only: no PDFs, no language model. Every return per society is kept (a panel).

## Run

    python find_fca_financials.py --limit 50              # trial: fetch + extract a reproducible sample
    python find_fca_financials.py --limit 50 --no-fetch   # re-extract the sample from the cache only
    python find_fca_financials.py --target 3000           # 3,000 in total: cached, baseline, random
    python find_fca_financials.py                         # full run (~1 request/1.05s; resumable)

Inputs and defaults:

- `--api-keys` braw-charity-accounts-api/.api-keys.local.json ("prod" key), not needed with `--no-fetch`.
- `--min-year 2018` first catalogue year. `--work-dir ./work`, `--out-dir ./output`.
- `--no-fetch` extracts from whatever is cached for the selected rows and skips the rest (needs
  `work/catalogue_gb_mpr.csv` already cached).
- `--baseline-dir` the PDF pipeline's v4 build audit (default
  `D:\fca-annual-reports\archive\v4-baseline-20260727\build-audit-20260727`). The comparison runs
  whenever the folder exists and is skipped otherwise.
- `--target N` (instead of `--limit`) selects N catalogue rows in total, in this order: every row
  already cached in `work/docs/`; then rows whose society number and year end match a baseline
  modern, releasable return (skipped if the baseline folder is absent); then a seeded random fill.
  The cached rows are not a random set (partly catalogue order), so analyse `selected_as ==
  "random"` on its own when a random sample is needed.

Caches in `work/`: `catalogue_gb_mpr.csv` (delete to refresh), `docs/{number}_{yearend}.md`
(one per return), `fetch_failures.csv` (retried on the next run).

Tests: `pytest test_find_fca_financials.py`.

## Forms

Each document is classified; `ar30_modern`, `ar30_2014`, `ar41` and `cu_cy_return` are
extracted, `credit_union` gives the year-end only, the rest are counted. Checked in this order:

- `ar30_modern`: title "Annual Return (AR30) form" (OCR `AR3O`, `AR30O`, and "(AR30O) for" with
  the "m" lost, accepted) or, when OCR lost the title page, the paper page footer "Mutuals Annual
  Return (AR3) ... Release N"; and "4.2 Based on the accounts" (OCR `4,2`, `4:2`, `Basedon`,
  `@Ccounts`, every word doubled as in 7404 accepted) or, when OCR lost that heading, "Section 4 -
  Financial information" (the block then starts there, 4681R) or "4.3 What Standard" (no block:
  all fields `missing`, e.g. 4406, 8272R); and no mention of AR41 (`AR41` or `AR 41`).
- `ar30_2014`: the older AR30, Release 3, July 2014 ("4.2 Has your society ...", OCR `4,2`
  accepted, or the page footer "AR 30 – registered societies (F) Release 3 July 2014"; the footer
  catches returns whose "4.2" is garbled, e.g. 4161, 7192).
- `ar41` (`AR41` or `AR 41`).
- `ar5`: the Friendly Societies Act 1974 return of specially authorised and benevolent societies
  (`A.R.5` / `A. R. 5A`, OCR `FORM AR.5`, `FORM AR.S`, `FORM ARS`, `FORMARS`; or, when the form
  number is lost, the printed header "a SPECIALLY AUTHORISED SOCIETY"). Classification only:
  nothing is extracted.
- `cu_cy_return`: "Annual return (CY) for credit unions" (not the "Annual return (CY) - Auditor's
  statement").
- `credit_union`: "credit union" in the first 3,000 characters (the cover page; usually the
  "Credit Union Accounts form"). Building and friendly societies that mention a credit union only
  deeper in their accounts (108B, 355B, 159B, 11BNI, 218F, 223F) are `other`.
- `other`.

## Credit unions

**Annual return (CY).** Each row reads "label | value | row code" (e.g. `||Total assets||4,225,676|C16|`).
A field's value is the number written just before its row code; scans may glue the code to the
value (`5,981,493.01C16`), and if OCR misread the code (`Att` for A11) the number right after the
row's label is used instead. When a document holds a web-form copy (bold "**Return Details:**"
header) that copy is read, and `layout` is `online`; otherwise the first copy is read and `layout`
is `scanned` (scanned printouts of the web form, and the 2018 spreadsheet template, e.g. 182C).
Year-end from "Return End Date: dd/mm/yyyy" when present, else blank.

| Output field | CY row | Meaning |
|---|---|---|
| `number_of_members` | A2 "Number of members at the financial year end" | count |
| `number_of_employees` | A11 "Total number of staff" | count |
| `assets` | C16 "Total assets" | £ |
| `turnover` | J13 "Total income" | £; total income, not a sales figure |
| `share_capital` | G1 "Members' share balances (total)" | £; members' savings, which a credit union holds as withdrawable share capital |
| `highest_rate_interest_paid_on_shares` | L5 "Rate of dividend" | %; the dividend rate paid on shares, not an interest rate |

`cu_totals_check` uses the return's own sums: C16 - D12 = E1 (total assets less total liabilities
= net assets) and J13 - K18 = L1 (total income less total expenditure = profit before tax), each
tested only when all three figures read. `pass` if every tested sum holds exactly, `fail` if one
does not, blank if neither can be read. Confidence is `high` only for `online` returns with
`pass` and every field `parsed`/`nil`; everything else is `review`. A dividend rate under 1
written without `%` (e.g. `0.5`, `0.01`) goes to `review` under the general value rules, as it
could be a fraction or a percentage.

**Credit union accounts form.** The cover page asks only "1. On what date did the financial year
in these accounts end?"; that date fills `year_end_on_form`. The form asks for no figures (the
accounts are attached), so all six fields are `not_on_form` and `confidence` is blank. Figures in
the attached accounts are not read.

Layout, judged on the text up to the end of the first block (4.2 on the modern form, 2.1 on the
2014 form):

- `online`: the web form (no "(if any)" labels and no paper page footer
  "Mutuals Annual Return (AR3) ... Release N" or "Release 3 July 2014"). The 2014 form is paper
  only, so it is never `online`.
- `filled`: the PDF form typed into on a computer. Its tick boxes come through as `☒`/`☐`, and
  none of the OCR signs below appear.
- `scanned`: a paper form read by OCR (text recognition from an image). Signs: page-1 bullets read
  as `- e this form`, the footer bullet read as `@`, `®`, `©` or `e` (`FCA @ Mutuals ...`), or
  `fca.org.uk` read as `fca.orq.uk`. A paper form with neither tick boxes nor OCR signs is also
  treated as scanned.

On the 91 paper returns cached on 12 Oct 2026 the two signs never overlapped: 14 filled (tick
boxes, no OCR signs; e.g. 5106R, 7550, 7670), 73 scanned by bullets/footer and 4 (2025 returns
from a newer OCR, e.g. 1040RS) by `fca.orq.uk` alone; none fell to the default.

AR41 uses its own signs (the AR30 ones do not fit: the web form also says "(if any)"):

- `online`: no paper footer "Mutuals AR41 Working Men's Club (F) ... Release N" (OCR `AR 41`,
  `AR 44`, `Workina` accepted) and the web form's guidance "Enter '0' where applicable" (paper
  forms say "Enter 'NIL'"). The title "Annual Return (AR41) form" is not used: Release 2/3 paper
  forms carry it too (1023W).
- `filled`: the paper footer, tick boxes and no OCR signs (e.g. 1038W).
- `scanned`: everything else, including paper forms whose footer was lost to OCR.

Grepping the 575 AR41 returns in the 3,000-document set gives 221 online, 9 filled and 345
scanned (228 of them Release 1). Some online returns are followed by a paper copy (831W, 1334W);
as for AR30, only the text up to the end of the first block counts.

## Method

The block runs from the first "4.2 Based on the accounts" to the next "4.3 What Standard"
(capped at 3,000 characters if that is missing). Markup, page footers and "Page N of N" are
removed, then each label is found in form order and its value is the text up to the next label.
Labels printed one under another with the values after them (e.g. 6365R) are filled in order.
A label whose table row ends in an empty cell (`|Number of employees (if any)||`) with nothing
before the next label is blank on the form and never takes the next row's value (829RS 2022 had
given employees the share capital, 48,800).

**2014 form.** The block runs from "2.1 You must enter the figures below" (or "2 Statistics" if
that is lost) to "2.2 Names of subsidiaries" (capped at 3,000 characters). Its lettered rows A-T
are split into lines (table rows, or picture-text lines at `<br>`); for each field below the row
is found by its label and the value is the rest of that row. The year-end comes from "1.2 Year end
date (dd/mm/yyyy)", written in boxes as `3 1 / 1 2 / 2 0 2 1`; anything else gives a blank.

| Output field | 2014 form row | Unit |
|---|---|---|
| `number_of_members` | D "Members at end of year" | count |
| `turnover` | E "Turnover for year" | £ |
| `assets` | J "Total assets (equal to amount in row O, below)" | £ |
| `share_capital` | L "Share capital" | £ |
| `number_of_employees` | not asked: blank, status `not_on_form` | |
| `highest_rate_interest_paid_on_shares` | not asked: blank, status `not_on_form` | |

Row O ("Total liabilities, share capital & reserves") is never read as share capital: a "share
capital" preceded by a comma or followed by "&" is skipped. A label found on more than one row
sends the field to `review`; a label not found gives `missing`. If a label's row holds no value,
the next line with text is used when it contains no letters (a value printed under its label).

**AR41 (working men's clubs).** Lettered rows A-L, of which four feed the output fields; no new
columns are added. Three versions:

- Release 2 (February 2019) and Release 3 (April 2024) paper forms, and the online web form: rows
  A-L under "4.2 Based on the accounts", ending at "5.1 Please select the audit option" or
  "Section 5". Year-end from "2.1 What date did the financial year ... end?" as for modern AR30.
- Release 1 (April 2013) paper form: rows A-K (no employees row) under "2.1 You must enter the
  figures below", ending at "3 The audit" / "3.1 Type of audit". Used when there is no 4.2 block.
  Year-end from "1.2 Year end date / Please enter year below", read as for the 2014 form; it is
  almost always OCR noise, so blank.
- A return with neither block (e.g. 1082W 2018, 588W 2021) gives `missing` for all four fields.

| Output field | AR41 row | Unit |
|---|---|---|
| `number_of_members` | A "Members at end of year" | count |
| `turnover` | B "Turnover for year" | £ |
| `assets` | G "Total assets (E+F) (equal to amount in K below)" | £ |
| `number_of_employees` | L "Number of employees (if any)"; Release 1: `not_on_form` | count |
| `share_capital` | not asked: `not_on_form` | |
| `highest_rate_interest_paid_on_shares` | not asked: `not_on_form` | |

Turnover caveat: the AR41 gives no guidance on what "Turnover for year" covers, so clubs may
define it differently from AR30 societies. Row C ("Total (of) income and expenditure (receipts
and payments added together)") is a different measure and is never read as turnover.

Paper forms (all releases) are read row by row, as for the 2014 form. The online form often
prints the labels apart from the values (e.g. 1001W: `7446 74603 22853 97456 10388 0 87068
97456` under the D-L labels). For online returns the numbers after the "Enter '0' where
applicable" line are therefore taken in order, after dropping picture text (which can repeat a
value, 1097W). They are used only if there are exactly 12 and the form's own totals hold:
G = K and E + F = G (`ar41_totals_check` = `pass`). Otherwise (`fail`) the rows are read by
label as for paper and the return cannot be `high`. Grepping gives 147 pass and 74 fail of the
221 online returns; fails include clubs whose own figures do not add up (1008W 2019: G 703,991,
K 704,021) and layouts with a different count of numbers.

Value rules (mirroring the PDF pipeline): £, commas and bold are removed; `N/A` -> `-9`
(`not_applicable`); `NIL`/`NONE` -> `0` (`nil`); a lone letter `O`/`oO` -> `0` (`nil`) on the
online form only, `review` on filled and scanned forms (no filled form in the sample used a letter
O for zero); anything else not cleanly numeric (spaces inside a number
such as `64, 205`, unbalanced brackets, more than 2 decimals on money, decimals on a count, a rate
over 100 or written with £, a digit before £ such as `1£179,522` where an AR41 box border was read
as a 1) -> `review` with the raw text kept; no value -> `missing`. A field the form does not ask
for -> `not_on_form` (2014 form and AR41; not counted as missing).

## Outputs (`output/`)

- `fca_ar30_financials.csv`: one row per selected, cached catalogue document. Columns: `uid`,
  `society_number`, `doc_id`, `selected_as` (`cached` / `baseline` / `random` with `--target`, the
  step that brought the row in; `random` with `--limit`; `all` on a full run), `matches_baseline`
  (True if a baseline modern, releasable return has the same society number and year end; a
  cached row can be True), `catalogue_year_end`, `form_type`, `layout`
  (`online`/`filled`/`scanned`, blank if not extracted), `year_end_on_form`
  (ISO date or blank), `year_end_matches_catalogue` (True/False, blank if no date read), then
  for each field (`number_of_members`, `turnover`, `assets`, `number_of_employees`,
  `share_capital`, `highest_rate_interest_paid_on_shares`) the value and `{field}_status`, then
  each `{field}_raw`, then `ar41_totals_check` (`pass`/`fail` on online AR41 returns, blank
  otherwise), `cu_totals_check` (credit union CY returns, see above), then `confidence`.
- `baseline_comparison.csv`: one row per (return, field) the PDF pipeline parsed: our value and
  status, the baseline value and whether they agree to 2 decimal places. Matched on society
  number and year end; baseline restricted to modern, releasable returns.
- `run_summary.json`: counts by `selected_as`, of `matches_baseline` rows, then by form type;
  layout, confidence, year-end match and field status for modern AR30 (top level), for the
  2014 form (under `ar30_2014`), for AR41 (under `ar41`, with `online_totals_check` pass/fail
  counts) and for the credit union CY return (under `cu_cy_return`, with `totals_check`); plus agree / disagree / ours-missing per field against the baseline (modern returns
  only).

## Confidence

- **high**: modern AR30, 2014 form or AR41, online or filled, every field `parsed`, `nil`,
  `not_applicable` or `not_on_form`; for online AR41 also `ar41_totals_check` = `pass`; credit
  union CY return, online, with `cu_totals_check` = `pass`.
- **review**: every other extracted return (all scanned returns, and online or filled returns with
  any field missing or in review).
- blank: forms not extracted, including the credit union accounts form (year-end only).

No 2014 return in the 12 Oct 2026 sample shows tick boxes, so all fall to `scanned` and `review`,
including clean typed ones such as 7115.

## Known limits

- Scanned paper returns are mostly OCR noise: labels go missing (e.g. 5420R, 4856), values come
  out as `Ce`, `jo`, `BB`, and the year-end date is unreadable. These stay `review`.
- When a label is lost to OCR its value is lost too (text before the first found label is ignored).
- The filled/scanned split rests on tick-box glyphs and a few OCR signs seen in this sample. A
  filled form whose tick boxes do not come through falls to `scanned` (safe: `review`); a scanned
  form showing tick boxes and none of the OCR signs would wrongly get `filled`. None seen so far.
- Filled forms that write a dash for nil (1032RS 2021: `-`) give `missing` and go to `review`.
- Only the first 4.2 block is read; documents holding a second copy (4253R) use the first.
- Modern AR30s whose 4.2 heading is lost (1229RS, 4406, 4428, 4681R, 8272R) are classified but
  mostly give `missing` or `review`: the figures went with the heading. 7404 (every word doubled)
  gives doubled values such as `£508,000 £508,000`, which go to `review`.
- A second copy of the 4.2 heading inside the block (829RS) is read as part of the preceding value,
  which then goes to `review`.
- Credit union CY scans: a value split over two lines (182C `2,034,399.1` / `4 G1`) gives the
  wrong number (`4`); scanned returns stay `review`.
- 2014 form: OCR often drops rows A-E (members, turnover) entirely.
- AR41: Release 1 returns are all scanned and OCR often drops rows A and B. Online returns that
  fail the totals check and put two rows on one line (1046W 2018: `**A. Members at end of year**
  300 **B. Turnover for year** 110416`) give `review` for those rows.
