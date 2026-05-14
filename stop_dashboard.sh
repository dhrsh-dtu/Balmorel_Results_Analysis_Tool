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

if [ -z "$REPO_PATH" ]; then
    cat >&2 <<EOF
❌ BALMOREL_DASH_PATH not set. See ./start_dashboard.sh for setup details.
EOF
    exit 1
fi

# Auto-derive entry host from /work3/<user>/ pattern (DTU HPC convention).
if [ -z "$ENTRY_HOST" ]; then
    case "$REPO_PATH" in
        /work3/*/*)
            AUTO_USER="${REPO_PATH#/work3/}"
            AUTO_USER="${AUTO_USER%%/*}"
            ENTRY_HOST="${AUTO_USER}@hpclogin1.hpccluster.dtu.dk"
            ;;
        *)
            cat >&2 <<EOF
❌ Couldn't auto-derive entry host. Set BALMOREL_DASH_HOST or pass as arg.
EOF
            exit 1
            ;;
    esac
fi

USER_PART="${ENTRY_HOST%%@*}"
if [ "$USER_PART" = "$ENTRY_HOST" ]; then
    USER_PART="$USER"
fi

# ── 0. On-cluster shortcut ─────────────────────────────────────────────────
# If we have local access to the repo, skip SSH and run stop.sh directly.
LOCAL_FQDN="$(hostname --fqdn 2>/dev/null || hostname)"

if [ -f "$REPO_PATH/stop.sh" ]; then
    echo "▶ Local access to $REPO_PATH detected — stopping on-cluster (no SSH needed)."

    ACTUAL_FQDN=""
    if [ -f "$REPO_PATH/.dashboard_host" ]; then
        ACTUAL_FQDN="$(head -1 "$REPO_PATH/.dashboard_host" | tr -d '[:space:]')"
    fi

    if [ -n "$ACTUAL_FQDN" ] && [ "$ACTUAL_FQDN" != "$LOCAL_FQDN" ]; then
        echo "▶ Session was on $ACTUAL_FQDN; SSHing there to stop tmux..."
        ssh "$USER_PART@$ACTUAL_FQDN" "bash -lc 'cd \"$REPO_PATH\" && ./stop.sh'" || true
    else
        ( cd "$REPO_PATH" && ./stop.sh ) || true
    fi

    echo "✅ Done. (No local tunnel to kill — you're on the cluster.)"
    exit 0
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
