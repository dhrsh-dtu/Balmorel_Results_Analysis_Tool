#!/usr/bin/env bash
#
# One-command launcher for the Balmorel dashboard running on a REMOTE host.
#
# Run this from your LAPTOP (clone the repo there too if you haven't).
# It will:
#   1. SSH to the remote host and run ./launch.sh there
#      (streamlit in a detached tmux session — survives disconnects)
#   2. Open an SSH port-forward tunnel from your laptop in the background
#   3. Open the dashboard URL in your default browser
#
# Usage:
#   ./start_dashboard.sh                       # use $BALMOREL_DASH_HOST
#   ./start_dashboard.sh user@hostname         # override host for this run
#
# Prerequisites on your laptop:
#   • SSH key auth set up to the remote host (no password prompts)
#   • These env vars (add to ~/.bashrc / ~/.zshrc to persist):
#       BALMOREL_DASH_HOST   user@hostname (required, or pass as arg)
#         e.g.  dhrsh@hpclogin1.hpccluster.dtu.dk
#       BALMOREL_DASH_PATH   absolute path to the repo on the remote (required)
#         e.g.  /work3/dhrsh/Balmorel/Balmorel_Results_Analysis_Tool
#       BALMOREL_DASH_PORT   port to forward (optional, default: 8501)
#
# DTU HPC note: ssh round-robin can land you on hpclogin1/2/3/…  The tmux
# session lives on the specific node you started it on, so pass that node
# explicitly when re-attaching from a fresh session:
#   ./start_dashboard.sh dhrsh@hpclogin2.hpccluster.dtu.dk
#
# Stop everything with: ./stop_dashboard.sh

set -euo pipefail

HOST="${1:-${BALMOREL_DASH_HOST:-}}"
REPO_PATH="${BALMOREL_DASH_PATH:-}"
PORT="${BALMOREL_DASH_PORT:-8501}"

if [ -z "$HOST" ] || [ -z "$REPO_PATH" ]; then
    cat >&2 <<EOF
❌ Missing remote host or repo path.

Either pass the host as an argument:
    ./start_dashboard.sh <user>@<hostname>

Or set both env vars (add to ~/.bashrc / ~/.zshrc to persist):
    export BALMOREL_DASH_HOST="<user>@<hostname>"
        # e.g. dhrsh@hpclogin1.hpccluster.dtu.dk
    export BALMOREL_DASH_PATH="/path/to/Balmorel_Results_Analysis_Tool"
        # absolute path on the remote host
    # Optional:
    # export BALMOREL_DASH_PORT=8501

The repo path always comes from \$BALMOREL_DASH_PATH (rarely changes per session).
EOF
    exit 1
fi

# ── 1. Start dashboard on remote (idempotent — refuses duplicate) ──────────
# `bash -lc` so the remote shell sources .bashrc/.profile and picks up the
# conda env (assuming `conda activate balmorel-results-viz` is in there).
echo "▶ Starting dashboard on $HOST..."
ssh "$HOST" "bash -lc 'cd \"$REPO_PATH\" && ./launch.sh'"

# ── 2. Set up SSH tunnel in background (if not already up) ─────────────────
TUNNEL_PATTERN="ssh -f -N -L $PORT:localhost:$PORT $HOST"
if pgrep -f "$TUNNEL_PATTERN" >/dev/null 2>&1; then
    echo "▶ SSH tunnel localhost:$PORT → $HOST already running."
else
    echo "▶ Opening SSH tunnel localhost:$PORT → $HOST..."
    if ssh -f -N -L "$PORT:localhost:$PORT" "$HOST"; then
        echo "  ✓ Tunnel up."
    else
        echo "⚠ Couldn't open tunnel — port $PORT may already be in use locally."
        echo "  Check: lsof -iTCP:$PORT  (or: lsof -nP -iTCP:$PORT -sTCP:LISTEN)"
        exit 1
    fi
fi

# ── 3. Give streamlit a moment to bind, then open the browser ──────────────
sleep 2

URL="http://localhost:$PORT"
echo "▶ Opening $URL in default browser..."

if command -v open >/dev/null 2>&1; then
    open "$URL"
elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL" >/dev/null 2>&1 &
elif command -v start >/dev/null 2>&1; then
    start "$URL"
else
    echo "  (couldn't auto-detect a 'browser open' command — visit $URL manually)"
fi

cat <<EOF

✅ Dashboard reachable at $URL

   Stop everything (remote streamlit + local tunnel):
       ./stop_dashboard.sh

   Get a shell on the remote host:
       ssh $HOST

   Watch remote streamlit logs:
       ssh $HOST -t "tmux attach -t balmorel-dash"
EOF
