@echo off
REM ============================================================================
REM   BIS Compass - one-command setup (Windows)
REM   Delegates to setup.py so logic is shared with macOS/Linux (setup.sh).
REM ============================================================================
where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: 'python' not found on PATH. Install Python 3.10-3.12 from python.org.
    exit /b 1
)
python setup.py
exit /b %errorlevel%
