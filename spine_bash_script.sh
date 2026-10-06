#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

usage() {
    cat <<'EOF'
Usage:
  ./spine_bash_script.sh PRIOR_RELEASE_DIR OUTPUT_DIR \
    CCEW_CURRENT_CSV OSCR_CURRENT_CSV CCNI_CURRENT_CSV

PRIOR_RELEASE_DIR must contain the prior published supplementary and matches
CSVs. OUTPUT_DIR is a new, clean staging directory and must not already exist.
The final three arguments are the explicitly selected current charity-register
snapshots used by the population-level source-alignment release gate.
Paths are resolved relative to this builder directory unless absolute.

The script expects raw inputs under ../raw_data. Set PYTHON_BIN to override the
interpreter; by default it uses .tso/Scripts/python.exe when present, otherwise
python3.
EOF
}

if [[ $# -ne 5 ]]; then
    usage >&2
    exit 2
fi

PRIOR_RELEASE_DIR="$1"
OUTPUT_DIR="$2"
CCEW_CURRENT_CSV="$3"
OSCR_CURRENT_CSV="$4"
CCNI_CURRENT_CSV="$5"
RAW_DATA_DIR="../raw_data"

if [[ -z "${PYTHON_BIN:-}" ]]; then
    if [[ -x ".tso/Scripts/python.exe" ]]; then
        PYTHON_BIN=".tso/Scripts/python.exe"
    else
        PYTHON_BIN="python3"
    fi
fi

export PYTHONUTF8=1
export PYTHONHASHSEED="${PYTHONHASHSEED:-0}"

trap 'status=$?; echo "ERROR: build failed at line ${LINENO}; partial files remain in ${OUTPUT_DIR} for diagnosis." >&2; exit "$status"' ERR

for prior_file in \
    TSCS_spine.supplementary.csv \
    TSCS_spine.matches.csv
do
    if [[ ! -f "$PRIOR_RELEASE_DIR/$prior_file" ]]; then
        echo "ERROR: prior release file is missing: $PRIOR_RELEASE_DIR/$prior_file" >&2
        exit 2
    fi
done

for current_file in \
    "$CCEW_CURRENT_CSV" \
    "$OSCR_CURRENT_CSV" \
    "$CCNI_CURRENT_CSV"
do
    if [[ ! -f "$current_file" ]]; then
        echo "ERROR: current source-alignment snapshot is missing: $current_file" >&2
        exit 2
    fi
done

if [[ ! -d "$RAW_DATA_DIR" ]]; then
    echo "ERROR: raw-data directory is missing: $RAW_DATA_DIR" >&2
    exit 2
fi

BUILD_LOCK_DIR="$RAW_DATA_DIR/.tscs-spine-build.lock"
if ! mkdir "$BUILD_LOCK_DIR" 2>/dev/null; then
    echo "ERROR: another build may be preprocessing the shared raw-data directory." >&2
    echo "Lock directory: $BUILD_LOCK_DIR" >&2
    echo "If no build is running, remove that empty stale lock directory and retry." >&2
    exit 2
fi
trap 'rmdir "$BUILD_LOCK_DIR" 2>/dev/null || true' EXIT

if [[ -e "$OUTPUT_DIR" ]]; then
    echo "ERROR: output directory already exists; use a new clean staging path: $OUTPUT_DIR" >&2
    exit 2
fi
mkdir -p "$OUTPUT_DIR"

SPINE_INPUTS=(
    "$OUTPUT_DIR/ccew.spine.csv"
    "$OUTPUT_DIR/oscr.spine.csv"
    "$OUTPUT_DIR/ccni.spine.csv"
    "$OUTPUT_DIR/mutuals.spine.csv"
    "$OUTPUT_DIR/CH_all.spine.csv"
    "$OUTPUT_DIR/CoOps.spine.csv"
    "$OUTPUT_DIR/ScotHousingReg.spine.csv"
    "$OUTPUT_DIR/SocialHousingEngland.spine.csv"
    "$OUTPUT_DIR/CareInspectScot.spine.csv"
    "$OUTPUT_DIR/CQC.spine.csv"
)
OUTPUT_BASE="$OUTPUT_DIR/TSCS_spine"

echo "Step 1/10: preprocess register snapshots"
"$PYTHON_BIN" handler/preprocess.py

echo "Step 2/10: preprocess Companies House"
"$PYTHON_BIN" cli.py preprocess-ch "$RAW_DATA_DIR/CH.all.csv"

echo "Step 3/10: preprocess charity registers"
"$PYTHON_BIN" cli.py process-charity-source ccni
"$PYTHON_BIN" cli.py process-charity-source oscr
"$PYTHON_BIN" cli.py process-charity-source ccew

echo "Step 4/10: create the ten source sub-spines"
"$PYTHON_BIN" cli.py process-source CompaniesHouse "$RAW_DATA_DIR/CH.all.csv" "$OUTPUT_DIR/CH_all.spine.csv"
"$PYTHON_BIN" cli.py process-source CareInspScot "$RAW_DATA_DIR/CareInspectScot.all.csv" "$OUTPUT_DIR/CareInspectScot.spine.csv"
"$PYTHON_BIN" cli.py process-source CQC "$RAW_DATA_DIR/CareQualityCommission.all.csv" "$OUTPUT_DIR/CQC.spine.csv"
"$PYTHON_BIN" cli.py process-source CoOps "$RAW_DATA_DIR/co_ops.all.csv" "$OUTPUT_DIR/CoOps.spine.csv"
"$PYTHON_BIN" cli.py process-source Mutuals "$RAW_DATA_DIR/mutuals.all.csv" "$OUTPUT_DIR/mutuals.spine.csv"
"$PYTHON_BIN" cli.py process-source SocialHousingEng "$RAW_DATA_DIR/SocialHousingEng.all.csv" "$OUTPUT_DIR/SocialHousingEngland.spine.csv"
"$PYTHON_BIN" cli.py process-source ScotHousingReg "$RAW_DATA_DIR/ScotHousingReg.all.csv" "$OUTPUT_DIR/ScotHousingReg.spine.csv"
"$PYTHON_BIN" cli.py process-source CCEW "$RAW_DATA_DIR/ccew.all.csv" "$OUTPUT_DIR/ccew.spine.csv"
"$PYTHON_BIN" cli.py process-source CCNI "$RAW_DATA_DIR/ccni.all.csv" "$OUTPUT_DIR/ccni.spine.csv"
"$PYTHON_BIN" cli.py process-source OSCR "$RAW_DATA_DIR/oscr.all.csv" "$OUTPUT_DIR/oscr.spine.csv"

echo "Step 5/10: link sources in the method-defining precedence order"
"$PYTHON_BIN" cli.py build-spine "${SPINE_INPUTS[@]}" -o "$OUTPUT_BASE" 2>&1 \
    | tee "$OUTPUT_DIR/build_spine.out"

echo "Step 6/10: verify every input UID is represented"
"$PYTHON_BIN" cli.py check-spine "${SPINE_INPUTS[@]}" -o "$OUTPUT_BASE"

echo "Step 7/10: build the SIC-code lookup"
"$PYTHON_BIN" cli.py build-sic-codes-list \
    "$RAW_DATA_DIR/CH.all.csv" \
    "$OUTPUT_BASE.matches.csv" \
    "$OUTPUT_BASE.SIC_codes.csv"

echo "Step 8/10: add civil-society classifications"
"$PYTHON_BIN" cli.py add-cso-type \
    "$OUTPUT_BASE.spine.csv" \
    "$OUTPUT_BASE.SIC_codes.csv"

echo "Step 9/10: carry forward historical supplementary values"
"$PYTHON_BIN" cli.py seed-supplementary \
    "$OUTPUT_BASE.supplementary.csv" \
    "$OUTPUT_BASE.spine.csv" \
    "$OUTPUT_BASE.matches.csv" \
    "$PRIOR_RELEASE_DIR/TSCS_spine.supplementary.csv"

echo "Step 10/10: suppress bootstrap-echo match rows"
"$PYTHON_BIN" cli.py suppress-echo-matches \
    "$OUTPUT_BASE.matches.csv" \
    "$PRIOR_RELEASE_DIR/TSCS_spine.matches.csv"

echo "Release validation"
"$PYTHON_BIN" cli.py validate-release "$OUTPUT_DIR" 2>&1 \
    | tee "$OUTPUT_DIR/release-validation.txt"

echo "Population source-alignment validation"
"$PYTHON_BIN" -m spine.source_alignment \
    --spine "$OUTPUT_BASE.spine.csv" \
    --matches "$OUTPUT_BASE.matches.csv" \
    --ccew "$CCEW_CURRENT_CSV" \
    --oscr "$OSCR_CURRENT_CSV" \
    --ccni "$CCNI_CURRENT_CSV" \
    --companies-house "$RAW_DATA_DIR/CH.all.csv" 2>&1 \
    | tee "$OUTPUT_DIR/source-alignment.txt"

echo "SUCCESS: validated build staged in $OUTPUT_DIR"
echo "Next: update and render the guidance, then run: $PYTHON_BIN cli.py prepare-release (see RUNBOOK section 5)."
