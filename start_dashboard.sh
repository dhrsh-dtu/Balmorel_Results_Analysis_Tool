#!/usr/bin/env bash
#
# One-command launcher for the Balmorel dashboard running on a REMOTE host.
#
# Run this from your LAPTOP. The script:
#   1. SSHes to any login node (the "entry host") to read the state file
#      `<repo>/.dashboard_host` — discovers which specific node already has
#      a running dashboard (HPC's filesystem is shared across login nodes,
#      so any one of them can read it).
#   2. If a session exists on a specific node, SSHes there to verify it's
#      alive and refresh the state file.
#   3. If no session exists, starts one on the entry host (whatever the
#      ssh round-robin landed on) and re-reads the state file to find the
#      node hostname.
#   4. Opens an SSH port-forward tunnel to that specific node in the
#      background.
#   5. Opens the dashboard URL in your default browser.
#
# Net effect: you never type a specific login node. Set any entry host
# once (specific node or round-robin alias), the script tracks where the
# tmux session actually lives.
#
# Usage:
#   ./start_dashboard.sh                       # auto-derive entry host
#   ./start_dashboard.sh user@hostname         # override entry host for this run
#
# Prerequisites on your laptop:
#   • SSH key auth set up to the entry host (no password prompts)
#   • One env var (add to ~/.bashrc / ~/.zshrc to persist):
#       BALMOREL_DASH_PATH   absolute path to the repo on the remote (required)
#         e.g.  /work3/dhrsh/Balmorel/Balmorel_Results_Analysis_Tool
#
#   On DTU HPC, the entry host is auto-derived from the path: any
#   `/work3/<username>/…` path yields `<username>@hpclogin1.hpccluster.dtu.dk`
#   as the default entry, and the state file re-routes to wherever the
#   tmux session actually lives. To override (other HPCs, custom user):
#       BALMOREL_DASH_HOST   user@<entry-host>  (optional)
#       BALMOREL_DASH_PORT   port to forward (optional, default: 8501)
#
# Stop everything with: ./stop_dashboard.sh

set -euo pipefail

ENTRY_HOST="${1:-${BALMOREL_DASH_HOST:-}}"
REPO_PATH="${BALMOREL_DASH_PATH:-}"
PORT="${BALMOREL_DASH_PORT:-8501}"

if [ -z "$REPO_PATH" ]; then
    cat >&2 <<EOF
❌ BALMOREL_DASH_PATH not set.

Add to your laptop ~/.bashrc / ~/.zshrc:
    export BALMOREL_DASH_PATH="/path/to/Balmorel_Results_Analysis_Tool"
        # absolute path on the remote host
EOF
    exit 1
fi

# Auto-derive entry host from /work3/<user>/ pattern (DTU HPC convention).
# Defaults to hpclogin1; state-file discovery re-routes if the session is
# actually on a different login node.
if [ -z "$ENTRY_HOST" ]; then
    case "$REPO_PATH" in
        /work3/*/*)
            AUTO_USER="${REPO_PATH#/work3/}"
            AUTO_USER="${AUTO_USER%%/*}"
            ENTRY_HOST="${AUTO_USER}@hpclogin1.hpccluster.dtu.dk"
            echo "▶ Auto-derived entry host: $ENTRY_HOST"
            ;;
        *)
            cat >&2 <<EOF
❌ Couldn't auto-derive entry host (BALMOREL_DASH_PATH not under /work3/<user>/).

Pass one as an argument or set BALMOREL_DASH_HOST:
    ./start_dashboard.sh <user>@<any-login-node>
    export BALMOREL_DASH_HOST="<user>@<any-login-node>"
EOF
            exit 1
            ;;
    esac
fi

# Pull the user prefix off the entry host so we can re-build "user@<actual-node>"
USER_PART="${ENTRY_HOST%%@*}"
if [ "$USER_PART" = "$ENTRY_HOST" ]; then
    USER_PART="$USER"
fi

# ── 0. On-cluster shortcut ─────────────────────────────────────────────────
# If we have local access to the repo (we're already on HPC's shared
# filesystem), skip SSH entirely. Avoids password prompts, the DTU login
# banner noise, and any `bash -lc` conda-activation issues. Then print the
# laptop-side tunnel command — the user still needs that to view in browser.
LOCAL_FQDN="$(hostname --fqdn 2>/dev/null || hostname)"

if [ -f "$REPO_PATH/launch.sh" ]; then
    echo "▶ Local access to $REPO_PATH detected — running on-cluster (no SSH needed)."

    ACTUAL_FQDN=""
    if [ -f "$REPO_PATH/.dashboard_host" ]; then
        ACTUAL_FQDN="$(head -1 "$REPO_PATH/.dashboard_host" | tr -d '[:space:]')"
    fi

    if [ -n "$ACTUAL_FQDN" ] && [ "$ACTUAL_FQDN" != "$LOCAL_FQDN" ]; then
        # State file points to a different login node — SSH there so the
        # idempotent re-launch check sees the actual tmux session.
        echo "▶ Existing session on $ACTUAL_FQDN (we're on $LOCAL_FQDN); SSHing there to refresh..."
        ssh "$USER_PART@$ACTUAL_FQDN" "bash -lc 'cd \"$REPO_PATH\" && ./launch.sh'"
    else
        # No session, or session is on this node — run launch.sh locally.
        ( cd "$REPO_PATH" && ./launch.sh )
        if [ -f "$REPO_PATH/.dashboard_host" ]; then
            ACTUAL_FQDN="$(head -1 "$REPO_PATH/.dashboard_host" | tr -d '[:space:]')"
        fi
        if [ -z "$ACTUAL_FQDN" ]; then
            echo "❌ launch.sh ran but didn't write .dashboard_host." >&2
            exit 1
        fi
    fi

    cat <<EOF

✅ Dashboard running on $ACTUAL_FQDN, port $PORT.

   You're on HPC, so there's no laptop browser to open from here.
   From your laptop, in a new terminal, set up the SSH tunnel:
       ssh -L $PORT:localhost:$PORT $USER_PART@$ACTUAL_FQDN
   Then visit: http://localhost:$PORT

   Watch live remote logs:
       ssh $USER_PART@$ACTUAL_FQDN -t "tmux attach -t balmorel-dash"
       (Ctrl+b then d to detach)

   Stop everything: ./stop_dashboard.sh
EOF
    exit 0
fi

# ── 1. Look for an existing dashboard via the shared state file ────────────
echo "▶ Checking for an existing dashboard via $ENTRY_HOST..."
ACTUAL_FQDN="$(
    ssh -o ConnectTimeout=10 -o BatchMode=no "$ENTRY_HOST" \
        "cat \"$REPO_PATH/.dashboard_host\" 2>/dev/null || true" \
    | head -1 | tr -d '[:space:]'
)"

if [ -n "$ACTUAL_FQDN" ]; then
    ACTUAL_HOST="$USER_PART@$ACTUAL_FQDN"
    echo "  ✓ State file points to $ACTUAL_FQDN"
    echo "▶ Verifying / refreshing dashboard on $ACTUAL_FQDN..."
    ssh "$ACTUAL_HOST" "bash -lc 'cd \"$REPO_PATH\" && ./launch.sh'"
else
    echo "  No existing session — starting a fresh one via $ENTRY_HOST..."
    ssh "$ENTRY_HOST" "bash -lc 'cd \"$REPO_PATH\" && ./launch.sh'"
    # launch.sh just wrote the state file; read it back
    ACTUAL_FQDN="$(
        ssh "$ENTRY_HOST" \
            "cat \"$REPO_PATH/.dashboard_host\" 2>/dev/null || true" \
        | head -1 | tr -d '[:space:]'
    )"
    if [ -z "$ACTUAL_FQDN" ]; then
        echo "❌ launch.sh ran but didn't write .dashboard_host. Can't determine the actual node." >&2
        exit 1
    fi
    ACTUAL_HOST="$USER_PART@$ACTUAL_FQDN"
    echo "  ✓ Dashboard started on $ACTUAL_FQDN"
fi

# ── 2. Tunnel to the specific node ─────────────────────────────────────────
TUNNEL_PATTERN="ssh -f -N -L $PORT:localhost:$PORT $ACTUAL_HOST"
if pgrep -f "$TUNNEL_PATTERN" >/dev/null 2>&1; then
    echo "▶ SSH tunnel localhost:$PORT → $ACTUAL_FQDN already up."
else
    echo "▶ Opening SSH tunnel localhost:$PORT → $ACTUAL_FQDN..."
    if ssh -f -N -L "$PORT:localhost:$PORT" "$ACTUAL_HOST"; then
        echo "  ✓ Tunnel up."
    else
        echo "⚠ Couldn't open tunnel — port $PORT may be in use locally." >&2
        echo "  Check: lsof -iTCP:$PORT" >&2
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
   Running on: $ACTUAL_FQDN

   Stop everything (remote streamlit + local tunnel):
       ./stop_dashboard.sh

   Watch remote streamlit logs:
       ssh $ACTUAL_HOST -t "tmux attach -t balmorel-dash"
EOF
