# FCA society financials from annual returns (AR30)

Standalone enhancement (not part of the builder). Reads the six figures in **section 4.2** of the
modern FCA annual return (AR30) for co-operative and community benefit societies (`GB-MPR-`
uids), plus the financial year-end written on the form, from the Braw corpus API's text of each
return. Regex only: no PDFs, no language model. Every return per society is kept (a panel).

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

Each document is classified; only `ar30_modern` is extracted, the rest are counted.

- `ar30_modern`: title "Annual Return (AR30) form" (OCR `AR3O`, `AR30O` accepted) and
  "4.2 Based on the accounts", and no mention of AR41.
- `ar30_2014`: the older AR30 ("4.2 Has your society produced accounts", figures under
  "2 Statistics"). `ar41`, `ar5` (A.R.5 / A. R. 5A), `credit_union`, `other`.

Layout of a modern return, judged on the text up to the end of the first 4.2 block:

- `online`: the web form (no "(if any)" labels and no paper page footer
  "Mutuals Annual Return (AR3) ... Release N").
- `filled`: the PDF form typed into on a computer. Its tick boxes come through as `☒`/`☐`, and
  none of the OCR signs below appear.
- `scanned`: a paper form read by OCR (text recognition from an image). Signs: page-1 bullets read
  as `- e this form`, the footer bullet read as `@`, `®`, `©` or `e` (`FCA @ Mutuals ...`), or
  `fca.org.uk` read as `fca.orq.uk`. A paper form with neither tick boxes nor OCR signs is also
  treated as scanned.

On the 91 paper returns cached on 12 Oct 2026 the two signs never overlapped: 14 filled (tick
boxes, no OCR signs; e.g. 5106R, 7550, 7670), 73 scanned by bullets/footer and 4 (2025 returns
from a newer OCR, e.g. 1040RS) by `fca.orq.uk` alone; none fell to the default.

## Method

The block runs from the first "4.2 Based on the accounts" to the next "4.3 What Standard"
(capped at 3,000 characters if that is missing). Markup, page footers and "Page N of N" are
removed, then each label is found in form order and its value is the text up to the next label.
Labels printed one under another with the values after them (e.g. 6365R) are filled in order.

Value rules (mirroring the PDF pipeline): £, commas and bold are removed; `N/A` -> `-9`
(`not_applicable`); `NIL`/`NONE` -> `0` (`nil`); a lone letter `O`/`oO` -> `0` (`nil`) on the
online form only, `review` on filled and scanned forms (no filled form in the sample used a letter
O for zero); anything else not cleanly numeric (spaces inside a number
such as `64, 205`, unbalanced brackets, more than 2 decimals on money, decimals on a count, a rate
over 100 or written with £) -> `review` with the raw text kept; no value -> `missing`.

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
  each `{field}_raw`, then `confidence`.
- `baseline_comparison.csv`: one row per (return, field) the PDF pipeline parsed: our value and
  status, the baseline value and whether they agree to 2 decimal places. Matched on society
  number and year end; baseline restricted to modern, releasable returns.
- `run_summary.json`: counts by `selected_as`, of `matches_baseline` rows, then by form type,
  layout, confidence, year-end match and field status, plus agree / disagree / ours-missing per
  field against the baseline.

## Confidence

- **high**: modern AR30, online or filled form, all six fields `parsed`, `nil` or `not_applicable`.
- **review**: every other modern AR30 (all scanned returns, and online or filled returns with any
  field missing or in review).
- blank: forms not extracted.

## Known limits

- Scanned paper returns are mostly OCR noise: labels go missing (e.g. 5420R, 4856), values come
  out as `Ce`, `jo`, `BB`, and the year-end date is unreadable. These stay `review`.
- When a label is lost to OCR its value is lost too (text before the first found label is ignored).
- The filled/scanned split rests on tick-box glyphs and a few OCR signs seen in this sample. A
  filled form whose tick boxes do not come through falls to `scanned` (safe: `review`); a scanned
  form showing tick boxes and none of the OCR signs would wrongly get `filled`. None seen so far.
- Filled forms that write a dash for nil (1032RS 2021: `-`) give `missing` and go to `review`.
- Only the first 4.2 block is read; documents holding a second copy (4253R) use the first.
