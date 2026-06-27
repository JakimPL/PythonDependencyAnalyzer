#!/usr/bin/env bash

set -euo pipefail

# Export notebooks/example.py to a self-contained WASM site that runs PDA
# entirely in the browser (Pyodide). The output directory can be uploaded
# as-is to any static host (e.g. cPanel public_html/).
#
# Usage:
#   scripts/export-wasm.sh [output-dir]
#
# Requires marimo on PATH (or set MARIMO=/path/to/marimo).

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
out_dir="${1:-$repo_root/site}"
marimo_bin="${MARIMO:-marimo}"
notebook="$repo_root/notebooks/example.py"

cd "$repo_root"

if ! command -v "$marimo_bin" >/dev/null 2>&1; then
    echo "error: '$marimo_bin' not found." >&2
    echo "Install the notebook extra into your environment:" >&2
    echo "    pip install -e \".[notebook]\"" >&2
    echo "or point MARIMO at an existing marimo binary:" >&2
    echo "    MARIMO=/path/to/marimo scripts/export-wasm.sh" >&2
    exit 1
fi

"$marimo_bin" export html-wasm "$notebook" \
    --output "$out_dir" \
    --mode run \
    --no-show-code \
    --force

cp notebooks/utils/wasm.py "$out_dir/wasm.py"

bundle="$out_dir/pda-bundle.zip"
rm -f "$bundle"
zip -r -q "$bundle" src/pda config \
    -x '*.pyc' -x '*/__pycache__/*'

echo "WASM site written to: $out_dir"
echo "Bundle: $bundle"
