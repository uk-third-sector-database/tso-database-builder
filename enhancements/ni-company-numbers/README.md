# NI company numbers from charity accounts

Standalone enhancement (not part of the builder). Finds Companies House numbers for
Northern Irish charities (`GB-NIC-` uids) that have no charity-to-company link in the
Spine, by regex-searching each charity's most recent annual-accounts text from the
Braw corpus API, then looking each number up on the Companies House public data API.

## Run

    python find_ni_company_numbers.py --limit 50   # trial run on 50 charities
    python find_ni_company_numbers.py              # full run (~1 request/1.05s; resumable)

Inputs and defaults:

- `--release-dir` release-v1.3.1-Sep2026 (Spine + matches files).
- `--api-keys` braw-charity-accounts-api/.api-keys.local.json ("prod" key) for the corpus API.
- `--ch-keys` the project `.env` (line `COH_API_KEYS=key1,key2,...`, the same keys
  `code/companies-house` uses); a plain one-key-per-line file also works. Requests to
  `https://api.company-information.service.gov.uk/company/{number}` use basic auth (key as
  username, blank password), rotate across all keys and stay under 600 requests / 5 minutes per key.
- `--work-dir ./work` (caches; delete `work/catalogue_gb_nic.csv` to refresh the catalogue),
  `--out-dir ./output`.

Caches in `work/` (all resumable; re-runs make no repeat requests):

- `docs/` - accounts text per charity.
- `ch_profiles/{number}.json` - the full Companies House company profile for **every** NI
  number found in each charity's accounts, not only the best match. Numbers not on the register
  are cached as `{"_not_found": true, ...}`. These profiles can be reused to study which other
  companies charities mention (subsidiaries, trading arms, funders, landlords). Delete a file to
  re-request it.
- `fetch_failures.csv` / `ch_lookup_failures.csv` - documents / numbers that failed this run
  (not cached, so a re-run retries them).

Tests: `pytest test_find_ni_company_numbers.py`.

## What counts as a number

- `NI` (or OCR `Nl`) + 5-6 digits, e.g. `NI049781`, `NI 49781`, `Company Number: NI031517`; normalised to `NI` + 6 digits.
- Old form `R0` + 6 digits, e.g. `R0000304`.
- Not matched: charity numbers (`NIC101307`), 1-4 digit shorthand (`NI 4978`, `NI 2025`).

## Outputs (`output/`)

- `ni_company_number_candidates.csv` - every (charity, number) found, with register details
  (name, status, company type, incorporation/cessation dates as YYYY-MM-DD, postcode), name similarity, postcode match, other-charity links and confidence.
- `ni_company_number_matches.csv` - high-confidence rows in `TSCS_spine.matches.csv` schema,
  `match_type = "companyid - accounts regex"`.
- `run_summary.json` - counts at each step, including `ch_lookups_this_run`, `ch_lookup_failures`
  and `high_by_implication` / `review_by_implication` / `medium_by_implication`.

Each candidate also carries `ch_address` (registered office), `company_spine_row`, `folded_into`
and an `implication` for the Spine. **dedup**: the company already has its own Spine row, so
linking would merge two Spine organisations into one. **conflict**: the company is already folded
into a different Spine organisation (listed in `folded_into`, taken from `TSCS_spine.matches.csv`);
these rows are always low confidence and need a manual decision. **enrich**: the company is on the
register but not on the Spine at all, so linking simply adds its company number to the charity.

## Confidence

- **high**: number is in the CH register, not already linked to another charity, name similarity
  >= 0.85, and (the only number in the document OR a keyword such as
  "company", "registered number", "limited by guarantee" within 100 characters before it).
- **review**: as high, but the name differs (similarity < 0.85) and the match rests on the same
  postcode alone. For manual checking: catches renamed companies and abbreviations, but also
  subsidiaries and corporate trustees that share the charity's address. Not written to
  `ni_company_number_matches.csv`.
- **medium**: in the register and not linked to another charity, but otherwise weaker.
- **low**: not in the register, already linked to another charity or folded into another Spine
  organisation, or the "company number" is
  just the charity's own registration number with an NI prefix (e.g. NI110229 for charity 110229).
- A charity with more than one high row has all of them downgraded to medium.
