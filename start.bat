@echo off
REM ============================================================================
REM   BIS Compass - boot the demo (backend + frontend) on Windows
REM   Delegates to start.py. Run setup.bat first if you haven't already.
REM ============================================================================
where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: 'python' not found on PATH. Install Python 3.10-3.12 from python.org.
    exit /b 1
)
python start.py
exit /b %errorlevel%
