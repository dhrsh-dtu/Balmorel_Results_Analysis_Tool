#!/usr/bin/env bash
#
# Stop the Balmorel dashboard running on a REMOTE host AND tear down the
# local SSH tunnel that start_dashboard.sh set up.
#
# Run this from your LAPTOP. Same configuration as start_dashboard.sh.
#
# Usage:
#   ./stop_dashboard.sh                       # use $BALMOREL_DASH_HOST
#   ./stop_dashboard.sh user@hostname         # override host for this run

set -euo pipefail

HOST="${1:-${BALMOREL_DASH_HOST:-}}"
REPO_PATH="${BALMOREL_DASH_PATH:-}"
PORT="${BALMOREL_DASH_PORT:-8501}"

if [ -z "$HOST" ] || [ -z "$REPO_PATH" ]; then
    cat >&2 <<EOF
❌ Missing remote host or repo path.

Pass the host as an argument or set BALMOREL_DASH_HOST + BALMOREL_DASH_PATH.
See ./start_dashboard.sh for setup details.
EOF
    exit 1
fi

echo "▶ Stopping dashboard on $HOST..."
ssh "$HOST" "bash -lc 'cd \"$REPO_PATH\" && ./stop.sh'" || true

echo "▶ Killing local SSH tunnel on port $PORT..."
TUNNEL_PIDS="$(pgrep -f "ssh -f -N -L $PORT:localhost:$PORT $HOST" || true)"
if [ -n "$TUNNEL_PIDS" ]; then
    # shellcheck disable=SC2086
    kill $TUNNEL_PIDS 2>/dev/null || true
    echo "  ✓ Killed tunnel PID(s): $TUNNEL_PIDS"
else
    echo "  (no local tunnel found)"
fi

echo "✅ Done."
