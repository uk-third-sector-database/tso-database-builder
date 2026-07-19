#!/usr/bin/env bash
set -Eeuo pipefail

# Compatibility wrapper for the safe Python release packager.
# All five paths are resolved relative to this repository directory when they
# are not absolute. The output directory must not already exist.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

usage() {
    cat <<'EOF'
Usage:
  ./prepare_zip.sh DATA_DIR GUIDANCE_HTML GUIDANCE_PDF LICENCE_FILE OUTPUT_DIR

The command validates the four canonical TSCS CSVs, checks the guidance, and
creates an exact-whitelist release directory plus deterministic transport ZIP.
It never runs notebooks, Git commands, pushes, deploys, or shell wildcards.

Set PYTHON_BIN to override the interpreter. By default the script uses the
Windows project venv when present, otherwise python3.
EOF
}

if [[ $# -ne 5 ]]; then
    usage >&2
    exit 2
fi

if [[ -z "${PYTHON_BIN:-}" ]]; then
    if [[ -x ".tso/Scripts/python.exe" ]]; then
        PYTHON_BIN=".tso/Scripts/python.exe"
    else
        PYTHON_BIN="python3"
    fi
fi

export PYTHONUTF8=1
export PYTHONHASHSEED=0

"$PYTHON_BIN" cli.py prepare-release "$1" "$2" "$3" "$4" "$5"
