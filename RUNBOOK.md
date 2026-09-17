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

   **CCNI company numbers (new in v1.3).** The CCNI register download has
   always carried a `Company number` column, but the CCNI step used to throw
   it away, so the only Northern Irish company numbers ever to reach the
   builder were the 655 held in the 2024 seed file. They are now read from
   every download and written into `companyid` in the spine's Companies
   House format: the bare digits CCNI publishes (`652013`, `43374`, `306`)
   are zero-padded to six and prefixed `NI` → `NI652013`, `NI043374`,
   `NI000306`. Values that cannot be a company number are left blank rather
   than guessed at — anything that is not a plain run of digits, anything
   longer than six digits (CCNI holds a handful), and any single repeated
   digit, because `0` and `000000` are CCNI's way of saying “not a company”
   and `111111`/`999999`/`99999` are keyboard filler. Legacy R-prefixed
   Northern Irish numbers are knowingly out of scope.

   **Which number wins when a charity has several rows.** A charity normally
   appears in more than one CCNI file (the 2024 seed, later register
   downloads, the removals scrape). The step takes the FIRST non-blank
   company number across the charity's rows, and because the seed rows are
   read first this means “the seed number, unless the charity only ever had
   a downloaded one”. This is deliberately the opposite of the CCEW
   convention, which takes the LAST non-blank value: CCEW's later extracts
   are corrections, whereas CCNI's self-reported `Company number` field is
   the weaker source. Of the five charities where a seed number and a
   downloaded number both exist, two of the downloaded numbers are wrong
   (charity 107318 reports `999999` against seed NI661353; charity 107859
   reports `64999`, a truncation of seed NI649994).

   **Known-bad declarations.** `CCNI_KNOWN_BAD_COMPANY_NUMBERS` in
   `handler/preprocess_charity_regulators.py` suppresses two specific
   declarations that name a real but different company. Both were checked
   against Companies House and the CCNI register on 17 September 2026:

   | Charity | Declared | Why it is wrong |
   |---|---|---|
   | 108557 Healthy Living Centres Alliance Ltd | `NI653679` | That number is TAUGHMONAGH WORKS C.I.C. The charity's own company is NI653799, at the charity's own CCNI address, and four CCNI trustees are its directors — the digits are transposed |
   | 108948 Pomeroy Development Projects Ltd | `NI056404` | That number is MEDICINE WHEEL PRODUCTIONS (IRELAND) LIMITED of Derry, dissolved 2013. The charity's own company is NI056101, and all four CCNI trustees are its directors |

   The suppression is value-specific, so if CCNI corrects the field in a
   later download the corrected number passes straight through and no code
   change is needed. Do **not** “fix” these from Find that Charity: FTC has
   inherited both errors from CCNI and so is not independent evidence. With
   the number suppressed, each charity reaches its real company through the
   exact-name rule in step 5 instead. The step prints
   `CCNI known-bad company number suppressed for charity <number>: <value>`
   once per charity per download file that repeats the bad value, so expect
   several such lines in a build log — one per file, not one per charity.
4. Ten `python3 cli.py process-source <Handler> <in> <out>` calls →
   per-source `*.spine.csv` + `*.supplementary.csv` in `../public_spine_data/`.
5. `python3 cli.py build-spine <ten .spine.csv files> -o ../public_spine_data/TSCS_spine`
   The record linkage. **The file order is part of the method** (earlier
   sources take precedence, and most match rules only link a later record
   to an earlier one): ccew, oscr, ccni, mutuals, CH, co-ops, Scottish
   Housing Regulator, Social Housing England, Care Inspectorate Scotland,
   CQC. Console output (including per-organisation warnings) goes to
   `build_spine.out` — read it after every build.

   **Match rules changed in v1.3.** Two additions and one narrowing; the rest
   of the rule set is unchanged.

   - **`name - ni charity`** links a Northern Irish company (a Companies
     House record whose number begins `NI`) to the CCNI charity of the same
     normalised name, joined from the Companies House side as
     `name - housing` is. CCNI records a company number for only about a
     fifth of its register, so for the rest a shared name is the only
     evidence available — and a shared name on its own is weak. The rule
     therefore fires only when the name picks out exactly ONE organisation on
     each side: exactly one stored organisation holds that name for CCNI
     (either in its own right, or because it absorbed a CCNI charity earlier
     through an `ftc`/`oscr` link), and the incoming record is the only
     NI-prefixed Companies House record carrying it. The second test cannot
     be read off the name index — the incoming record is not stored yet — so
     `merge()` first counts NI-prefixed Companies House records per
     normalised name across the incoming batch and passes that census in.
     The census covers ONE call of `merge()`, i.e. one input file, so it
     assumes Companies House arrives as a single `CH.all.csv`, which is how
     `spine_bash_script.sh` loads it. **Do not split Companies House across
     several input files** — a second NI company on the same name would
     escape the guard. The charity is the surviving organisation (CCNI
     outranks Companies House in the load order) and the company's own name
     and address are kept in the supplementary file.

   - **`merge via bridge`** is not a match rule — no rule can produce it —
     but a record that two spine organisations were folded into one. When a
     single incoming record matched two stored organisations, the build used
     to let one absorb the record and leave the other holding a blank-uid
     association row, even where the incoming record was proof that the two
     stored organisations are the same body. It now folds them together, but
     only when every one of these holds:

     1. the record resolves to exactly two distinct stored organisations;
     2. those two come from different registers;
     3. neither link is the association-only `companyid - companyid`;
     4. both are still live spine organisations, so merges can never chain;
     5. the evidence clears the policy in `bridge_evidence_is_strong_enough()`
        — the two share a normalised name, or share it once THE / LTD /
        LIMITED and punctuation are set aside, or each is linked to the
        bridging record by an identifier rule with at least one of those
        links declared by a register about itself (`ftc`, `oscr`,
        `companyid - id_in_source`, `companyid - coop mutual`).

     The last condition is what keeps related-but-distinct bodies apart: a
     CQC provider's return often cites both a charity number and the company
     number of that charity's trustee company or trading subsidiary, which is
     good evidence of a relationship but not of identity. The organisation
     from the register loaded EARLIER survives (the file order of this step
     is the precedence order); the other leaves the spine, becomes an
     absorbed record of the survivor carrying the fixed match type
     `merge via bridge`, and hands over its supplementary rows and its own
     match rows.

     Every merge prints one line to `build_spine.out`:

     ```
     Bridge merge: <loser uid> -> <survivor uid> via <bridge uid> (<match types>)
     ```

     **Read these after every build.** They are the complete list of
     organisations that left the spine by merging, and each one should be
     defensible on its own evidence. `spine/compare_releases.py` (§5) collects
     them with organisation names attached, which is the easier read.

     Because a merged-away uid is no longer a spine row, the two uid-keyed
     linkage tables (the Find that Charity same-as table and the historic
     OSCR linkage) are looked up through an alias map: a link naming the
     merged-away organisation now resolves to its survivor instead of
     silently matching nothing.

   - **`companyid - coop mutual` narrowed.** A co-operative's registered
     number identifies a Companies House company or a Mutuals Public Register
     society — never a charity. The rule used to link EVERY organisation the
     number index returned as soon as one of them qualified, which let a
     Scottish charity number collide with an identically formatted Scottish
     company number: the co-op GB-COOP-R009306 linked both CITY CABS
     (EDINBURGH) LIMITED (GB-COH-SC033518) and the unrelated OSCR charity
     2nd Inchinnan Brownie Unit (GB-SC-SC033518). In v1.2 that surfaced as a
     harmless blank-uid row — it is published as an example match row in the
     guidance — but it is exactly the kind of evidence a bridge merge would
     act on. Only organisations that actually hold the number on a qualifying
     Companies House or Mutuals record are matched now.

   **Keep the two match-type lists in step.** `MATCHTYPE_ORDER` in
   `spine/build_public_spine.py` (which sets rule precedence) and
   `MATCH_TYPES` in `spine/release.py` (the values release validation will
   accept) are maintained by hand in two modules. A type added to one and not
   the other either loses its precedence or fails validation at the end of
   the build. `spine/test_release.py` now asserts that the two lists hold
   exactly the same names, so the drift cannot go unnoticed — but a new
   match type still has to be added to both by hand.
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
   v1.3 (17 September 2026): 705,270 built rows plus 407,348 rows seeded
   from the prior release gave 1,112,618 supplementary rows (of v1.0's
   872,084 prior rows, 463,220 were already present in the fresh build and
   1,516 belong to organisations no longer represented in the release).
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
    describe superseded artifacts.) The v1.3 rebuild of 17 September removed
    41,122 rows from its 180,984-row pre-echo file, keeping 139,862.

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
  guidance. v1.3, September 2026 — spine rows / active / supplementary /
  matches / SIC rows: 781,176 / 384,096 / 1,112,618 / 139,862 /
  474,842). Large unexplained swings in any cell mean stop and
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

### Delta adjudication against the prior release

The three gates say a build is internally sound; they do not say *what
changed*. Since v1.3 every candidate release is also adjudicated line by
line against the release it replaces:

```
python spine/compare_releases.py <prior_release_dir> <new_staging_dir> <out_dir>
```

Both directories must hold the four release CSVs, and nothing else is read,
so the comparison is reproducible from published artefacts alone. It writes
`delta-report.md` plus supporting CSVs into `<out_dir>`:

1. **Headline counts** — the four files, the active/removed split and
   distinct uids, prior against new with the differences.
2. **Spine uids removed** — every organisation in the prior spine and not in
   the new one, *and where it went*: whether it reappears as the junior side
   of a match row, under which match type, and which organisation absorbed
   it, broken down by uid prefix and by status
   (`spine-uids-removed.csv`). An organisation that leaves the spine without
   reappearing anywhere is the thing to chase.
3. **Spine uids added** — organisations new to the spine
   (`spine-uids-added.csv`), including those separated out of a prior
   over-merge.
4. **Match rows** — totals by `match_type` prior against new, rows added and
   removed by type (`match-rows-added.csv`, `match-rows-removed.csv`), the
   match types the release introduces, and a bridge-merge table giving both
   parties' names and the bridging record (`bridge-merges.csv`). This is the
   readable version of the `Bridge merge:` lines in `build_spine.out`.
5. **Field changes for surviving organisations** — name, normalised name,
   postcode, registration date, removal date, CIC flag and the two
   classification columns, with removal-date changes classified (revived:
   had a date, now blank; newly removed; date changed) and a sample of
   changed rows (`spine-field-changes.csv`).
6. **Supplementary** — rows added and removed by source register, and which
   organisations' variant records changed
   (`supplementary-rows-added.csv`, `supplementary-rows-removed.csv`,
   `supplementary-uids-changed.csv`).
7. **SIC codes** — organisations gaining or losing codes
   (`sic-uids-changed.csv`).
8. **Northern Ireland** — the section written for this release: what
   evidence stands behind each CCNI charity-to-company link, charities that
   absorbed more than one company, postcode agreement between a charity and
   the company folded into it, and CCNI charities that were removed in the
   prior spine but are active in the new one
   (`ni-charity-company-absorptions.csv`, `ni-charities-multi-company.csv`,
   `ni-charities-revived.csv`).

Keep the report and its CSVs with the release record. The adjudication is
the evidence that every count movement was intended rather than merely
tolerated.

**Builds run from a frozen copy of the repo.** A full build takes hours, so
it is normal to copy the repo to `code/tso-build-snapshot-<tag>` and run the
build there, leaving the working repo free for further code edits. The copy
is the build's code of record — name it in the QA notes — and it is deleted
once the release is signed off. Never promote CSVs out of a snapshot whose
code does not match what was committed.

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

The equivalent v1.3 table — four logical row counts and SHA-256 hashes:

| File | Logical rows | SHA-256 |
|---|---:|---|
| `TSCS_spine.spine.csv` | 781,176 | `1038502982df3dcf52c3cc8ac8767884c293102f862d8951d658e54fcf1abafd` |
| `TSCS_spine.matches.csv` | 139,862 | `f4720b41c5aebbd6e407adec310b460fbf9a8d95001341f60547178c693b192f` |
| `TSCS_spine.supplementary.csv` | 1,112,618 | `3ecc1e4e16f7fb0549be69b231097cd2217de11895ac30ea518562931233c757` |
| `TSCS_spine.SIC_codes.csv` | 474,842 | `7088679d373200a14858bddc9f7bd6fe0a1cd71fc8317d455f37c896f409e025` |

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
- **Name-only Northern Ireland links are weaker than identifier-confirmed
  ones (v1.3).** Where a CCNI charity and a Northern Irish company are
  linked by exact name alone, the two records agree on postcode about 52% of
  the time, against about 79% for pairs confirmed by a company number. Much
  of that gap is not error: a Companies House registered office is often the
  address of the charity's accountant or solicitor, while CCNI holds the
  charity's own address. Treat the name-only links as good but not certain,
  and use the `match_type` column to separate them.
- **Registration dates move earlier when a company is folded in.** The
  spine's `registerdate` is the earliest date across all linked source
  records, so a CCNI charity linked to an older company shows the company's
  incorporation date rather than its charity registration date. This is the
  designed rule (the same one behind the charity-merger effect above), but it
  became visible for Northern Ireland only in v1.3, when NI companies started
  linking in numbers.
- **Clyde Valley Housing Association is still two organisations** (OSCR
  SC037244 and Mutuals 2489RS). The bridge merge does not fire because the
  Scottish Housing Regulator record names it “… Ltd” while the other side
  says “… Limited”, and the name rules compare normalised names, which keep
  the difference. Follow-up: normalise Ltd/Limited in the pipeline's own name
  normalisation (`handler/base_definitions.py`), not only in the
  bridge-merge comparison form.
- **CCNI company numbers are self-reported.** Roughly 0.3% of the numbers
  CCNI publishes name a different company. Two verified cases are suppressed
  by name (§4 step 3); others may remain. Find that Charity has inherited at
  least those two errors from CCNI, so it cannot be used as an independent
  check.
- **Two CCNI charities are classified as CICs** — uHub Therapy Centre and
  RiChmusicNI both resolve to companies registered as Community Interest
  Companies, so `is_cic` is true and `cso_type` is CIC rather than Charity.
  That is what the registers say; it is unusual but not a pipeline error.
