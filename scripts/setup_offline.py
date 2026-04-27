"""One-time setup: download all model weights to local cache.

After this script completes, the project can be run with the env var
`HF_HUB_OFFLINE=1` and will not contact Hugging Face Hub at runtime —
critical for judges scoring on machines without internet access.

Usage:
    python scripts/setup_offline.py
    # then optionally:
    export HF_HUB_OFFLINE=1     # Linux / macOS
    setx HF_HUB_OFFLINE 1       # Windows (persistent)
"""
from __future__ import annotations

import os
import sys
import time

import torch
from huggingface_hub import snapshot_download


MODELS = [
    ("BAAI/bge-m3", "embedder"),
    ("BAAI/bge-reranker-v2-m3", "reranker"),
]


def main() -> int:
    cache_dir = os.environ.get("HF_HOME") or os.path.expanduser("~/.cache/huggingface")
    print(f"HF cache directory: {cache_dir}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"  GPU: {torch.cuda.get_device_name(0)}")
    print()

    for repo_id, label in MODELS:
        print(f"-- Downloading {label}: {repo_id}")
        t = time.perf_counter()
        try:
            snapshot_download(
                repo_id=repo_id,
                local_files_only=False,
                resume_download=True,
            )
        except Exception as e:
            print(f"  FAILED: {e}", file=sys.stderr)
            return 1
        print(f"  ok ({time.perf_counter() - t:.1f}s)")

    # Smoke-test offline loads to confirm everything is in place.
    print("\n-- Offline-mode smoke test")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    try:
        from src.retrieval.embedder import get_embedder
        from src.retrieval.reranker import get_reranker
        get_embedder()
        get_reranker()
    except Exception as e:
        print(f"  FAILED: {e}", file=sys.stderr)
        return 1
    print("  ok — both models load offline.")

    print("\nAll set. To enforce offline mode in your shell:")
    print("    export HF_HUB_OFFLINE=1   # Linux / macOS")
    print("    setx HF_HUB_OFFLINE 1     # Windows (persistent)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
