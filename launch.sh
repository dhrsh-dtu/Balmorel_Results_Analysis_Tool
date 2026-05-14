#!/usr/bin/env bash
#
# Launch the Balmorel dashboard in the background so the terminal stays usable.
#
#   ./launch.sh
#
# Uses tmux when available (re-attachable, survives SSH disconnect), falls
# back to nohup + a log file when tmux isn't installed.
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
STATE_FILE="$REPO_DIR/.dashboard_host"

# Write FQDN to state file so start_dashboard.sh on the laptop can discover
# which specific login node the session is on (HPC's /work3 is shared).
write_state() {
    (hostname --fqdn 2>/dev/null || hostname) > "$STATE_FILE"
}

# ── Sanity checks ──────────────────────────────────────────────────────────
# When this script is called via `ssh user@host "bash -lc 'launch.sh'"` from
# a laptop, the remote login shell often doesn't auto-source ~/.bashrc, so
# the user's `conda activate` line never fires. Try to source conda from
# common locations as a fallback before giving up.
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
    ./launch.sh
EOF
    exit 1
fi

# Refuse to start a duplicate (but refresh the state file in case it's stale)
if command -v tmux >/dev/null 2>&1 && tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    write_state
    cat <<EOF
⚠ Dashboard is already running in tmux session '$SESSION_NAME'.
  Attach:  tmux attach -t $SESSION_NAME
  Stop:    ./stop.sh
EOF
    exit 0
fi
if pgrep -f "streamlit run streamlit_app.py" >/dev/null 2>&1; then
    write_state
    PIDS="$(pgrep -f 'streamlit run streamlit_app.py' | tr '\n' ' ')"
    cat <<EOF
⚠ A streamlit instance for this app is already running (PID: $PIDS).
  Stop it first:  ./stop.sh
EOF
    exit 0
fi

# ── Background with tmux if available, else nohup ──────────────────────────
if command -v tmux >/dev/null 2>&1; then
    tmux new-session -d -s "$SESSION_NAME" \
        "streamlit run streamlit_app.py --server.headless=true --server.port=$PORT"
    write_state
    cat <<EOF
✅ Dashboard running in tmux session '$SESSION_NAME' on port $PORT.

  Attach (see live logs):   tmux attach -t $SESSION_NAME
                            (detach again with: Ctrl+b then d)
  Stop:                     ./stop.sh
EOF
else
    mkdir -p "$(dirname "$LOG_FILE")"
    nohup streamlit run streamlit_app.py --server.headless=true --server.port="$PORT" \
        > "$LOG_FILE" 2>&1 &
    PID=$!
    write_state
    cat <<EOF
✅ Dashboard running (PID $PID) on port $PORT.  [tmux not found, used nohup]

  Logs:  tail -f $LOG_FILE
  Stop:  ./stop.sh   (or: kill $PID)
EOF
fi

cat <<EOF

➡  Open the URL from your laptop:
       http://localhost:$PORT
   If Streamlit runs on a remote host, SSH-tunnel that port first:
       ssh -L $PORT:localhost:$PORT user@hostname
EOF
