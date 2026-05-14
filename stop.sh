#!/usr/bin/env bash
#
# Stop the Balmorel dashboard launched by launch.sh.
#
# Tears down both the tmux session (if any) and any streamlit process
# running streamlit_app.py for this repo. Safe to run repeatedly.

set -euo pipefail

SESSION_NAME="${BALMOREL_DASH_SESSION:-balmorel-dash}"
STOPPED=0

if command -v tmux >/dev/null 2>&1 && tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    tmux kill-session -t "$SESSION_NAME"
    echo "✅ Stopped tmux session '$SESSION_NAME'."
    STOPPED=1
fi

if pgrep -f "streamlit run streamlit_app.py" >/dev/null 2>&1; then
    pkill -f "streamlit run streamlit_app.py" || true
    echo "✅ Killed streamlit processes running streamlit_app.py."
    STOPPED=1
fi

if [ "$STOPPED" -eq 0 ]; then
    echo "ℹ No running dashboard found."
fi
