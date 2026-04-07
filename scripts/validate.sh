#!/usr/bin/env bash
# Thin wrapper — delegates to Python pipeline.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
exec python3 "$PROJECT_ROOT/harness/validate.py" "$PROJECT_ROOT" "$@"
