"""Single-source-of-truth offline-mode enforcer.

Both inference.py and the analysis scripts import this so the same logic runs
everywhere. If the BAAI bge-m3 + bge-reranker-v2-m3 model directories are
present in the local HuggingFace cache, we set HF_HUB_OFFLINE / TRANSFORMERS_
OFFLINE so subsequent model loads NEVER touch the network.

Override with HF_FORCE_NETWORK=1 if you really want to re-pull from the Hub.
"""
from __future__ import annotations

import os
import sys


def enforce_offline_if_cached(verbose: bool = True) -> bool:
    """Return True iff we just enforced offline mode (or it was already on)."""
    if os.environ.get("HF_FORCE_NETWORK") == "1":
        return False
    if os.environ.get("HF_HUB_OFFLINE") == "1" and os.environ.get("TRANSFORMERS_OFFLINE") == "1":
        return True

    hf_home = os.environ.get("HF_HOME") or os.path.join(
        os.path.expanduser("~"), ".cache", "huggingface"
    )
    hub_dir = os.path.join(hf_home, "hub")
    if not os.path.isdir(hub_dir):
        return False

    needed = {"models--BAAI--bge-m3", "models--BAAI--bge-reranker-v2-m3"}
    have = set(os.listdir(hub_dir))
    if needed.issubset(have):
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        if verbose:
            print(
                "[offline-guard] HF cache complete — enforcing offline mode "
                "(HF_HUB_OFFLINE=1, TRANSFORMERS_OFFLINE=1)",
                file=sys.stderr,
            )
        return True
    return False
