#!/usr/bin/env bash
#
# Stop the Balmorel dashboard running on a REMOTE host AND tear down the
# local SSH tunnel that start_dashboard.sh set up.
#
# Run this from your LAPTOP. Same configuration as start_dashboard.sh.
#
# Usage:
#   ./stop_dashboard.sh                       # use $BALMOREL_DASH_HOST
#   ./stop_dashboard.sh user@hostname         # override entry host for this run

set -euo pipefail

ENTRY_HOST="${1:-${BALMOREL_DASH_HOST:-}}"
REPO_PATH="${BALMOREL_DASH_PATH:-}"
PORT="${BALMOREL_DASH_PORT:-8501}"

if [ -z "$ENTRY_HOST" ] || [ -z "$REPO_PATH" ]; then
    cat >&2 <<EOF
❌ Missing entry host or repo path.

Pass the entry host as an argument or set BALMOREL_DASH_HOST + BALMOREL_DASH_PATH.
See ./start_dashboard.sh for setup details.
EOF
    exit 1
fi

USER_PART="${ENTRY_HOST%%@*}"
if [ "$USER_PART" = "$ENTRY_HOST" ]; then
    USER_PART="$USER"
fi

# ── 1. Discover which specific node holds the session ──────────────────────
ACTUAL_FQDN="$(
    ssh -o ConnectTimeout=10 "$ENTRY_HOST" \
        "cat \"$REPO_PATH/.dashboard_host\" 2>/dev/null || true" \
    | head -1 | tr -d '[:space:]'
)"

if [ -n "$ACTUAL_FQDN" ]; then
    STOP_HOST="$USER_PART@$ACTUAL_FQDN"
    echo "▶ Stopping dashboard on $ACTUAL_FQDN..."
else
    STOP_HOST="$ENTRY_HOST"
    echo "▶ No state file found; running stop.sh on $ENTRY_HOST anyway..."
fi

ssh "$STOP_HOST" "bash -lc 'cd \"$REPO_PATH\" && ./stop.sh'" || true

# ── 2. Kill local SSH tunnel for this port ─────────────────────────────────
echo "▶ Killing local SSH tunnel on port $PORT..."
TUNNEL_PIDS="$(pgrep -f "ssh -f -N -L $PORT:localhost:$PORT" || true)"
if [ -n "$TUNNEL_PIDS" ]; then
    # shellcheck disable=SC2086
    kill $TUNNEL_PIDS 2>/dev/null || true
    echo "  ✓ Killed tunnel PID(s): $TUNNEL_PIDS"
else
    echo "  (no local tunnel found)"
fi

echo "✅ Done."
