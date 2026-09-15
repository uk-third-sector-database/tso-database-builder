# Regenerating the TSCS Organisation Register (Spine): Run Book

This document describes the complete process for regenerating the Third
Sector and Civil Society (TSCS) Organisation Register from scratch. It was
written in July 2026 after a full review of the pipeline, so that the Spine
can be rebuilt without relying on any one person's working knowledge.

Read this alongside:

- `README.md` — quick start.
- `tscs_database_builder.tex/pdf` — the technical appendix (method detail,
  source URLs, download dates used in past builds).
- The published guidance:
  https://uk-third-sector-database.github.io/guidance/tcss-organisation-register-guidance.html

## 1. How the pipeline fits together

```
raw register downloads            (step 0 — manual/scripted, see §3)
        |
  preprocess: stamp each file's snapshot date ("iteration"), concatenate
        |                         (steps 1–3)
  per-source handlers: one standardised "sub-spine" CSV per register
        |                         (step 4)
  build-spine: rule-based record linkage across registers
        |                         (step 5)
  check-spine + SIC codes + cso_type classification
        |                         (steps 6–8)
  seed-supplementary + suppress-echo-matches
        |                         (steps 9–10)
  TSCS_spine.{spine,supplementary,matches,SIC_codes}.csv
        |
  release gates: validate-release + population source alignment (§5)
```

All commands run **from the repo root**. Data lives in sibling folders
(outside the repo, so nothing large is ever committed):

- `../raw_data/` — one subfolder per source (see §3 for exact names).
- a **new, clean staging directory per build** — all intermediates and
  outputs of that run. The build script requires it not to exist yet.
- `../public_spine_data/` — holds exactly the four signed CSVs of the
  accepted release. **Never run a build in this folder.** Promote the four
  final CSVs into it only after a build passes every gate in §5, and
  re-hash them after copying.

The whole recipe is scripted in `spine_bash_script.sh` (run under Git Bash
on Windows). The standard invocation is:

```
./spine_bash_script.sh <prior_release_dir> <new_staging_dir> \
    <ccew_current.csv> <oscr_current.csv> <ccni_current.csv>
```

`<prior_release_dir>` holds the prior published supplementary and matches
CSVs (used by steps 9–10). The final three arguments are the explicitly
selected current charity-register snapshots for the population
source-alignment gate; when given these paths the script runs both release
validations automatically at the end of the build. The steps below explain
what each stage does and what can go wrong.

## 2. Environment

- Python **3.11** (python.org installer on Windows; `pyenv` targets in the
  Makefile are Unix-only).
- Create a virtual environment and install the pinned requirements. Three
  requirement files exist and should be used separately: `requirements.txt`
  (core build), `test-requirements.txt` (adds the test tooling) and
  `requirements-visualise.txt` (optional, notebook visualisations only):

  ```
  python -m venv .tso
  .tso\Scripts\python.exe -m pip install -r requirements.txt -r test-requirements.txt
  ```

- Activation is optional: call the environment's interpreter directly, e.g.
  `.tso/Scripts/python.exe cli.py validate-release <dir>`. This is what
  `spine_bash_script.sh` does by default (it uses `.tso/Scripts/python.exe`
  when present; set `PYTHON_BIN` to override), and it guarantees Windows
  operators are on the intended interpreter without shell activation.
- Run the test suite before a build: `.tso/Scripts/python.exe -m pytest`
  from the repo root. All tests should pass; investigate any failure before
  proceeding.
- On Windows, run `spine_bash_script.sh` under **Git Bash** (it uses bash
  redirection). PowerShell will not run it unmodified.
- The script is **fail-fast** (`set -Eeuo pipefail`): any failing step stops
  the build and leaves the partial staging directory in place for
  diagnosis. Do not release from a directory whose build did not print
  `SUCCESS`.
- On Windows, set `PYTHONUTF8=1` (e.g. `export PYTHONUTF8=1` in Git Bash)
  before running any build step. Parts of the pipeline write intermediate
  files as UTF-8 but read them back with the system default encoding, which
  on Windows is cp1252 — without UTF-8 mode, `process-source` fails with a
  `UnicodeDecodeError` on the first non-cp1252 character. The build script
  exports this automatically.
- The build script defaults `PYTHONHASHSEED=0` (override by exporting a
  different value, e.g. for cross-seed QA). This is defence in depth only:
  outputs are deterministic by construction and were verified byte-identical
  across seeds 0 and 1 (see §5).
- The script takes an atomic lock — the directory
  `../raw_data/.tscs-spine-build.lock` — before touching the shared raw-data
  folder, so two builds cannot preprocess it concurrently. **Stale-lock
  recovery:** if a build crashed and the lock remains, first verify no build
  or preprocess process is still running, then remove the empty lock
  directory and retry.

## 3. Step 0 — acquire the raw data

This is the least automated stage and the most common source of failure.
The snapshot date ("iteration") of every downloaded file is parsed **from
its filename**, so files must be named exactly as shown. Get a pattern
wrong and the file is silently skipped or its details lose the recency
contest.

### 3.1 Files that must be PRESERVED (or reconstructed)

**The design principle behind this section.** Every build REGENERATES the
current facts from raw register data, but some history is unrepeatable —
it came from snapshot files that no longer exist and records the registers
no longer publish. That history enters a build in exactly two ways: (a) as
reconstructed input files, rebuilt once from the most recent published
release and then kept permanently alongside fresh downloads (§3.1.1–§3.1.3
— data goes in through the front door and flows through the normal
matching rules), and (b) for historical name/address variants only, as the
seed-supplementary union with the previous release (§4 step 9 — output
rows carried forward directly, because a raw snapshot row can only hold
one name and one address). Anything in category (a) or (b) has "the
previous published release" as its effective provenance; the values
themselves are whatever v1.0 recorded, unaltered.

These inputs are irreplaceable or curated:

| File | Role | If lost |
|---|---|---|
| `../raw_data/ccew/ccew_spine_public.csv` | Historical CCEW base (2001–2023), built once by `archive/ccew_publicspine_prep.do` from private snapshots | Reconstruct from the published Spine — see §3.1.1 |
| `../raw_data/oscr/oscr_spine_public.csv` | Historical OSCR base (2012–2023), from `archive/oscr_publicspine_prep.do` | Reconstruct from the published Spine — see §3.1.1 |
| `../raw_data/ccni/ccni_spine.csv` | Historical CCNI base (April 2023), from `archive/ccni_spine_prep.do` | Reconstruct from the published Spine — see §3.1.1 |
| `../raw_data/CompaniesHouse/ch_adv_scrape.csv` | One-off 2022 advanced-search API scrape (github.com/uk-third-sector-database/ch_adv_scraper); the only source for companies dissolved before the bulk downloads began | Reconstruct from the published Spine — see §3.1.2 |
| `../raw_data/FTC_data/dkane_relationships_sameas.csv` | Find that Charity "same-as" lookup; supplies the majority of cross-register links and the charity-merger logic | Can be re-derived from David Kane's public Find that Charity data (findthatcharity.uk; drkane on GitHub — includes CCEW Register of Mergers). Document the derivation when refreshed |
| `co_ops/coops_bootstrap_2026_01.csv`, `SocialHousingEngland/registered_providers_bootstrap_Jan2026.csv`, `ScotHousingReg/social_landlords_bootstrap.to_Jan2026.csv`, `CareInspectScot/MDSF_data_bootstrap.Jan2026.csv` (all under `../raw_data/`) | Reconstructed lost-register history: organisations that left the co-op / housing / care registers before the July 2026 fresh downloads (their historical snapshots were lost); sole input source for 281 spine organisations and ~4,800 match-pair endpoints | Reconstruct from the published Spine — see §3.1.3 |

The build now **stops with an error** if the FTC or OSCR linkage files are
missing (pass `--allow-missing-linkage` to `build-spine` only if you
deliberately want a spine without them).

#### 3.1.1 Reconstructing the three charity base files from a published release

The original Stata-built base files were lost in 2026 and cannot be rebuilt
from public register downloads. The **standard way to seed them** is now to
reconstruct them from the most recent published Spine release, whose
spine + supplementary + matches files together carry almost all of the base
files' content. Future builds then equal "published Spine (as the carrier
of the 2001–2023 history) + fresh register downloads". From the repo root:

```
python cli.py bootstrap-base-files \
    <extracted>/TSCS_spine.spine.csv \
    <extracted>/TSCS_spine.supplementary.csv \
    <extracted>/TSCS_spine.matches.csv \
    -o ../raw_data
```

`<extracted>` is the unzipped published release (v1.0 = `tcss-spine-Mar2026.zip`).
`--as-of mm/yyyy` states the currency of the release's details (default
`01/2026`, correct for v1.0 which is the January 2026 build); change it if
reconstructing from a later release. Run this ONCE, then run
`process-charity-source` and the rest of the build as normal.

Validated against v1.0 (July 2026): 100.0000% of published organisations
are reproduced on all three registers, plus the organisations that were
merged into another during the original linkage (5,364 CCEW, 1,421 OSCR)
are recovered so the next build re-merges them identically; every date
difference falls into designed categories (regulator-own registration
dates preferred over a matched company's incorporation date; removals the
published spine suppressed are recovered). Full numbers and the
reconstruction rules are in the `spine/bootstrap_base_files.py` docstring.

**Permanently lost in reconstruction** (all filled with neutral values the
pipeline treats as "no special handling"):

- CCEW: the `cqc_reg` flag ("should also be CQC-registered"); the
  per-snapshot origin years of historical name/address/date variants; the
  linked-charity substructure (which `-1`/`-2` sub-charity a historical
  name belonged to — flattened to name variants of the parent charity).
- OSCR: the `name_origin` provenance text of historical names ("Known As",
  "Former Name", …); the `localauthority` column and the split address
  lines (the consolidated address string is carried instead); 2012-register
  linkage rows whose counterpart never entered the published spine.
- CCNI: name/address variants of organisations already removed in the
  published release (472 organisations — kept out so an arbitrary variant
  cannot become the primary name; their removal *dates* are kept, and the
  variants remain available in the published v1.0 supplementary file);
  company numbers where the published matches carry no link.

One behaviour to expect: until the first fresh CCNI download is added,
which of a CCNI organisation's recorded names becomes primary is arbitrary
(the CCNI step stamps all base rows with one shared snapshot date). It
resolves at the first `charitydetails_*` download, which any real build
includes.

#### 3.1.2 Reconstructing the 2022 Companies House scrape from a published release

The 2022 advanced-search scrape file is the pipeline's only source for
companies dissolved before the monthly bulk downloads began; without any
`ch_adv_scrape*.csv` present, a from-raw rebuild **silently drops those
companies**. If the original file is unavailable, reconstruct it from the
published release (same principle as §3.1.1). From the repo root:

```
python cli.py bootstrap-ch-scrape \
    <extracted>/TSCS_spine.spine.csv \
    <extracted>/TSCS_spine.supplementary.csv \
    <extracted>/TSCS_spine.matches.csv \
    <extracted>/TSCS_spine.SIC_codes.csv \
    -o ../raw_data
```

This writes `../raw_data/CompaniesHouse/ch_adv_scrape_bootstrap.csv` in the
2022 scraper's exact column layout. The filename deliberately carries no
date: `preprocess-CH` stamps dateless `ch_adv_scrape` files with the
historical iteration `2022`, so every fresh bulk download or API refresh
wins the recency contest against these rows. Run it ONCE, then
`preprocess-CH` as normal. (If the original 2022 file surfaces from backup,
prefer it and delete the bootstrap file.)

Validated against v1.0 (July 2026): all 425,797 GB-COH organisations are
reproduced (325,169 with their own spine row + 100,628 that were merged
into another organisation during linkage), with 100% identical names,
cities and postcodes and every date difference in a designed category
(the company's own displaced incorporation/dissolution dates recovered
from the supplementary file: 73 + 207 companies); CIC flags are exact
(72,881, plus 63 inherited by absorbed companies). Reconstruction rules
and permanent losses (company_type detail beyond the CIC flag — unused by
the pipeline; name/address history; SIC codes recorded as "None Supplied")
are in the `spine/bootstrap_ch_scrape.py` docstring.

#### 3.1.3 Reconstructing the lost co-op / housing / care register history

The historical snapshots of four registers — Co-operatives UK, Social
Housing England, the Scottish Housing Regulator and Care Inspectorate
Scotland — were lost, and their fresh downloads list **current members
only**. Without reconstruction, a from-raw rebuild silently drops every
organisation that left those registers (July 2026 trial: 281 spine
organisations gone entirely, plus ~4,800 match pairs whose deregistered
co-op / closed care-service endpoint never entered the inputs). From the
repo root, **after** the fresh register downloads are in place (the step
computes "what is missing" against them):

```
python cli.py bootstrap-lost-registers \
    <extracted>/TSCS_spine.spine.csv \
    <extracted>/TSCS_spine.supplementary.csv \
    <extracted>/TSCS_spine.matches.csv \
    -o ../raw_data
```

This writes one historical snapshot per register (filenames in the §3.1
table), each in the register's exact raw-download column layout,
containing only the organisations present in the published release but
absent from the fresh downloads. The filenames carry the release currency
(January 2026), so `handler/preprocess.py` stamps the rows iteration
`01/2026` and any fresher download wins the recency contest. Run it ONCE,
then `handler/preprocess.py` and the build as normal; the step refuses to
overwrite its outputs. Keep the four files permanently — they are the
pipeline's only source for these organisations.

Key recovered values: the co-op FCA society number (what the
`companyid - coop mutual` rule fires on) is taken from the release's own
match rows — regulator-published data v1.0 preserved, so the re-fired
pairs are NOT bootstrap echoes and `suppress-echo-matches` (which only
targets `companyid - id_in_source` rows the prior release never published)
does not touch them. Reconstruction rules, absorber-fill logic and
permanent losses (no dates/addresses for Scottish Housing Regulator
records; no removal dates for Care Inspectorate Scotland; care pairs whose
service is still listed but under a revised provider name) are in the
`spine/bootstrap_lost_registers.py` docstring. Validation numbers: see the
2026-07-19 progress-log entry and
`docs/spine-docs/qa-rebuild-2026-07/validate_lostreg_restoration.py`.

### 3.2 Fresh downloads, per source

**Every source below is scripted**: `python -m acquire.<module> --outdir
../raw_data` downloads it and saves it under the exact expected filename
(module-per-source detail, API-key requirements and the July 2026
live-test record are in `acquire/README.md`). The table documents where
the data comes from and the filename contract the preprocess step parses
— useful as the manual fallback if a website changes and a module breaks.

| Source | Download from | Save as (exact pattern) | Notes |
|---|---|---|---|
| CCEW (Charity Commission E&W) | register-of-charities.charitycommission.gov.uk → full register download ("charity" table) | `../raw_data/ccew/ccew-publicextract.<monyyyy>.csv` e.g. `ccew-publicextract.feb2025.csv` | Download is JSON/txt; `acquire.ccew` converts to CSV (recreates the lost `reformat_ccew.ipynb` from the recipe preserved in `handler/preprocess_charity_regulators.py`) |
| OSCR (Scottish Charity Register) | oscr.org.uk charity register download (updated daily) | keep native names: `../raw_data/oscr/CharityExport-DD-Mon-YYYY.csv` and `CharityExport-Removed-DD-Mon-YYYY.csv` | Two files: current + removed |
| CCNI (NI) | `acquire.ccni` (supersedes `archive/ccni-scrape-2025-05-20.py`) | register → `../raw_data/ccni/<anything>charitydetails_YYYY_MM_DD.csv`; removals → `../raw_data/ccni/ni-removals-YYYY-MM-DD.csv` | The scraper also recovers removal dates (CCNI's own download omits them). Removals scrape is incremental across earlier `ni-removals-*` files — never seed a partial/test file as the first one. Fragile HTML scrape — verify output row counts against the CCNI website total |
| Companies House bulk | download.companieshouse.gov.uk/en_output.html | `../raw_data/CompaniesHouse/BasicCompanyDataAsOneFile-YYYY-MM-DD.csv` | Free monthly product; covers live companies only |
| Companies House API scrape | one-off 2022 output of github.com/uk-third-sector-database/ch_adv_scraper | `../raw_data/CompaniesHouse/ch_adv_scrape*.csv` | Covers companies dissolved before bulk downloads began. PRESERVE the 2022 output; if lost, reconstruct with `bootstrap-ch-scrape` (§3.1.2) |
| CQC (Care Quality Commission) | cqc.org.uk → "Using CQC data" → care directory | `../raw_data/CareQualityCommission/DD_MonthName_YYYY_<anything>.csv` e.g. `01_January_2023_directory.csv` | File has 4 preamble rows (handled). Matches only — CQC records never form spine rows |
| Care Inspectorate Scotland | careinspectorate.com → statistics → datastore (MDSF) | `../raw_data/CareInspectScot/MDSF_data_<year>.csv` or `<name>.<MonYYYY>.csv` | Matches only. Column names have varied across years; new variants need edits in `handler/preprocess.py` |
| Co-operatives UK | uk.coop/resources/open-data | `../raw_data/co_ops/<anything>_YYYY_MM.csv` | |
| Mutuals (FCA register) | mutuals.fca.org.uk export | `../raw_data/mutuals/<anything>-YYYY-MM.csv` or `<name>.MonYYYY.csv` | Code relies on the register's own header typo "Full Registation Number" — check it still exists after FCA portal changes |
| Social Housing England | gov.uk "Registered providers of social housing" (monthly) | `../raw_data/SocialHousingEngland/<anything>_YYYYMMDD.csv` or `_MonYYYY.csv` | Published as a spreadsheet; export the providers sheet to CSV. Only "Non-profit" designations are kept |
| Scottish Housing Regulator | housingregulator.gov.scot → statistical information (annual) | `../raw_data/ScotHousingReg/<anything>-YYYY.csv` or `<name>.to_MonYYYY.csv` | Source has no addresses or dates |

Keep every previously used download in place — the preprocess step
concatenates **all** files in each folder, and history (e.g. an
organisation's removal) is inferred across snapshots.

### 3.3 Assembling `../raw_data` from scratch, in order

The full scripted sequence for an empty `../raw_data` (new machine, or
rebuilding after loss). `<extracted>` is the unzipped published release;
`<env>` is a `.env` file carrying `COH_API_KEYS` and
`CQC_PRIMARY_KEY`/`CQC_SECONDARY_KEY`. Order matters only where stated.

1. **Seed the reconstructed historical inputs** (one-off; §3.1.1 and §3.1.2 —
   skip either if the original file is restored from backup instead):

   ```
   python cli.py bootstrap-base-files <extracted>/TSCS_spine.spine.csv \
       <extracted>/TSCS_spine.supplementary.csv \
       <extracted>/TSCS_spine.matches.csv -o ../raw_data
   python cli.py bootstrap-ch-scrape <extracted>/TSCS_spine.spine.csv \
       <extracted>/TSCS_spine.supplementary.csv \
       <extracted>/TSCS_spine.matches.csv \
       <extracted>/TSCS_spine.SIC_codes.csv -o ../raw_data
   ```

2. **Register downloads** (independent of each other; minutes each):
   `python -m acquire.<module> --outdir ../raw_data` for `ccew`, `oscr`,
   `ccni`, `co_ops`, `mutuals`, `care_inspectorate`, `ftc`,
   `social_housing_england`, `scot_housing_reg`. The first-ever `ccni` run
   scrapes every removed charity's page (~1,300 pages ≈ 45 min); later
   runs are incremental (seconds–minutes).

   Then, AFTER these downloads are in place (one-off; §3.1.3 — the step
   computes what is missing against the downloads on disk):

   ```
   python cli.py bootstrap-lost-registers <extracted>/TSCS_spine.spine.csv \
       <extracted>/TSCS_spine.supplementary.csv \
       <extracted>/TSCS_spine.matches.csv -o ../raw_data
   ```

3. **Companies House bulk** (~500 MB; `--verify-only` first if unsure):
   `python -m acquire.companies_house_bulk --outdir ../raw_data`

4. **Companies House dissolution refresh** — AFTER step 3; needs `<env>`
   and a spine file:

   ```
   python -m acquire.ch_dissolution_check \
       --spine <extracted>/TSCS_spine.spine.csv --env-file <env> --dry-run
   ```

   then without `--dry-run`. Writes
   `CompaniesHouse/ch_adv_scrape_api_refresh_<date>.csv` (July 2026 first
   run: 7,678 candidates ≈ 7 min with 12 keys).

5. **CQC full API fetch** (~64k providers ≈ 2 h; resumable within the
   calendar month): `python -m acquire.cqc_api --out
   ../raw_data/CareQualityCommission --env <env>`. Also restore any
   historical CQC care-directory snapshots you hold (filename pattern in
   §3.2) — they carry the CQC match history.

Steps 2, 3→4 and 5 have no dependencies on each other and can run in
parallel shells. First full assembly on this layout: July 2026 (all
steps verified live).

## 4. Steps 1–10 — the build

These are the commands in `spine_bash_script.sh`, in order (the script
numbers them 1/10 … 10/10 and then runs the two release validations of §5
automatically):

1. `python3 handler/preprocess.py`
   Stamps iterations and concatenates the six non-charity sources →
   `../raw_data/<Source>.all.csv` each.
2. `python3 cli.py preprocess-ch ../raw_data/CH.all.csv`
   Concatenates Companies House bulk + API-scrape files. **The argument is
   the OUTPUT path.**
3. `python3 cli.py process-charity-source ccni` (then `oscr`, then `ccew`)
   Combines each regulator's base file + downloads → `../raw_data/{ccni,oscr,ccew}.all.csv`.
   The OSCR step also writes `../raw_data/oscr.linkage.csv`, required later.
4. Ten `python3 cli.py process-source <Handler> <in> <out>` calls →
   per-source `*.spine.csv` + `*.supplementary.csv` in `../public_spine_data/`.
5. `python3 cli.py build-spine <ten .spine.csv files> -o ../public_spine_data/TSCS_spine`
   The record linkage. **The file order is part of the method** (earlier
   sources take precedence, and most match rules only link a later record
   to an earlier one): ccew, oscr, ccni, mutuals, CH, co-ops, Scottish
   Housing Regulator, Social Housing England, Care Inspectorate Scotland,
   CQC. Console output (including per-organisation warnings) goes to
   `build_spine.out` — read it after every build.
6. `python3 cli.py check-spine <same ten files> -o ../public_spine_data/TSCS_spine`
   Verifies every input organisation reached the spine, supplementary or
   matches output.
7. `python3 cli.py build-sic-codes-list ../raw_data/CH.all.csv ../public_spine_data/TSCS_spine.matches.csv ../public_spine_data/TSCS_spine.SIC_codes.csv`
   SIC (industry) codes for spine organisations, via their Companies House
   links. Must use the matches file just built (an earlier version of the
   script read a stale file here).
8. `python3 cli.py add-cso-type ../public_spine_data/TSCS_spine.spine.csv ../public_spine_data/TSCS_spine.SIC_codes.csv`
   Appends the `cso_type` and `cso_subtype` classification columns
   (rewrites the spine CSV in place). Historically this ran outside the
   repo; it is now step 8 of the standard build.
9. `python3 cli.py seed-supplementary ../public_spine_data/TSCS_spine.supplementary.csv ../public_spine_data/TSCS_spine.spine.csv ../public_spine_data/TSCS_spine.matches.csv <prior_release>/TSCS_spine.supplementary.csv`
   Unions the prior published release's supplementary rows into the fresh
   build, so historical name/address variants that only survive in the
   published release (they came from register snapshots that can no longer
   be re-downloaded) are never lost by a from-raw rebuild. Only rows whose
   uid is represented in the new release (spine or matches) are carried;
   rows the build already produced are skipped. The pre-seed file is kept
   as `TSCS_spine.supplementary.preseed.csv` and the step refuses to run
   twice. On the July 2026 trial rebuild this restored 393,833 of v1.0's
   872,084 rows (697,656 built + 393,833 seeded = 1,091,489; only 8,581
   v1.0 rows — organisations no longer representable — were not carried).
   The final accepted July 2026 build, after the lost-register restoration
   of §3.1.3 and the association-matching correction, produced 1,108,256
   seeded supplementary rows; the v1.2 rebuild of 20 July (housing–mutuals
   matching fix) produced 1,108,831.
10. `python3 cli.py suppress-echo-matches ../public_spine_data/TSCS_spine.matches.csv <prior_release>/TSCS_spine.matches.csv`
    Removes bootstrap-echo `companyid - id_in_source` rows from the fresh
    matches file. Because `bootstrap-base-files` back-fills CCEW/CCNI
    company numbers from the prior release's own links (CCEW's extracts do
    not publish them), every rebuild re-fires the company-number rule on
    those planted numbers and re-emits the prior release's ftc links as if
    they were independent identifier evidence. This step drops a
    `companyid - id_in_source` row only when the prior release did not
    publish that row itself, the prior release already linked the pair
    another way, and the pair keeps other evidence in the fresh file — so
    no pair is ever disconnected and the uid universe is unchanged (order
    relative to step 9 does not matter). The input is kept as
    `TSCS_spine.matches.preecho.csv`, the removed rows as
    `TSCS_spine.matches.suppressed-echo.csv`, and the step refuses to run
    twice. On the final accepted July 2026 build this removed exactly
    40,467 rows, partitioning the 176,261-row pre-echo file into 135,794
    kept rows plus the suppressed set; the v1.2 rebuild of 20 July removed
    the same 40,467 rows from its 177,045-row pre-echo file, keeping
    136,578. (Earlier notes quoting 40,427 / 131,699 or 40,428 / 135,682
    describe superseded artifacts.)

## 5. Validating a build before release

Every release must pass **three gates**. The build script runs the second
and third automatically at the end of a run; each can also be run by hand.

1. **Input-UID representation** (`check-spine`, step 6): every UID in the
   ten source sub-spines must be present in the spine, supplementary or
   matches output.
2. **Four-file internal validation** (`python cli.py validate-release
   <staging_dir>`): file names, exact schemas, logical row counts, UID and
   date formats, match referential integrity, SIC structure and duplicate
   checks, with SHA-256 hashes printed for the four CSVs. The script saves
   this as `release-validation.txt` in the staging directory.
3. **Population source alignment** (`python -m spine.source_alignment`;
   the build script passes the arguments): the spine's current populations
   are reconciled against the explicitly selected current CCEW, OSCR and
   CCNI snapshots and the Companies House data. The gate requires **zero
   unresolved and zero falsely-removed current source records**. Saved as
   `source-alignment.txt`.

   For Companies House, the current population is defined as the records
   seen in the newest monthly bulk snapshot **or a later dated refresh**
   (July 2026: 219,364 UIDs). Records seen only in the historical
   2000/2022 bootstrap files are *not* proof of current active status —
   a blank removal field there means "historically unknown" — and the
   status of CE-prefix CIO records is deferred to CCEW, whose data is
   newer and authoritative for them.

   Context for this gate: the corrected legacy (pre-July-2026) baseline
   showed **6,220 active source UIDs falsely marked removed across 5,556
   unique spine parents** (CCEW 5,197 UIDs / 5,194 parents; OSCR 107/105;
   CCNI 0/0; Companies House 916/916). The July 2026 rebuild reduced all
   of these to zero. Do not quote the older figures (6,912 / 6,212, and
   Companies House 1,608/1,605) in release documentation — they predate
   the corrected gate.

Additional checks:

- `build_spine.out`: scan for ERROR lines (removal-date inconsistencies,
  organisations that failed consolidation).
- Row counts and distributions: compare spine rows, supplementary rows,
  match counts by `match_type`, and spine counts by `source_register`
  against the most recent release (v1.0, March 2026: 770,923 spine rows;
  872,084 supplementary; 125,624 matches; 668,280 SIC rows. v1.1,
  July 2026: 783,606 spine rows, of which 386,122 active; 1,108,256
  supplementary; 135,794 matches; 474,843 SIC rows. v1.2, July 2026
  (current): 782,995 spine rows, of which 385,515 active; 1,108,831
  supplementary; 136,578 matches; 474,843 SIC rows; full tables in the
  guidance). Large unexplained swings in any cell mean stop and
  investigate.
- uid conventions: every spine uid starts GB-CHC/GB-COH/GB-SC/GB-MPR/
  GB-NIC/GB-COOP/GB-SHPE/GB-SHR; GB-CIS and GB-CQC appear only in matches.
- `python3 cli.py tex-table-spine` produces the release-notes counts table.
- Update the guidance page (schema, counts, changelog, download-date
  coverage) for every release, re-render the guidance PDF from the updated
  HTML, and visually check the rendered pages before packaging.
  `release_info.tex` is a deprecated historical record, not a second
  hand-maintained source of current counts — point readers to the guidance
  changelog and the archived validation records instead.

### Determinism (cross-seed acceptance completed 19 July 2026)

The pipeline's outputs are deterministic by construction: consolidation,
linkage tie-breaks, SIC extraction, supplementary seeding and echo
suppression all use explicit stable sort keys, so correctness does not
depend on the hash seed. Acceptance was completed on 19 July 2026: two
complete builds under `PYTHONHASHSEED=0` and `1` produced byte-identical
copies of all four release CSVs and all twenty per-source outputs, and the
full test suite (194 tests at the time; now 200) passed under each seed.
The four canonical files of the current release (v1.2, published 20 July
2026) are:

| File | Logical rows | SHA-256 |
|---|---:|---|
| `TSCS_spine.spine.csv` | 782,995 | `789cb4bd72b2020d0579b0efff8b8145251eae4d5ddea085db64234605422fe8` |
| `TSCS_spine.matches.csv` | 136,578 | `21a7f44205d6378ab2fe88890617beb364f0e435981b46c1c904358797188829` |
| `TSCS_spine.supplementary.csv` | 1,108,831 | `3ffcb7d7b4cb198c42b97238721fba28dc6299ebab909d79b6c702f0f660799a` |
| `TSCS_spine.SIC_codes.csv` | 474,843 | `2e6b5644900f3b05d4b91e538f4866f9fd218d2cc5b9dacba709d7c70e71feb6` |

Release lineage of these hashes: the v1.1 candidate signed on 19 July
2026 was corrected the same evening for an association-matching defect
(the RNIB/UCLH wrong cross-border match; see
`docs/spine-docs/rnib-wrong-match-investigation-2026-07-19.md`) and
published as v1.1 (spine `f5dc33ca…`, matches `4bd4e96b…`, supplementary
`39d1b01d…`, SIC `2e6b5644…`). On 20 July 2026 the `name - housing` rule
was extended to accept Mutuals Public Register counterparts and the
release was rebuilt from the matching step and republished as v1.2 under
the same download filename — spine, matches and supplementary changed;
the SIC file is byte-identical to v1.1. The v1.2 rebuild reused the
accepted preprocessing outputs and ran single-seed (the tweak changes
rule eligibility only, no ordering logic); gates and delta adjudication:
`docs/spine-docs/qa-rebuild-2026-07/housing-mutuals-rebuild-2026-07-20.md`.

After promoting the four CSVs into `../public_spine_data/`, re-hash them
and compare against this table (or the signed hashes of whichever release
is current).

### Packaging

Package with the exact-whitelist command — never publish a build staging
directory (it contains per-source intermediates, `.preseed`/`.preecho`
backups and QA sidecars):

```
python cli.py prepare-release <staging_dir> \
    <path>/tcss-organisation-register-guidance.html \
    <path>/tcss-organisation-register-guidance.pdf \
    <path>/LICENCE.txt <new_package_dir>
```

It re-validates the four CSVs, checks that the guidance HTML carries the
release's headline counts, copies exactly the seven payload files into a
new directory (refusing to overwrite), and writes a deterministic
transport ZIP. Archive alongside the package: the release-validation and
source-alignment reports, the frozen raw-input hash list, and the QA
sign-off. (There is currently no machine-readable release manifest — do
not refer to one; those four artefacts are the release record.)

### Cleanup after sign-off

Delete run intermediates (per-source sub-spines, `.tmp` files,
`.preseed`/`.preecho` backups, sidecars, superseded trial builds) only
after the release is signed off and the four CSVs are promoted and
re-hashed. Always retain: the raw register snapshots, the reconstructed
historical inputs of §3.1 (irreplaceable), the prior published release,
the frozen input hash lists, the unit/regression tests and the QA records
— these are reproducibility controls, not disposable build debris.

## 6. Known caveats and open items (July 2026 review)

- **Release lineage**: the published v1.0 ("Mar 2026") is the January 2026
  build with classification columns appended. An improved February rebuild
  (revised removal-date handling; 769,850 rows) exists in
  `tso-spine-files.March2026.zip` but was never published. The next release
  should state which lineage it continues.
- The July 2026 correctness fixes (this branch) deliberately change
  outputs: dates are now compared chronologically rather than as text,
  addresses are no longer truncated at city names, same-name organisations
  are no longer over-merged, and previously inert cross-border/CQC match
  rules now fire. Expect small, explainable count differences from v1.0.
- **Charity mergers are folded into the transferee (found 15 Sept 2026,
  Decelerator endings audit)**. The Find that Charity same-as table
  includes links from the CCEW Register of Mergers as well as
  re-registrations, and `build_public_spine.py` treats every `ftc` link as
  "same organisation". Checked against the Register of Mergers (5,944
  transferor rows, Sept 2026 copy): 5,031 transferors have no spine row and
  no removal date, 459 keep their own row, 439 are absent (mostly
  subsidiaries). Two effects: (a) the transferor's removal (a genuine
  ending, typically CCEW reason "Amalgamated"/"Transfer of funds"/"Ceased to
  exist") disappears from the spine, so E&W removal counts are short by
  roughly 250-450 events a year 2010-2025; (b) the transferee inherits the
  transferor's `registerdate` (earliest-date rule) - 2,811 of 3,331
  transferees in v1.1 carry a registration date earlier than their own CCEW
  registration (e.g. GB-CHC-1113140 Cornwall Hospice Care, registered 2006,
  shows 13/02/1981 from absorbed GB-CHC-281746 Mount Edgcumbe Hospice,
  removed 2008). Re-registrations (charity-reregistrations.csv, 1,931 pairs)
  are correctly folded and should stay so. Suggested fix: load the Register
  of Mergers (drkane/charity-lookups `ccew-register-of-mergers.csv`) as an
  exclusion list so transferor-transferee pairs are emitted as a
  `successor` relationship in the matches file rather than merged, keeping
  the transferor as its own removed row. Until then, consumers needing
  endings should append Register of Mergers transferors to the spine and
  take transferee registration dates from the raw CCEW extract.
- CQC and Care Inspectorate Scotland contribute matches only, by design.
- The supplementary file's `id_in_source` column is empty by construction.
- `prepare_zip.sh` is out of date (wrong file names, dead branch) — do not
  use it. Release packaging is `python cli.py prepare-release` (see §5),
  which validates, copies the exact seven-file payload and writes the
  transport ZIP.
- The Makefile's `setup-pyenv`/`setup-venv` targets are Unix-only and
  broken; use §2 instead.
