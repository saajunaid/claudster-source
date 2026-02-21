#!/usr/bin/env bash
# junai.sh — JUNAI unified CLI wrapper
#
# Usage:
#   ./junai.sh pipeline status
#   ./junai.sh pipeline init    --project "My Project" --feature "Feature Name"
#   ./junai.sh pipeline mode    --value supervised|auto
#   ./junai.sh pipeline gate    --name <gate_name>
#   ./junai.sh pipeline next    [--event <event>]
#   ./junai.sh pipeline advance --event <event> [--stage <stage>]
#   ./junai.sh pipeline transitions
#   ./junai.sh pipeline preflight --target-stage <stage>
#
#   ./junai.sh agent make      --name <xyz> [--role executing|advisory]
#   ./junai.sh agent validate  --name <xyz>
#   ./junai.sh agent diff      --name <xyz>
#   ./junai.sh agent onboard   --name <xyz> [--yes]
#   ./junai.sh agent list
#   ./junai.sh agent inspect   --name <xyz>
#   ./junai.sh agent remove    --name <xyz> [--force]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER="$SCRIPT_DIR/tools/pipeline-runner/junai.py"
PYTHON="$SCRIPT_DIR/.venv/bin/python"

if [[ ! -x "$PYTHON" ]]; then
    echo "[junai] ERROR: Python venv not found at $PYTHON"
    echo "        Run: python -m venv .venv && .venv/bin/pip install -r requirements.txt"
    exit 1
fi

if [[ ! -f "$RUNNER" ]]; then
    echo "[junai] ERROR: junai.py not found at $RUNNER"
    exit 1
fi

exec "$PYTHON" "$RUNNER" "$@"
