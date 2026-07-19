# TSCS Organisation Register builder

This repository builds the UK Third and Civil Society Sector Organisation
Register. `RUNBOOK.md` is the authoritative operating guide; this page is the
short Windows quick start.

## One-time setup on Windows

Install 64-bit Python 3.11, open Git Bash in this directory, and run:

```bash
py -3.11 -m venv .tso
.tso/Scripts/python.exe -m pip install --upgrade pip
.tso/Scripts/python.exe -m pip install -r requirements.txt
.tso/Scripts/python.exe -m pip install -r test-requirements.txt
.tso/Scripts/python.exe -m pytest
```

`requirements.txt` contains the pinned build and acquisition dependencies.
`test-requirements.txt` adds the pinned test runner. The old analysis notebooks
are not part of the release build; install their optional packages only when
needed:

```bash
.tso/Scripts/python.exe -m pip install -r requirements-visualise.txt
```

The commands call the virtual-environment interpreter directly, so activation
is optional. If you prefer activation in Git Bash, use:

```bash
source .tso/Scripts/activate
```

## Build a clean release candidate

First follow `RUNBOOK.md` section 3 to acquire and preserve the required raw
register snapshots under `../raw_data`. Then run the ten build steps into a new
staging directory:

```bash
./spine_bash_script.sh \
  ../published-v1.0 \
  ../public_spine_data/run-2026-07 \
  ../raw_data/ccew/ccew-publicextract.jul2026.csv \
  ../raw_data/oscr/CharityExport-17-Jul-2026.csv \
  ../raw_data/ccni/register_charitydetails_2026_07_18.csv
```

The first argument is the prior published release, used to carry forward
irreplaceable history. The second must be a path that does not already exist.
The final three arguments identify the current CCEW, OSCR and CCNI snapshots
selected for this release; recording them explicitly makes the population
status check reproducible.
The script defaults `PYTHONHASHSEED` to `0`, fails on the first error, runs all
ten steps, and finishes with both internal release validation and
population-level source alignment. Set an explicit alternative seed only for
determinism QA comparisons.

Never reuse a previous staging directory. A failed run is retained for
diagnosis; choose a new directory for the rerun.

## Validate or package

Validate an existing candidate:

```bash
.tso/Scripts/python.exe cli.py validate-release \
  ../public_spine_data/run-2026-07
```

After updating and rendering the canonical HTML/PDF guidance, create a new
exact-whitelist release directory:

```bash
./prepare_zip.sh \
  ../public_spine_data/run-2026-07 \
  ../../docs/guidance/tcss-organisation-register-guidance.html \
  ../../docs/guidance/tcss-organisation-register-guidance.pdf \
  ../published-v1.0/LICENCE.txt \
  ../published-v1.1-candidate
```

Packaging validates the data and guidance again, copies only the four canonical
CSVs, HTML, PDF, and licence, and creates a deterministic transport ZIP. It
does not commit, push, deploy, or overwrite an existing directory.

Website promotion is a separate, deliberate manual step after release sign-off;
see `RUNBOOK.md` section 6.

## Developer shortcuts

The Makefile uses the venv interpreter directly:

```bash
make install-deps
make install-test-deps
make test
make validate DATA_DIR=../public_spine_data/run-2026-07
```

On Unix, override `PYTHON=python3 VENV_PYTHON=.tso/bin/python`.

New source handlers should subclass `DataHandler` and be registered in
`handler_map` in `cli.py`. Changing source order changes the linkage method;
make such changes only with tests, QA, and documented release notes.
