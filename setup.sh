#!/usr/bin/env bash
#
# One-command setup for Balmorel Results Analysis Tool.
#
#   ./setup.sh
#
# Strategy:
#   • If `conda` is available — create or update the conda env defined in
#     environment.yml, then `pip install -e .` inside it.
#   • Otherwise — fall back to `pip install` in the currently active Python.
#
# After install, checks for a GAMS installation and prints a warning (not an
# error) if it isn't found — `--serve --no-export` still works on archives
# someone else exported.

set -euo pipefail

ENV_NAME="balmorel-results-viz"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

# ── Locate/use conda or fall back to pip ───────────────────────────────────
NEXT_STEP=""
if command -v conda >/dev/null 2>&1; then
    echo "▶ Using conda to set up env '$ENV_NAME'..."

    # shellcheck disable=SC1091
    source "$(conda info --base)/etc/profile.d/conda.sh"

    if conda env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
        echo "  Env '$ENV_NAME' already exists — updating dependencies."
        conda env update -n "$ENV_NAME" -f environment.yml --prune
    else
        conda env create -n "$ENV_NAME" -f environment.yml
    fi

    conda activate "$ENV_NAME"
    echo "▶ Installing the dashboard package in editable mode..."
    pip install -e . --quiet

    NEXT_STEP="conda activate $ENV_NAME"
else
    echo "▶ conda not found — installing into the current Python env."
    echo "  Using: $(command -v python)"

    # Python 3.10+ required (pybalmorel needs it). Fail fast with a clear
    # message if the active Python is too old — otherwise pip errors out
    # halfway through with a wall of red text about incompatible versions.
    PY_OK=$(python -c 'import sys; print(1 if sys.version_info >= (3, 10) else 0)')
    if [ "$PY_OK" != "1" ]; then
        PY_VER=$(python -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')
        cat >&2 <<EOF

❌ Python 3.10+ is required, but the active Python is $PY_VER ($(command -v python)).

Either:
  • Activate a Python 3.10+ environment (e.g. python3.11 -m venv .venv && source .venv/bin/activate), or
  • Install conda/miniconda — setup.sh will then create a clean 'balmorel-results-viz' env automatically.
EOF
        exit 1
    fi

    pip install --upgrade pip --quiet
    pip install -r requirements.txt -r requirements-export.txt -e . --quiet

    NEXT_STEP="# (current Python env already has everything)"
fi

# ── GAMS sanity check (warn only) ──────────────────────────────────────────
echo
echo "▶ Checking for a GAMS installation..."
GAMS_FOUND=""

# Scan PATH + GAMS_SYSDIR + GAMSDIR for the marker file optgams.def
IFS_BACKUP="${IFS:-}"
IFS=":"
for d in ${PATH} "${GAMS_SYSDIR:-}" "${GAMSDIR:-}"; do
    if [ -n "$d" ] && [ -f "$d/optgams.def" ]; then
        GAMS_FOUND="$d"
        break
    fi
done
IFS="$IFS_BACKUP"

if [ -n "$GAMS_FOUND" ]; then
    echo "  ✓ GAMS found at: $GAMS_FOUND"
else
    cat <<'EOF'
  ⚠ No GAMS installation detected on PATH / GAMS_SYSDIR / GAMSDIR.

    You can still:
      • View existing scenario archives:
          python -m balmorel_dashboard --serve --no-export /path/to/Balmorel
      • Upload zips received from a collaborator via the dashboard UI.

    To enable full exports, add your GAMS install to PATH, or pass
    --gams-dir /path/to/gams to the CLI at run time.
EOF
fi

# ── Final message ──────────────────────────────────────────────────────────
cat <<EOF

✅ Setup complete.

Next steps:
  $NEXT_STEP
  python -m balmorel_dashboard --serve /path/to/Balmorel

Or, just inspect what scenarios are present:
  python -m balmorel_dashboard --list-scenarios /path/to/Balmorel
EOF
