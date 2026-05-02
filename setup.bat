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
setlocal

REM --- Locate a real Python (not the Microsoft Store stub) ---------------
REM  Win 10/11 ships a 0-byte python.exe stub in WindowsApps that opens the
REM  Store page when invoked. `where python` finds it; we have to verify
REM  it's a real interpreter before using it.

set "PY="
for /f "delims=" %%P in ('where python 2^>nul') do (
    if not defined PY (
        echo %%P | findstr /I "WindowsApps" >nul
        if errorlevel 1 (
            "%%P" -c "import sys; sys.exit(0 if sys.version_info>=(3,10) else 2)" >nul 2>&1
            if not errorlevel 1 set "PY=%%P"
        )
    )
)

if not defined PY (
    echo ERROR: a real Python 3.10+ install was not found on PATH.
    echo.
    echo Likely causes:
    echo   * Only the Microsoft Store stub is installed (a 0-byte placeholder).
    echo   * Python is below 3.10.
    echo.
    echo Install Python 3.10-3.12 from https://www.python.org/downloads/
    echo and re-run setup.bat. Make sure to check "Add to PATH" in the installer.
    exit /b 1
)

echo Using Python: %PY%
echo.

"%PY%" setup.py
if errorlevel 1 (
    echo.
    echo Setup failed. See output above. Demo boot skipped.
    exit /b %errorlevel%
)

echo.
echo Setup complete. Booting demo...
echo.
"%PY%" start.py
exit /b %errorlevel%
