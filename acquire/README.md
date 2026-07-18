# acquire — programmatic raw-data downloads (RUNBOOK step 0)

One module per source. Each downloads the raw register file(s) and saves
them under the exact filename pattern the preprocess step parses the
snapshot date from (RUNBOOK.md §3.2). All modules take `--outdir` = the
raw-data **root** (default `../raw_data` relative to the repo root); each
writes into its own subfolder. Run from the repo root, e.g.:

```
python -m acquire.oscr --outdir ../raw_data
```

Shared download/retry helpers live in `common.py`. Requirements beyond
the pipeline's own: `requests`, `beautifulsoup4` (CCNI scrape),
`openpyxl` (Social Housing England spreadsheet).

`cqc_api.py` (CQC care directory) is maintained separately — see its
own docstring.

## Sources

| Module | Source | Output | Automated? |
|---|---|---|---|
| `ccew` | register-of-charities.charitycommission.gov.uk full-register download ("charity" table, JSON zip; link scraped from the download page) | `ccew/ccew-publicextract.<monyyyy>.csv` (month from the extract's own `date_of_extract`) | Fully. Recreates the lost JSON→CSV converter (recipe preserved in `handler/preprocess_charity_regulators.py`) |
| `oscr` | oscr.org.uk `/download/charity-register` and `/download/charity-former-register` (daily zips) | `oscr/CharityExport-DD-Mon-YYYY.csv`, `oscr/CharityExport-Removed-DD-Mon-YYYY.csv` (OSCR's native names kept) | Fully. Use implies acceptance of the OGL terms on OSCR's download page |
| `ccni` | charitycommissionni.org.uk CSV export API (`/api/charity-search/exportSearchResultsToCsv/` — moved from the old `/umbraco/...` path in 2025/26; `homePageId` parameter read from the search page) + per-charity details pages for removal dates | `ccni/register_charitydetails_YYYY_MM_DD.csv`, `ccni/ni-removals-YYYY-MM-DD.csv` | Fully. SSL verification is ON (the old scraper's `verify=False` hack is no longer needed). Removals scrape is **incremental**: dates already in earlier `ni-removals-*.csv` files are re-used and only newly-removed charities get a page visit (first-ever run ~1,300 pages ≈45 min; routine re-runs seconds–minutes; `--full` forces a complete re-scrape) |
| `companies_house_bulk` | download.companieshouse.gov.uk/en_output.html (monthly one-file product, ~500 MB zip) | `CompaniesHouse/BasicCompanyDataAsOneFile-YYYY-MM-DD.csv` | Fully; `--verify-only` checks the link without the big download |
| `companies_house_api` | api.company-information.service.gov.uk company-profile endpoint | `CompaniesHouse/ch_api_company_profiles_YYYY-MM-DD.csv` (same columns as the historical `ch_adv_scrape*.csv`; this generic name deliberately does **not** match that glob — the dissolution-check flow below writes the pipeline-consumable name) | Needs API key(s): `COH_API_KEYS=key1,key2,...` in the environment or a `.env` file via `--env-file`. One worker thread per key, each inside the 600-per-5-min per-key limit (12 keys ≈ 20 req/s); resumable. Replaces the external ch_adv_scraper's "organisation details" role only — a full advanced-search rebuild of pre-2010s dissolved companies still needs that repo. **Quote the `--numbers` list in PowerShell** (unquoted comma lists are parsed as integers and lose their leading zeros) |
| `ch_dissolution_check` | derives its own input: spine `GB-COH-*` rows with a blank `removeddate` MINUS companies still in the latest bulk download (the bulk product lists live companies only, so a vanished company = candidate dissolution), then fetches those profiles via `companies_house_api` | `CompaniesHouse/ch_adv_scrape_api_refresh_YYYY-MM-DD.csv` — **matches the pipeline glob on purpose**; the handler stamps iteration from the filename date (dateless names keep the historical 2022 stamp) | Needs the spine CSV (`--spine`), a bulk download in place, and API keys as above. `--dry-run` reports candidate counts without calling the API |
| `social_housing_england` | gov.uk "Current registered providers of social housing" (monthly .xlsx) | `SocialHousingEngland/registered_providers_YYYYMMDD.csv` (date from the spreadsheet filename; dates rewritten DD/MM/YYYY for the handler) | Fully |
| `scot_housing_reg` | housingregulator.gov.scot statistical information → `afs_public.csv` (annual financial statements, all social landlords; served with a UTF-8 BOM but Windows-1252 body — BOM stripped on save) | `ScotHousingReg/all-social-landlords-YYYY.csv` (YYYY = latest financial-year end in the data) | Fully |
| `co_ops` | uk.coop/resources/open-data (organisations CSV) | `co_ops/coops_opendata_YYYY_MM.csv` (YYYY_MM from the source filename) | Fully |
| `mutuals` | mutuals.fca.org.uk → `SocietyList.csv` (direct static export; no session needed) | `mutuals/SocietyList-YYYY-MM.csv` | Fully. Stops with a clear error if the FCA ever fixes the "Full Registation Number" header typo the pipeline relies on |
| `care_inspectorate` | careinspectorate.com datastore library (latest snapshot page → S3 CSV) | `CareInspectScot/MDSF_data_YYYY.csv`, or `MDSF_data.MonYYYY.csv` with `--monthly-name` (use the latter when downloading more than once a year) | Fully |
| `ftc` | github.com/drkane/charity-lookups `relationships/_sameas.csv` (**owner-confirmed source**, July 2026; the data behind findthatcharity.uk) | `FTC_data/dkane_relationships_sameas.csv` | Fully. The download already carries the needed columns (`org_id_a`, `org_id_b`, `source` incl. "Charity Commission Register of Mergers" rows) and is validated before saving; re-derives the lost linkage file in RUNBOOK §3.1 |

## What still cannot be re-downloaded

The four preserved inputs in RUNBOOK §3.1 (the ccew/oscr/ccni historical
base files) remain restore-from-backup only — except
`FTC_data/dkane_relationships_sameas.csv`, which `acquire.ftc` now
re-derives.

## Live-test record (17 July 2026)

Every module was run for real on 17 Jul 2026 (into a scratch folder,
not `../raw_data`):

- CCEW: 56.6 MB zip → 397,564 rows, 34 columns → `ccew-publicextract.jul2026.csv`
- OSCR: 8.7 MB + 3.6 MB zips → `CharityExport-17-Jul-2026.csv`, `CharityExport-Removed-17-Jul-2026.csv`
- CCNI: 10.1 MB export, 8,339 rows (1,344 removed); removals scrape verified on the first 5 removed charities (5/5 dates parsed)
- Companies House bulk: link verified (HEAD 200, 496,518,240 bytes, zip magic OK); full download not pulled in the test
- Companies House API: 3 profiles fetched with 12 rotating keys (Oxfam, Cancer Research UK, one CIC — subtype and SIC formats confirmed)
- Social Housing England: 1,580 providers (1,262 Non-profit) → `registered_providers_20260629.csv`
- Scottish Housing Regulator: 720 rows, financial years 2020/2021–2024/2025 → `all-social-landlords-2025.csv`
- Co-ops UK: 8,017 organisations → `coops_opendata_2026_07.csv`
- Mutuals: 32,393 societies → `SocietyList-2026-07.csv`
- Care Inspectorate: 10,566 rows (31 May 2026 snapshot) → `MDSF_data_2026.csv`
- FTC: 82,205 links (5,141 merger rows); parsed by `spine.build_public_spine.read_dkane_sameas()` → 149,117 linked organisations, 5,074 merger primaries

All output filenames and column layouts were checked against the
parsing logic in `handler/preprocess.py` and
`handler/preprocess_charity_regulators.py`.
