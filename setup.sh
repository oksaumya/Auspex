#!/usr/bin/env bash
# Auspex — one-command setup.
# Creates a .venv with Python 3.10+, installs dependencies, copies .env,
# and verifies the install by running the test suite.
#
# Usage: ./setup.sh

set -euo pipefail
cd "$(dirname "$0")"

# ----- Pretty printing ----------------------------------------------------
say()  { printf "\n\033[1;36m==> %s\033[0m\n" "$*"; }
ok()   { printf "    \033[1;32mok\033[0m %s\n" "$*"; }
warn() { printf "    \033[1;33m!!\033[0m %s\n" "$*"; }
die()  { printf "\n\033[1;31m!! %s\033[0m\n" "$*" >&2; exit 1; }

# ----- 1. Locate a usable Python -----------------------------------------
say "Locating Python 3.10+"
PY=""
for v in 3.13 3.12 3.11 3.10; do
    if command -v "python$v" >/dev/null 2>&1; then
        PY="python$v"
        break
    fi
done
if [ -z "$PY" ] && command -v python3 >/dev/null 2>&1; then
    if python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
        PY="python3"
    fi
fi
[ -n "$PY" ] || die "Python 3.10+ not found. Install it (e.g. \`brew install python@3.12\`) and retry."
ok "$($PY --version) at $(command -v "$PY")"

# ----- 2. Create / reuse virtual environment -----------------------------
say "Preparing virtual environment (.venv)"
if [ -d .venv ]; then
    ok "reusing existing .venv"
else
    "$PY" -m venv .venv
    ok "created .venv"
fi

# ----- 3. Install dependencies -------------------------------------------
say "Installing dependencies"
.venv/bin/pip install --upgrade pip --quiet
.venv/bin/pip install --quiet -r requirements.txt
ok "$(.venv/bin/pip list --format=freeze 2>/dev/null | wc -l | tr -d ' ') packages installed"

# ----- 4. Configure .env --------------------------------------------------
say "Configuring environment"
if [ -f .env ]; then
    ok ".env already exists — leaving it alone"
else
    cp .env.example .env
    ok ".env created from template — edit it to add GROQ_API_KEY (optional)"
fi

# ----- 5. Run the test suite ---------------------------------------------
say "Running test suite (37 cases)"
if .venv/bin/pytest tests/ -q --no-header; then
    ok "all tests passed"
else
    warn "tests failed — install completed but the project may not be healthy"
    exit 1
fi

# ----- 6. Done ------------------------------------------------------------
say "Setup complete"
cat <<'EOF'

Next step:

    ./run.sh

This will start the FastAPI backend on http://127.0.0.1:8000 and the Streamlit
dashboard on http://127.0.0.1:8501, with logs tailed in the foreground.
Press Ctrl-C to stop both.

EOF
