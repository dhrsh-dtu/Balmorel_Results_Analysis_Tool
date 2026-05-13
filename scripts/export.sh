#!/usr/bin/env bash
# Convenience launcher for the export CLI on Linux / macOS.
#
# Sets up GAMS env vars then runs `python -m balmorel_dashboard <args>`.
# Adjust GAMS_DIR if your installation lives elsewhere.

set -euo pipefail

GAMS_DIR="${GAMS_DIR:-/appl/gams/50.4.1}"
ENV_NAME="${BALMOREL_CONDA_ENV:-pybalmorel}"

export PATH="${GAMS_DIR}:${PATH}"
export LD_LIBRARY_PATH="${GAMS_DIR}:${LD_LIBRARY_PATH:-}"

# shellcheck disable=SC1091
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "${ENV_NAME}"

cd "$(dirname "$0")/.."
exec python -m balmorel_dashboard "$@"
