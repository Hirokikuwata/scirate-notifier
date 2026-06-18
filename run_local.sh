#!/usr/bin/env bash
# Wrapper for local / cron execution.
# - Creates .venv on first run and keeps dependencies up to date.
# - Loads environment variables from .env if present.
# - Forwards all arguments to `python -m scirate_notifier`.
#
# Crontab examples (runs at 08:00 local time — assumes Mac timezone = JST):
#
#   # SciRate top papers (scite-sorted)
#   0 8 * * * /Users/kuwatahiroki/Projects/scirate-notifier/run_local.sh --source scirate >> /tmp/scirate-notifier.log 2>&1
#
#   # arXiv latest submissions
#   0 8 * * * /Users/kuwatahiroki/Projects/scirate-notifier/run_local.sh --source arxiv   >> /tmp/scirate-notifier.log 2>&1

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$REPO_DIR/.venv"
LOG_PREFIX="[$(date '+%Y-%m-%d %H:%M:%S')]"

# Load .env if present (NTFY_TOPIC etc.)
if [[ -f "$REPO_DIR/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "$REPO_DIR/.env"
    set +a
fi

# Create venv if missing
if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    echo "$LOG_PREFIX Creating virtual environment at $VENV_DIR"
    python3 -m venv "$VENV_DIR"
fi

# Install / upgrade dependencies quietly
"$VENV_DIR/bin/pip" install \
    --quiet \
    --upgrade \
    -r "$REPO_DIR/requirements.txt"

echo "$LOG_PREFIX Running: python -m scirate_notifier $*"
exec "$VENV_DIR/bin/python" -m scirate_notifier "$@"
