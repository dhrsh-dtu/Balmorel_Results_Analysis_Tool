#!/usr/bin/env bash
#
# Start the Balmorel dashboard on this machine (HPC) in the background.
#
#   ./start_dashboard.sh
#
# Uses tmux when available (re-attachable, survives SSH disconnect), falls
# back to nohup + a log file when tmux isn't installed. Prints the exact
# SSH tunnel command you should run from your laptop to view the dashboard.
#
# Override defaults via env vars before invocation:
#   BALMOREL_DASH_PORT     port to bind (default: 8501)
#   BALMOREL_DASH_LOG      log file path for the nohup fallback
#                          (default: /tmp/balmorel-dashboard.log)
#   BALMOREL_DASH_SESSION  tmux session name (default: balmorel-dash)

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

SESSION_NAME="${BALMOREL_DASH_SESSION:-balmorel-dash}"
LOG_FILE="${BALMOREL_DASH_LOG:-/tmp/balmorel-dashboard.log}"
PORT="${BALMOREL_DASH_PORT:-8501}"

# ── Sanity checks ──────────────────────────────────────────────────────────
# If `streamlit` isn't on PATH, try sourcing conda from common locations as
# a fallback (helps users who haven't added `conda activate …` to ~/.bashrc).
if ! command -v streamlit >/dev/null 2>&1; then
    for conda_sh in \
        "$HOME/miniconda3/etc/profile.d/conda.sh" \
        "$HOME/anaconda3/etc/profile.d/conda.sh" \
        "/work3/$USER/miniconda3/etc/profile.d/conda.sh" \
        "/opt/conda/etc/profile.d/conda.sh" \
        ; do
        if [ -f "$conda_sh" ]; then
            # shellcheck disable=SC1090
            . "$conda_sh"
            conda activate balmorel-results-viz 2>/dev/null || true
            if command -v streamlit >/dev/null 2>&1; then
                break
            fi
        fi
    done
fi

if ! command -v streamlit >/dev/null 2>&1; then
    cat >&2 <<EOF
❌ 'streamlit' not found on PATH.

Activate your env first, then re-run this script:
    conda activate balmorel-results-viz
    ./start_dashboard.sh
EOF
    exit 1
fi

# Refuse to start a duplicate
if command -v tmux >/dev/null 2>&1 && tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "⚠ Already running (tmux: $SESSION_NAME). Stop with ./stop_dashboard.sh."
    exit 0
fi
if pgrep -f "streamlit run streamlit_app.py" >/dev/null 2>&1; then
    PIDS="$(pgrep -f 'streamlit run streamlit_app.py' | tr '\n' ' ')"
    echo "⚠ streamlit already running (PID: $PIDS). Stop with ./stop_dashboard.sh."
    exit 0
fi

# ── Background with tmux if available, else nohup ──────────────────────────
if command -v tmux >/dev/null 2>&1; then
    tmux new-session -d -s "$SESSION_NAME" \
        "streamlit run streamlit_app.py --server.headless=true --server.port=$PORT"
    RUNNING_DESC="tmux: $SESSION_NAME"
else
    mkdir -p "$(dirname "$LOG_FILE")"
    nohup streamlit run streamlit_app.py --server.headless=true --server.port="$PORT" \
        > "$LOG_FILE" 2>&1 &
    RUNNING_DESC="PID $!, logs: $LOG_FILE"
fi

# ── Resolve a usable FQDN for the tunnel hint ──────────────────────────────
HOSTNAME_FQDN="$(hostname --fqdn 2>/dev/null || hostname 2>/dev/null || echo localhost)"
case "$HOSTNAME_FQDN" in
    *.*) ;;
    *)
        DNS_DOMAIN="$(dnsdomainname 2>/dev/null || true)"
        if [ -n "$DNS_DOMAIN" ]; then
            HOSTNAME_FQDN="${HOSTNAME_FQDN}.${DNS_DOMAIN}"
        fi
        ;;
esac

cat <<EOF
✅ Dashboard running: http://localhost:$PORT  ($RUNNING_DESC)

   Plain SSH (IDE Remote SSH auto-forwards — skip this line):
     ssh -L $PORT:localhost:$PORT $USER@$HOSTNAME_FQDN

   Stop: ./stop_dashboard.sh
EOF
