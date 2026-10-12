# Scottish company numbers from charity accounts

Standalone enhancement (not part of the builder). Finds Companies House numbers for
Scottish charities (`GB-SC-` uids, e.g. `GB-SC-SC055511`) that have no charity-to-company
link in the Spine, by searching each charity's most recent annual-accounts text (a local
set of cached OSCR documents; the corpus API is not used), then looking each number up on the
Companies House public data API. Adapted from `../ni-company-numbers/` (same structure, caching
and outputs).

## The SC / SC problem

Scottish charity numbers (OSCR) and Scottish company numbers (Companies House) look the
same: `SC` + 6 digits. A charitable company's accounts usually print both, and a lone `SC`
number in a Scottish charity's accounts is most often its charity number. So each mention is
classed by the **nearest keyword** in the 100 characters before it:

- company words ("company", "company number", "company no", "company registration",
  "registered in Scotland", "registered number", "limited by guarantee", "companies house")
  give `number_context = company`;
- charity words ("charity", "charitable", "OSCR", "Scottish Charity", "SCIO", "charity number",
  "charity no", "registered charity") give `charity`;
- no keyword gives `none`.

Example: in "Company No. SC123456 Charity No. SC012345", SC123456 is `company` and SC012345
is `charity`. A number mentioned several times is `company` if any mention is, else `charity`
if any mention is, else `none`. "Registration number" on its own is not used, because
"Charity Registration Number" is common in Scottish accounts. Known weak spot: the phrase
"a charity registered in Scotland, SC012345" reads as company context (the nearest words are
"registered in Scotland"); the charity's own number is still caught by the own-number check,
and other charities' numbers rarely pass the name check.

The number itself also helps. Every Scottish charity number begins `SC0`; Scottish company
numbers can begin `SC0` but usually begin `SC1`-`SC9` (column `sc0_prefix`). A number that does
not begin `SC0` cannot be a charity number, so charity words near it are ignored (its context
becomes `none`), it is never flagged as another charity's number, and it counts as specific
even without a company word. An `SC0` number needs a company word to count as specific.

## Run

    python find_sc_company_numbers.py --limit 50   # trial run on 50 charities
    python find_sc_company_numbers.py              # full run (resumable; only Companies House calls)

Inputs and defaults:

- `--release-dir` release-v1.3.1-Sep2026 (Spine + matches files). Existing links are the
  `TSCS_spine.matches.csv` rows with `orgA_source = "OSCR"` and `orgB_source = "CH"`.
- `work/docs/` - the accounts text, one markdown file per document named
  `{charity number}_{year end}.md` (e.g. `SC000003_2025-07-31.md`). These 7,501 OSCR documents
  (corpus `src_store` oscr) were copied on 2026-10-12 from
  `C:\Users\diarm\Braw Data\web-apps - Documents\braw-charity-accounts-analyses\bank-details-disclosure\work\docs\`.
  The run is limited to these files: the list of documents is read from the file names (latest
  year end per charity), and nothing is fetched from the corpus API. Charities without a file
  here are counted in `targets_without_doc`.
- `--ch-keys` the project `.env` (line `COH_API_KEYS=key1,key2,...`, the same keys
  `code/companies-house` uses); a plain one-key-per-line file also works. Requests to
  `https://api.company-information.service.gov.uk/company/{number}` use basic auth (key as
  username, blank password), rotate across all keys and stay under 600 requests / 5 minutes per key.
- `--work-dir ./work` (holds `docs/` and the caches), `--out-dir ./output`.

Caches in `work/` (resumable; re-runs make no repeat requests):

- `ch_profiles/{number}.json` - the full Companies House company profile for every SC number
  found in each charity's accounts, except the charity's own number (never looked up). Numbers
  not on the register are cached as `{"_not_found": true, ...}`. Delete a file to re-request it.
- `ch_lookup_failures.csv` - numbers whose lookup failed this run (not cached, so a re-run
  retries them).

Tests: `pytest test_find_sc_company_numbers.py`.

## What counts as a number

- `SC` (upper case only) + 6 characters of digits or the letter `O` (OCR often prints zero as
  `O`, e.g. `SCO00003`), with optional space or `:` `.` `-` after `SC`; normalised to `SC` + 6
  digits (`SC000003`). At least one real digit is required.
- Not matched: `SC` preceded by a letter or digit (`XSC123456`), 7-digit runs (`SC1234567`).
- English/Welsh 8-digit company numbers are out of scope for now.

## Outputs (`output/`)

- `sc_company_number_candidates.csv` - every (charity, number) found, with `number_context`, `sc0_prefix`,
  `is_own_charity_number` (the number is the charity's own), `is_other_charity_number` (the
  number is a different Scottish charity on the Spine), register details (name, status, company
  type, incorporation/cessation dates as YYYY-MM-DD, postcode), name similarity, postcode match,
  other-charity links and confidence.
- `sc_company_number_matches.csv` - high-confidence rows in `TSCS_spine.matches.csv` schema,
  `orgA_source = "OSCR"`, `match_type = "companyid - accounts regex"`.
- `run_summary.json` - counts at each step, including `ch_lookups_this_run`, `ch_lookup_failures`
  and `high_by_implication` / `review_by_implication` / `medium_by_implication`.

Each candidate also carries `ch_address` (registered office), `company_spine_row`, `folded_into`
and an `implication` for the Spine. **dedup**: the company already has its own Spine row, so
linking would merge two Spine organisations into one. **conflict**: the company is already folded
into a different Spine organisation (listed in `folded_into`); these rows are always low
confidence and need a manual decision. **enrich**: the company is on the register but not on the
Spine at all, so linking simply adds its company number to the charity.

## Confidence

- **high**: number is in the CH register, not already linked to another charity, specific
  (company context - a company word is the nearest keyword before at least one mention - or the
  number does not begin `SC0`), and name similarity >= 0.85. Unlike the NI version, being the
  only number in the document is not enough.
- **review**: as high, but the name differs (similarity < 0.85) and the match rests on the same
  postcode alone. For manual checking (renamed companies and abbreviations, but also subsidiaries
  and corporate trustees at the charity's address). Not written to the matches file.
- **medium**: in the register and not ruled out, but otherwise weaker (an `SC0` number without
  company context, a lower name similarity without a postcode match, or the
  Companies House record is a partnership - `scottish-partnership` / `limited-partnership` - not a
  company).
- **low**: not in the register, already linked to another charity or folded into another Spine
  organisation, the charity's own number, or (for `SC0` numbers only) charity context, or another
  Scottish charity's number without company context.
- A charity with more than one high row has all of them downgraded to medium.
