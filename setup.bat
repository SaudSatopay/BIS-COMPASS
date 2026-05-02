@echo off
REM ============================================================================
REM   BIS Compass - one-command setup + demo boot (Windows)
REM
REM   Calls setup.py (env setup + indices + eval), then start.py (boots
REM   the FastAPI backend and Next.js frontend, opens browser).
REM
REM   First run on a fresh machine:  ~5-7 min
REM   Subsequent runs:               ~10 s + frontend boot (~5 s)
REM
REM   To run ONLY setup (no demo boot):
REM     python setup.py
REM
REM   To run ONLY the demo (assumes setup is done):
REM     python start.py
REM ============================================================================

where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: 'python' not found on PATH. Install Python 3.10-3.12 from python.org.
    exit /b 1
)

python setup.py
if errorlevel 1 (
    echo.
    echo Setup failed. See output above. Demo boot skipped.
    exit /b %errorlevel%
)

echo.
echo Setup complete. Booting demo...
echo.
python start.py
exit /b %errorlevel%
