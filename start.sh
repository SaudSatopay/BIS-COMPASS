#!/usr/bin/env bash
# ============================================================================
#   BIS Compass - boot the demo (backend + frontend) on Linux / macOS
#   Delegates to start.py. Run setup.sh first if you haven't already.
# ============================================================================
set -e

if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "ERROR: python3 not found. Install Python 3.10-3.12."
    exit 1
fi

cd "$(dirname "$0")"
exec "$PY" start.py
