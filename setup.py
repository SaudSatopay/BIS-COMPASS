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
# Force UTF-8 stdout/stderr so the ✓ / ✗ / ▶ glyphs we print don't crash
# on terminals whose default encoding can't represent them (Git Bash on
# Windows defaults to cp1252; PowerShell sometimes too). We use
# errors="replace" so a truly hostile encoding falls back to '?' instead
# of raising UnicodeEncodeError.
# ----------------------------------------------------------------------
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        pass

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
def _persist_env_var(key: str, value: str) -> None:
    """Save KEY=value to .env so subsequent processes (FastAPI backend,
    inference.py, etc.) inherit it via python-dotenv. Idempotent —
    replaces any existing line for the same key."""
    env_file = ROOT / ".env"
    lines: list[str] = []
    if env_file.exists():
        try:
            lines = env_file.read_text(encoding="utf-8").splitlines()
        except Exception:  # noqa: BLE001
            lines = []
    prefix = f"{key}="
    lines = [ln for ln in lines if not ln.strip().startswith(prefix)]
    lines.append(f"{key}={value}")
    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _persist_hf_token(token: str) -> None:
    """Backward-compat shim — now just delegates to _persist_env_var."""
    _persist_env_var("HF_TOKEN", token)


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
def _can_create_symlinks() -> bool:
    """Test whether the current process can create symlinks.

    On Windows this requires Developer Mode or admin privileges. On
    Unix it's effectively always true. We test by actually creating
    one in a temp directory rather than reading the registry — that
    catches every edge case (Dev Mode, group policy overrides, FAT32
    filesystems, container restrictions, etc.) at the cost of a few
    millis of file I/O. The TemporaryDirectory auto-cleans, so we
    don't need to manually unlink (which would itself raise if the
    symlink_to call had failed).
    """
    if platform.system() != "Windows":
        return True
    import tempfile  # noqa: PLC0415
    try:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "_t"
            target.write_text("ok", encoding="utf-8")
            link = Path(tmp) / "_l"
            link.symlink_to(target)
            return True
    except (OSError, NotImplementedError, PermissionError):
        return False


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

    # Adaptive HF downloader selection: HuggingFace's xet downloader uses
    # symlinks for cross-revision deduplication. Stock Windows (no
    # Developer Mode, no admin) can't create symlinks → xet sometimes
    # crashes mid-download with WinError 1314. If we can't create
    # symlinks, force the legacy downloader AND persist that decision
    # to .env so the backend / inference.py (separate processes) inherit
    # it via python-dotenv. Otherwise setup.py works but the demo backend
    # later hits the same crash on a model refresh.
    if not _can_create_symlinks():
        os.environ["HF_HUB_DISABLE_XET"] = "1"
        try:
            _persist_env_var("HF_HUB_DISABLE_XET", "1")
        except Exception:  # noqa: BLE001
            pass
        print(color("dim", "  symlinks unavailable → disabling xet (legacy HF downloader, persisted to .env)"))
    else:
        print(color("dim", "  symlinks supported ✓"))

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


def _ignore_patterns_for(model_id: str) -> list[str]:
    """Per-model ignore list. CRITICAL: bge-m3 ships its weights ONLY in
    `pytorch_model.bin` (no `model.safetensors`), so we must NOT filter
    that file out for that repo. bge-reranker-v2-m3 has both formats so
    we drop the .bin to avoid a redundant 2.3 GB download.

    The earlier blanket ignore of pytorch_model.bin caused the prefetch
    to silently complete with bge-m3 missing all weights, then crash at
    warm-up with `OSError: no file named model.safetensors, or
    pytorch_model.bin`. Caught only on cold-cache anonymous runs.
    """
    base = [
        "*.onnx",
        "onnx/*",
        "onnx_*/*",
        "openvino/*",
        "openvino_*/*",
        "*.msgpack",
        "*.h5",
        "*.gguf",
        "model.bin",  # rare alternate name; never the canonical weight file we use
    ]
    # bge-m3 ships pytorch_model.bin ONLY — keep it.
    # bge-reranker-v2-m3 ships both .bin and .safetensors — drop .bin.
    if model_id == "BAAI/bge-m3":
        return base
    return base + ["pytorch_model.bin", "pytorch_model-*"]


def _has_weights_in_cache(model_id: str) -> bool:
    """Verify a usable weights file landed in the local cache after a
    snapshot_download. Returns False if neither `model.safetensors` nor
    `pytorch_model.bin` is present in any snapshot."""
    try:
        from huggingface_hub import scan_cache_dir  # noqa: PLC0415
    except ImportError:
        return True  # Optimistic — can't verify, assume ok
    try:
        info = scan_cache_dir()
    except Exception:  # noqa: BLE001
        return True
    for repo in info.repos:
        if repo.repo_id != model_id:
            continue
        for rev in repo.revisions:
            names = {f.file_name for f in rev.files}
            if "model.safetensors" in names or "pytorch_model.bin" in names:
                return True
    return False


def step_prefetch_models(n: int):
    """Pre-fetch only the model files we actually need from HuggingFace,
    in parallel, with high per-file concurrency.

    Three optimisations stacked:
      • ignore_patterns filter (per-model — see _ignore_patterns_for) —
        drops ONNX, OpenVINO, redundant weight formats. Cuts wire size
        from ~12 GB to ~5 GB without dropping any file we need.
      • max_workers=16 — more concurrent file fetches per model.
      • ThreadPoolExecutor over both models — parallel download.

    All three are pure delivery optimisations — same model bytes in the
    cache, model behaviour unchanged.

    POST-DOWNLOAD VERIFY: after each fetch we confirm a usable weight
    file (.safetensors OR pytorch_model.bin) is in the cache. If not,
    we fail loud here rather than crashing in step 6 with an opaque
    transformers stack trace.
    """
    t = step(
        n, TOTAL,
        "Pre-fetching HF models in parallel (filtered, ~5 GB)",
    )
    try:
        from huggingface_hub import snapshot_download  # noqa: PLC0415
        from concurrent.futures import ThreadPoolExecutor, as_completed  # noqa: PLC0415
    except ImportError:
        print(color("yellow", "      huggingface_hub not yet installed — skipping pre-fetch."))
        print(color("yellow", "      (Models will still download, just unfiltered.)"))
        return

    token = os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")
    models = ("BAAI/bge-m3", "BAAI/bge-reranker-v2-m3")

    def _fetch(model_id: str) -> tuple[str, bool, str]:
        try:
            snapshot_download(
                repo_id=model_id,
                ignore_patterns=_ignore_patterns_for(model_id),
                token=token,
                max_workers=16,
                tqdm_class=None,
            )
            # Verify that a usable weights file actually landed
            if not _has_weights_in_cache(model_id):
                return (
                    model_id,
                    False,
                    "download succeeded but no model.safetensors / pytorch_model.bin "
                    "found in cache (filter or revision issue)",
                )
            return (model_id, True, "")
        except Exception as e:  # noqa: BLE001
            return (model_id, False, str(e))

    print(color("dim", "      starting both downloads in parallel..."))
    failures: list[tuple[str, str]] = []
    with ThreadPoolExecutor(max_workers=len(models)) as ex:
        futures = {ex.submit(_fetch, m): m for m in models}
        for fut in as_completed(futures):
            model_id, ok, err = fut.result()
            if ok:
                print(color("green", f"      OK  {model_id}"))
            else:
                print(color("red", f"      FAIL {model_id}: {err}"))
                failures.append((model_id, err))

    if failures:
        print()
        print(color("red", "  Pre-fetch did not produce usable weights for:"))
        for mid, err in failures:
            print(color("red", f"    - {mid}: {err}"))
        print(color("yellow", "  Setup will fail at the warm-up step. Aborting now so the"))
        print(color("yellow", "  error surfaces here instead of inside transformers later."))
        sys.exit(2)

    done(t)


def _has_nvidia_gpu() -> bool:
    """Detect an NVIDIA GPU by looking for `nvidia-smi`. Conservative —
    if nvidia-smi isn't reachable we assume no GPU (false negative is fine,
    just means we skip the CUDA torch wheel)."""
    try:
        r = subprocess.run(
            ["nvidia-smi"],
            capture_output=True,
            timeout=5,
            text=True,
        )
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.SubprocessError):
        return False


def _torch_status() -> tuple[bool, bool]:
    """Return (installed, has_cuda). Subprocess so torch import doesn't
    pollute setup.py's process — torch is heavy and we only need the
    boolean. Times out at 30 s in case torch hangs on first import."""
    try:
        result = subprocess.run(
            [
                sys.executable, "-c",
                "import sys; "
                "import torch; "
                "sys.stdout.write('YES|' + str(torch.cuda.is_available()))",
            ],
            capture_output=True,
            timeout=30,
            text=True,
        )
        if result.returncode == 0:
            line = (result.stdout or "").strip()
            if line.startswith("YES|"):
                return (True, line == "YES|True")
    except Exception:  # noqa: BLE001
        pass
    return (False, False)


def _torch_pin_from_requirements() -> str:
    """Read the torch line from requirements.txt verbatim so we install the
    same version pin that the rest of the resolver expects."""
    try:
        for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and line.lower().startswith("torch"):
                # Strip trailing comments
                return line.split("#", 1)[0].strip()
    except Exception:  # noqa: BLE001
        pass
    return "torch"


def step_install_deps(n: int):
    t = step(n, TOTAL, "Installing dependencies (requirements.txt)")
    print(color("dim", "      pip install --upgrade pip ..."))
    run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "pip", "--quiet"],
        "pip self-upgrade",
    )

    # Pre-install torch with the right wheel for this hardware so that
    # `pip install -r requirements.txt` (next step) sees torch already
    # satisfied and doesn't download a wrong-architecture wheel.
    #
    # Three branches:
    #   1. Already-installed CUDA torch  -> nothing to do
    #   2. NVIDIA GPU available + need install -> CUDA 11.8 wheel (judge case)
    #   3. No GPU, no torch yet                -> explicit CPU wheel
    #
    # cu128 (CUDA 12.8) is the right wheel for torch 2.11.0 — older indexes
    # like cu118 / cu121 don't ship 2.11.0. cu128 covers Turing / Ampere /
    # Ada / Hopper / Blackwell (RTX 20xx through RTX 50xx, A-series, H-series)
    # via NVIDIA's forward-compat. Requires NVIDIA driver >= 555 (2024+).
    # Older drivers should set TORCH_NO_CUDA=1 to fall back to CPU torch.
    has_gpu = _has_nvidia_gpu()
    torch_installed, torch_has_cuda = _torch_status()
    skip_cuda = bool(os.getenv("TORCH_NO_CUDA"))
    torch_pin = _torch_pin_from_requirements()

    if has_gpu and torch_has_cuda:
        print(color("dim", "      torch with CUDA already installed → skipping wheel pre-install"))
    elif has_gpu and not skip_cuda:
        print(
            color(
                "cyan",
                f"      NVIDIA GPU detected → installing {torch_pin} with CUDA 12.8 (~3 GB)",
            )
        )
        print(color("dim", "      cu128 covers Turing / Ampere / Ada / Hopper / Blackwell (RTX 20-50xx)."))
        print(color("dim", "      Override: TORCH_NO_CUDA=1 to use CPU torch instead."))
        run(
            [
                sys.executable, "-m", "pip", "install",
                torch_pin,
                "--index-url", "https://download.pytorch.org/whl/cu128",
                "--quiet",
            ],
            "pip install torch (CUDA 12.8)",
        )
    elif not has_gpu and not torch_installed:
        print(
            color(
                "dim",
                f"      no NVIDIA GPU detected → installing {torch_pin} from CPU wheel index"
                f" (saves ~2 GB on Linux/macOS) ...",
            )
        )
        run(
            [
                sys.executable, "-m", "pip", "install",
                torch_pin,
                "--index-url", "https://download.pytorch.org/whl/cpu",
                "--quiet",
            ],
            "pip install torch (CPU)",
        )
    elif not has_gpu and torch_installed:
        # CPU machine + torch already installed (presumably from prior run).
        # Leave it alone; requirements.txt will reconcile if needed.
        print(color("dim", "      no GPU, torch already installed → leaving as-is"))

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
        "Warm-up run on public test set (loads cached models, runs 10 eval queries)",
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
