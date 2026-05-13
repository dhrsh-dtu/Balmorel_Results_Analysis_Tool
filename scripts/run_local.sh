#!/usr/bin/env bash
# Convenience launcher for local dev on Linux / macOS.
#
# Activates an existing conda env (default name: pybalmorel) and runs the
# Streamlit dashboard. Adjust the env name with `--env <name>` if yours is
# different.

set -euo pipefail

ENV_NAME="pybalmorel"
PORT=8501

while [[ $# -gt 0 ]]; do
    case "$1" in
        --env) ENV_NAME="$2"; shift 2 ;;
        --port) PORT="$2"; shift 2 ;;
        -h|--help)
            echo "Usage: $0 [--env <conda-env>] [--port <number>]"
            echo "       Default env: pybalmorel, default port: 8501"
            exit 0 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# shellcheck disable=SC1091
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "${ENV_NAME}"

cd "$(dirname "$0")/.."

exec streamlit run streamlit_app.py --server.port "${PORT}"
