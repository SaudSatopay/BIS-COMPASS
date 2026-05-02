#!/usr/bin/env bash
# ============================================================================
#   BIS Compass - one-command setup + demo boot (Linux / macOS)
#
#   Calls setup.py (env setup + indices + eval), then start.py (boots
#   the FastAPI backend and Next.js frontend, opens browser).
#
#   First run on a fresh machine:  ~5-7 min
#   Subsequent runs:               ~10 s + frontend boot (~5 s)
#
#   To run ONLY setup (no demo boot):
#     python3 setup.py
#
#   To run ONLY the demo (assumes setup is done):
#     python3 start.py
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

"$PY" setup.py

echo
echo "Setup complete. Booting demo..."
echo
exec "$PY" start.py
