#!/usr/bin/env python
"""
BIS Compass — boot the demo (backend + frontend)
==================================================

Run this AFTER `setup.py` has populated the indices and downloaded the
HuggingFace model weights at least once.

What this does
--------------
1. Verify that `setup.py` has run (indices exist)
2. Install frontend npm deps if missing
3. Build the frontend (production build) if missing
4. Spawn FastAPI backend on :8000
5. Spawn Next.js production frontend on :3000
6. Wait for both to be reachable
7. Open `http://localhost:3000` in the default browser
8. Wait until Ctrl+C, then cleanly stop both servers

Usage
-----
    python start.py

Or via the OS shortcut:
    start.bat       (Windows)
    bash start.sh   (Linux / macOS)
"""

from __future__ import annotations

import atexit
import os
import platform
import shutil
import signal
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
IS_WINDOWS = platform.system() == "Windows"

# Force UTF-8 stdout/stderr (Git Bash on Windows defaults to cp1252,
# which can't encode the ✓ / ▶ glyphs we print).
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        pass

# Re-use the color helpers from setup.py
if IS_WINDOWS:
    os.system("")  # noqa: S605

C = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "red": "\033[91m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "cyan": "\033[96m",
}


def color(name: str, text: str) -> str:
    if os.environ.get("NO_COLOR") or not (sys.stdout.isatty() or IS_WINDOWS):
        return text
    return f"{C[name]}{text}{C['reset']}"


# ----------------------------------------------------------------------
# Pre-flight
# ----------------------------------------------------------------------
def preflight() -> None:
    required = [
        "data/parsed_standards.json",
        "data/index/bge_m3_dense.faiss",
        "data/index/bm25.pkl",
    ]
    missing = [p for p in required if not Path(p).exists()]
    if missing:
        print(color("red", "ERROR: setup hasn't completed."))
        print(color("yellow", "       Missing: " + ", ".join(missing)))
        print()
        print(color("yellow", "       Run setup first:"))
        print(color("dim",    "         python setup.py"))
        sys.exit(1)

    if shutil.which("npm") is None:
        print(color("red", "ERROR: 'npm' not found on PATH."))
        print(color("yellow", "       Install Node.js (LTS, 18+) from https://nodejs.org/"))
        sys.exit(1)


# ----------------------------------------------------------------------
# Frontend prep (npm install + build if missing)
# ----------------------------------------------------------------------
def prepare_frontend() -> None:
    fe = ROOT / "frontend"
    if not (fe / "node_modules").exists():
        print(color("cyan", "▶ Installing frontend dependencies (one-time, ~2 min)..."))
        run_blocking(["npm", "install"], cwd=fe, label="npm install")
    if not (fe / ".next").exists():
        print(color("cyan", "▶ Building frontend production bundle (one-time)..."))
        run_blocking(["npm", "run", "build"], cwd=fe, label="npm run build")


def run_blocking(cmd: list[str], cwd: Path | None = None, label: str = "") -> None:
    try:
        subprocess.check_call(cmd, cwd=cwd, shell=IS_WINDOWS)
    except subprocess.CalledProcessError as e:
        print(color("red", f"✗ {label or cmd[0]} failed (exit {e.returncode})"))
        sys.exit(e.returncode)


# ----------------------------------------------------------------------
# Spawn + wait helpers
# ----------------------------------------------------------------------
processes: list[subprocess.Popen] = []


def cleanup() -> None:
    for p in processes:
        if p.poll() is None:
            try:
                if IS_WINDOWS:
                    p.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
                else:
                    p.terminate()
                p.wait(timeout=5)
            except Exception:  # noqa: BLE001
                try:
                    p.kill()
                except Exception:  # noqa: BLE001
                    pass


atexit.register(cleanup)


def spawn(cmd: list[str], cwd: Path | None = None) -> subprocess.Popen:
    """Spawn a long-running child. On Windows, use a new process group so
    Ctrl+C in the parent doesn't get rebroadcast incorrectly."""
    kw: dict = {"cwd": cwd}
    if IS_WINDOWS:
        kw["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        kw["shell"] = True  # for npm.cmd resolution
    p = subprocess.Popen(cmd, **kw)
    processes.append(p)
    return p


def wait_url(url: str, timeout: float = 120.0) -> bool:
    import urllib.error
    import urllib.request

    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            pass
        time.sleep(1)
    return False


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main() -> None:
    line = "=" * 60
    print()
    print(color("cyan", line))
    print(color("cyan", "  BIS Compass — booting demo"))
    print(color("cyan", line))

    preflight()
    prepare_frontend()

    print()
    print(color("cyan", "▶ Starting FastAPI backend on :8000..."))
    backend = spawn([sys.executable, "-m", "src.api.main"])

    print(color("cyan", "▶ Starting Next.js frontend on :3000..."))
    spawn(["npm", "start"], cwd=ROOT / "frontend")

    print()
    print(color("dim", "  Waiting for backend (model load: ~30 s on first hot run)..."))
    if not wait_url("http://localhost:8000/health", timeout=180):
        print(color("red", "✗ Backend didn't come up within 3 minutes — check its terminal output."))
        sys.exit(1)
    print(color("green", "  ✓ Backend ready"))

    print(color("dim", "  Waiting for frontend..."))
    if not wait_url("http://localhost:3000", timeout=60):
        print(color("red", "✗ Frontend didn't come up within 1 minute."))
        sys.exit(1)
    print(color("green", "  ✓ Frontend ready"))

    print()
    print(color("cyan", line))
    print(color("green", "  Demo is live."))
    print()
    print(f"    Demo UI:    {color('cyan', 'http://localhost:3000')}")
    print(f"    API:        {color('cyan', 'http://localhost:8000')}")
    print(f"    API docs:   {color('cyan', 'http://localhost:8000/docs')}")
    print(color("cyan", line))
    print()
    print(color("dim", "  Press Ctrl+C in this window to stop both servers."))
    print()

    # Open the browser to the UI
    try:
        webbrowser.open("http://localhost:3000")
    except Exception:  # noqa: BLE001
        pass

    # Idle loop — exit when either child dies or user hits Ctrl+C
    try:
        while True:
            time.sleep(1)
            if backend.poll() is not None:
                print(color("yellow", "\n[backend exited unexpectedly]"))
                break
            if processes[1].poll() is not None:
                print(color("yellow", "\n[frontend exited unexpectedly]"))
                break
    except KeyboardInterrupt:
        print()
        print(color("yellow", "Stopping servers..."))


if __name__ == "__main__":
    main()
