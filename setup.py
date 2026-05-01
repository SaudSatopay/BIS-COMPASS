#!/usr/bin/env python
"""
BIS Compass — one-command environment setup
============================================

Cross-platform (Windows / Linux / macOS). Idempotent: skips steps that
already finished. Pre-flight checks Python version. Gives colored,
timed progress so a judge can tell at a glance what's happening.

Usage
-----
    python setup.py

Or via the platform-native shortcut:
    setup.bat       (Windows)
    bash setup.sh   (Linux / macOS)

What this does
--------------
1. Verify Python version (3.10–3.13 supported; warns on 3.14+)
2. Install dependencies from requirements.txt
3. Parse SP 21 PDF -> 559 standards + IS-code whitelist  (skipped if cached)
4. Build FAISS dense index (downloads bge-m3 ~2.3 GB)     (skipped if cached)
5. Build BM25 sparse index                                (skipped if cached)
6. Warm-up inference.py on the public test set
   (downloads bge-reranker-v2-m3 ~2.3 GB on first run)
7. Score the warm-up with eval_script.py

First run:        3-7 minutes (most of it is HF model download)
Subsequent runs:  ~10 seconds (everything is cached, fully offline)
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)

# ----------------------------------------------------------------------
# ANSI colors — enable on Windows 10+ via os.system("")
# ----------------------------------------------------------------------
if platform.system() == "Windows":
    os.system("")  # noqa: S605 — turns on ANSI parsing in cmd

C = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "red": "\033[91m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "cyan": "\033[96m",
    "magenta": "\033[95m",
}


def supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty() or platform.system() == "Windows"


def color(name: str, text: str) -> str:
    if not supports_color():
        return text
    return f"{C[name]}{text}{C['reset']}"


# ----------------------------------------------------------------------
# Step helpers
# ----------------------------------------------------------------------
def banner(text: str):
    line = "=" * 60
    print()
    print(color("cyan", line))
    print(color("cyan", f"  {text}"))
    print(color("cyan", line))


def step(num: int, total: int, label: str) -> float:
    print()
    print(color("cyan", f"[{num}/{total}] {label}"))
    return time.time()


def skip(num: int, total: int, label: str):
    print()
    print(color("dim", f"[{num}/{total}] {label}  (cached, skipping)"))


def done(start: float):
    elapsed = time.time() - start
    print(color("green", f"      ✓ done in {elapsed:.1f}s"))


def fail(msg: str, code: int = 1):
    print()
    print(color("red", f"  ✗ {msg}"))
    sys.exit(code)


def run(cmd: list[str], description: str = "") -> bool:
    try:
        subprocess.check_call(cmd)
        return True
    except subprocess.CalledProcessError as e:
        fail(f"{description or cmd[0]} failed (exit {e.returncode}). See output above.")
        return False
    except FileNotFoundError:
        fail(f"{cmd[0]} not found on PATH.")
        return False


def all_exist(*paths: str) -> bool:
    return all(Path(p).exists() for p in paths)


# ----------------------------------------------------------------------
# HuggingFace token prompt (optional, but big speedup)
# ----------------------------------------------------------------------
def _persist_hf_token(token: str) -> None:
    """Save HF_TOKEN to .env so subsequent runs (and the FastAPI backend)
    pick it up automatically. Idempotent — replaces any existing line."""
    env_file = ROOT / ".env"
    lines: list[str] = []
    if env_file.exists():
        try:
            lines = env_file.read_text(encoding="utf-8").splitlines()
        except Exception:  # noqa: BLE001
            lines = []
    lines = [ln for ln in lines if not ln.strip().startswith("HF_TOKEN=")]
    lines.append(f"HF_TOKEN={token}")
    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def maybe_prompt_hf_token() -> None:
    """If we don't already have an HF token, offer the user a one-time prompt.
    Authenticated HF downloads are ~10-50× faster than anonymous (which is
    rate-limited to ~1 MB/s). Skipping is fine — falls back to anonymous."""

    # Already in env?
    if os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN"):
        print(color("dim", "  HF_TOKEN ✓ (already set in environment)"))
        return

    # Already saved by `huggingface-cli login`?
    hf_dir = Path.home() / ".cache" / "huggingface"
    for candidate in (hf_dir / "token", hf_dir / "stored_tokens"):
        if candidate.exists():
            try:
                content = candidate.read_text(encoding="utf-8").strip()
                if content and not content.startswith("{"):  # plain token, not json
                    os.environ["HF_TOKEN"] = content.split()[0]
                    print(color("dim", f"  HF_TOKEN ✓ (loaded from {candidate})"))
                    return
            except Exception:  # noqa: BLE001
                pass

    # Already in .env?
    env_file = ROOT / ".env"
    if env_file.exists():
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("HF_TOKEN=") and "=" in line:
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if val:
                        os.environ["HF_TOKEN"] = val
                        print(color("dim", "  HF_TOKEN ✓ (loaded from .env)"))
                        return
        except Exception:  # noqa: BLE001
            pass

    # Ask. Skip the prompt if stdin isn't a TTY (CI, piped input).
    if not sys.stdin.isatty():
        print(color("dim", "  HF_TOKEN not set (non-interactive shell — skipping prompt)"))
        return

    print()
    print(color("yellow", "  ┌────────────────────────────────────────────────────────┐"))
    print(color("yellow", "  │  HuggingFace token — STRONGLY recommended              │"))
    print(color("yellow", "  └────────────────────────────────────────────────────────┘"))
    print()
    print(color("bold", "    Without a token:  ~3 GB download takes 15–25 minutes"))
    print(color("green", "    With a free token: same download in 3–5 minutes"))
    print()
    print(color("dim", "    Get one in 30 seconds:"))
    print(color("cyan", "      https://huggingface.co/settings/tokens"))
    print(color("dim", "      (sign in with Google → 'Create new token' → 'Read')"))
    print()
    print(color("dim", "    Paste it below, or press Enter to skip (slower)."))
    print()

    try:
        token = input("  Paste HF token (or press Enter to skip): ").strip()
    except (KeyboardInterrupt, EOFError):
        print()
        return

    if not token:
        print(color("yellow", "  Skipping — proceeding with anonymous downloads (slower)."))
        return

    if not token.startswith("hf_"):
        print(color("yellow", "  WARNING: token doesn't start with 'hf_' — using it anyway."))

    try:
        _persist_hf_token(token)
        os.environ["HF_TOKEN"] = token
        print(color("green", "  ✓ Token saved to .env. HuggingFace downloads will be much faster."))
    except Exception as e:  # noqa: BLE001
        print(color("yellow", f"  Couldn't write .env ({e}) — using token for this run only."))
        os.environ["HF_TOKEN"] = token


# ----------------------------------------------------------------------
# Pre-flight
# ----------------------------------------------------------------------
def preflight() -> None:
    py = sys.version_info
    py_str = f"{py.major}.{py.minor}.{py.micro}"

    if py < (3, 10):
        print(color("red", f"  Python 3.10+ required, found {py_str}"))
        sys.exit(1)

    if py >= (3, 14):
        print(color("yellow", f"  WARNING: Python {py_str} detected."))
        print(color("yellow", "           ML wheels (numpy / torch / faiss) often lag 6-12 months"))
        print(color("yellow", "           behind Python releases. If installation fails, fall back to"))
        print(color("yellow", "           Python 3.10-3.12 — that range is fully validated."))
        print()
    else:
        print(color("dim", f"  Python {py_str} ✓"))

    # Tiny disk-space check (not exhaustive — just a hint)
    try:
        free_gb = shutil.disk_usage(ROOT).free / (1024 ** 3)
        if free_gb < 8:
            print(
                color(
                    "yellow",
                    f"  WARNING: only {free_gb:.1f} GB free in {ROOT.drive or '/'}. "
                    f"First run downloads ~5 GB of model weights.",
                )
            )
    except Exception:  # noqa: BLE001
        pass


# ----------------------------------------------------------------------
# Steps
# ----------------------------------------------------------------------
TOTAL = 7


def step_prefetch_models(n: int):
    """Pre-fetch only the model files we actually need from HuggingFace.

    The default `snapshot_download` triggered by sentence-transformers /
    FlagEmbedding pulls the WHOLE repo for each model — which for bge-m3
    means ~7 GB (PyTorch bin + ONNX + SafeTensors + LoRA adapters in
    parallel). We only need SafeTensors + tokenizer + configs (~2.3 GB).
    Same story for bge-reranker-v2-m3.

    Filtering with `ignore_patterns` cuts the total HF download from
    ~12 GB to ~5 GB without changing model behaviour.
    """
    t = step(
        n, TOTAL,
        "Pre-fetching HF models (filtered to SafeTensors only, ~5 GB instead of ~12 GB)",
    )
    try:
        from huggingface_hub import snapshot_download  # noqa: PLC0415
    except ImportError:
        print(color("yellow", "      huggingface_hub not yet installed — skipping pre-fetch."))
        print(color("yellow", "      (Models will still download, just unfiltered.)"))
        return

    ignore_patterns = [
        # Alternate weight formats we don't use (we read SafeTensors)
        "*.onnx",
        "onnx/*",
        "onnx_*/*",
        "openvino/*",
        "openvino_*/*",
        "pytorch_model.bin",
        "pytorch_model-*",
        "model.bin",
        "*.msgpack",
        "*.h5",
        # Image / multimodal extras (bge-m3 ships none, but defensive)
        "*.gguf",
    ]
    token = os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")

    for model_id in ("BAAI/bge-m3", "BAAI/bge-reranker-v2-m3"):
        print(color("dim", f"      → {model_id}"))
        try:
            snapshot_download(
                repo_id=model_id,
                ignore_patterns=ignore_patterns,
                token=token,
                # Print download progress to the same stream so the user
                # sees what's happening
                tqdm_class=None,
            )
        except Exception as e:  # noqa: BLE001
            print(color("yellow", f"      WARNING: pre-fetch of {model_id} failed: {e}"))
            print(color("yellow", "      Falling back to library-default download."))
    done(t)


def step_install_deps(n: int):
    t = step(n, TOTAL, "Installing dependencies (requirements.txt)")
    print(color("dim", "      pip install --upgrade pip ..."))
    run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "pip", "--quiet"],
        "pip self-upgrade",
    )
    print(color("dim", "      pip install -r requirements.txt ..."))
    run(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
        "pip install -r requirements.txt",
    )
    done(t)


def step_parse_pdf(n: int):
    if all_exist("data/parsed_standards.json", "data/is_code_whitelist.json"):
        skip(n, TOTAL, "Parse SP 21 PDF -> 559 standards + IS-code whitelist")
        return
    t = step(n, TOTAL, "Parsing SP 21 PDF (929 pages -> 559 standards)")
    run([sys.executable, "-m", "src.ingestion.pdf_parser"], "PDF parser")
    done(t)


def step_build_dense(n: int):
    if all_exist(
        "data/index/bge_m3_dense.faiss",
        "data/index/standards_meta.json",
    ):
        skip(n, TOTAL, "Build FAISS dense index")
        return
    t = step(
        n, TOTAL,
        "Building FAISS dense index "
        "(first run downloads bge-m3 from HuggingFace ~2.3 GB)",
    )
    run([sys.executable, "-m", "src.retrieval.index"], "Dense index build")
    done(t)


def step_build_bm25(n: int):
    if all_exist("data/index/bm25.pkl"):
        skip(n, TOTAL, "Build BM25 sparse index")
        return
    t = step(n, TOTAL, "Building BM25 sparse index")
    run([sys.executable, "-m", "src.retrieval.bm25_index"], "BM25 index build")
    done(t)


def step_warmup(n: int):
    t = step(
        n, TOTAL,
        "Warm-up run on public test set "
        "(first run downloads bge-reranker-v2-m3 ~2.3 GB)",
    )
    run(
        [
            sys.executable, "inference.py",
            "--input", "datasets/public_test_set.json",
            "--output", "team_results.json",
        ],
        "inference.py",
    )
    done(t)


def step_score(n: int):
    t = step(n, TOTAL, "Scoring the warm-up with eval_script.py")
    print()
    # Don't capture eval output — it's the headline result the judge wants to see.
    try:
        subprocess.check_call(
            [sys.executable, "eval_script.py", "--results", "team_results.json"]
        )
    except subprocess.CalledProcessError:
        print(color("yellow", "      eval_script.py reported a failure; check output above."))
    done(t)


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main():
    banner("BIS Compass — environment setup")
    preflight()
    maybe_prompt_hf_token()

    overall = time.time()

    step_install_deps(1)
    step_prefetch_models(2)
    step_parse_pdf(3)
    step_build_dense(4)
    step_build_bm25(5)
    step_warmup(6)
    step_score(7)

    elapsed = time.time() - overall

    print()
    print(color("green", "=" * 60))
    print(color("green", f"  Setup complete in {elapsed:.0f}s. Environment ready."))
    print(color("green", "=" * 60))
    print()
    print("Run inference on a private test set:")
    print(color("dim", "  python inference.py --input <input.json> --output <output.json>"))
    print()
    print("Boot the demo UI:")
    print(color("dim", "  python -m src.api.main         # backend on :8000"))
    print(color("dim", "  cd frontend && npm install && npm run build && npm start"))
    print()


if __name__ == "__main__":
    main()
