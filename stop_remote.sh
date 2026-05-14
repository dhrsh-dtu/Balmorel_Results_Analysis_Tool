#!/usr/bin/env bash
#
# Stop the Balmorel dashboard on the remote host AND tear down the
# local SSH tunnel that launch_remote.sh set up.
#
# Run this from your LAPTOP. Same env vars as launch_remote.sh.

set -euo pipefail

HOST="${BALMOREL_REMOTE_HOST:-}"
REPO_PATH="${BALMOREL_REMOTE_PATH:-}"
PORT="${BALMOREL_REMOTE_PORT:-8501}"

if [ -z "$HOST" ] || [ -z "$REPO_PATH" ]; then
    cat >&2 <<EOF
❌ Required env vars not set (BALMOREL_REMOTE_HOST, BALMOREL_REMOTE_PATH).
See ./launch_remote.sh for setup instructions.
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
