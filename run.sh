#!/usr/bin/env bash
# Auspex — one-command run.
# Boots the FastAPI backend and the Streamlit dashboard, waits for both to
# become healthy, tails their logs, and cleans up on Ctrl-C.
#
# Usage: ./run.sh
# Override ports with: BACKEND_PORT=9000 DASHBOARD_PORT=9501 ./run.sh

set -euo pipefail
cd "$(dirname "$0")"

BACKEND_PORT="${BACKEND_PORT:-8000}"
DASHBOARD_PORT="${DASHBOARD_PORT:-8501}"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"

# ----- Pretty printing ----------------------------------------------------
say()  { printf "\n\033[1;36m==> %s\033[0m\n" "$*"; }
ok()   { printf "    \033[1;32mok\033[0m %s\n" "$*"; }
die()  { printf "\n\033[1;31m!! %s\033[0m\n" "$*" >&2; exit 1; }

# ----- Pre-flight ---------------------------------------------------------
[ -d .venv ]              || die ".venv not found. Run ./setup.sh first."
[ -x .venv/bin/uvicorn ]  || die ".venv/bin/uvicorn missing. Run ./setup.sh first."
[ -x .venv/bin/streamlit ]|| die ".venv/bin/streamlit missing. Run ./setup.sh first."

mkdir -p logs

# ----- Free the ports if something is already bound them ------------------
release_port() {
    local port=$1
    local pid
    pid="$(lsof -ti tcp:"$port" 2>/dev/null || true)"
    if [ -n "$pid" ]; then
        say "Port $port is in use by PID $pid — terminating"
        kill "$pid" 2>/dev/null || true
        sleep 1
    fi
}
release_port "$BACKEND_PORT"
release_port "$DASHBOARD_PORT"

# ----- Cleanup on exit ----------------------------------------------------
BACKEND_PID=""
DASHBOARD_PID=""
TAIL_PID=""

# Streamlit fork()s grandchildren that survive a parent kill, so we also
# free anything still bound to our ports.
kill_port() {
    local port=$1
    local pids
    pids="$(lsof -ti tcp:"$port" 2>/dev/null || true)"
    [ -n "$pids" ] && kill $pids 2>/dev/null || true
    sleep 0.5
    pids="$(lsof -ti tcp:"$port" 2>/dev/null || true)"
    [ -n "$pids" ] && kill -9 $pids 2>/dev/null || true
}

_CLEANUP_RAN=0
cleanup() {
    [ "$_CLEANUP_RAN" = "1" ] && return 0
    _CLEANUP_RAN=1
    printf "\n\033[1;36m==> Shutting down\033[0m\n"
    [ -n "$TAIL_PID" ]      && kill "$TAIL_PID"      2>/dev/null || true
    [ -n "$DASHBOARD_PID" ] && kill "$DASHBOARD_PID" 2>/dev/null || true
    [ -n "$BACKEND_PID" ]   && kill "$BACKEND_PID"   2>/dev/null || true
    kill_port "$DASHBOARD_PORT"
    kill_port "$BACKEND_PORT"
    wait 2>/dev/null || true
    printf "    \033[1;32mok\033[0m goodbye\n"
}
trap cleanup INT TERM HUP EXIT

# ----- Start backend ------------------------------------------------------
say "Starting FastAPI backend on http://${BACKEND_HOST}:${BACKEND_PORT}"
.venv/bin/uvicorn server:app \
    --host "$BACKEND_HOST" --port "$BACKEND_PORT" --log-level info \
    > logs/backend.log 2>&1 &
BACKEND_PID=$!

# Wait until the health endpoint responds
for _ in $(seq 1 30); do
    if curl -s -f "http://${BACKEND_HOST}:${BACKEND_PORT}/" > /dev/null 2>&1; then
        ok "backend ready (PID $BACKEND_PID)"
        break
    fi
    sleep 1
done
if ! curl -s -f "http://${BACKEND_HOST}:${BACKEND_PORT}/" > /dev/null 2>&1; then
    die "backend failed to start within 30s — check logs/backend.log"
fi

# ----- Start dashboard ----------------------------------------------------
say "Starting Streamlit dashboard on http://${BACKEND_HOST}:${DASHBOARD_PORT}"
REVIEWER_API_URL="http://${BACKEND_HOST}:${BACKEND_PORT}" \
    .venv/bin/streamlit run dashboard/Home.py \
    --server.port "$DASHBOARD_PORT" \
    --server.address "$BACKEND_HOST" \
    --server.headless true \
    --browser.gatherUsageStats false \
    > logs/dashboard.log 2>&1 &
DASHBOARD_PID=$!

for _ in $(seq 1 30); do
    if curl -s -f "http://${BACKEND_HOST}:${DASHBOARD_PORT}/_stcore/health" > /dev/null 2>&1; then
        ok "dashboard ready (PID $DASHBOARD_PID)"
        break
    fi
    sleep 1
done

# ----- Banner -------------------------------------------------------------
cat <<EOF

\033[1;35mAuspex is running\033[0m

    Backend    http://${BACKEND_HOST}:${BACKEND_PORT}
    API docs   http://${BACKEND_HOST}:${BACKEND_PORT}/docs
    Dashboard  http://${BACKEND_HOST}:${DASHBOARD_PORT}

Logs are streaming below. Press Ctrl-C to stop both services.

EOF

# ----- Tail both logs and wait via a poll loop ---------------------------
# A bare `wait` defers signal delivery, which prevents Ctrl-C from firing
# the cleanup trap when run.sh itself is backgrounded. A sleep loop is
# interruptible so the trap fires immediately on INT/TERM.
tail -f logs/backend.log logs/dashboard.log &
TAIL_PID=$!

while kill -0 "$BACKEND_PID" 2>/dev/null && kill -0 "$DASHBOARD_PID" 2>/dev/null; do
    sleep 1
done
