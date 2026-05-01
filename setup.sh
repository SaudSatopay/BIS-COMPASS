#!/usr/bin/env bash
# ============================================================================
#   BIS Compass - one-command setup (Linux / macOS)
#   Delegates to setup.py so logic is shared with Windows (setup.bat).
# ============================================================================
set -e

# Prefer python3, fall back to python
if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "ERROR: python3 not found. Install Python 3.10-3.12."
    exit 1
fi

cd "$(dirname "$0")"
exec "$PY" setup.py
