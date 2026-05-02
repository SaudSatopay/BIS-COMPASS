"""Single-source-of-truth offline-mode enforcer.

Both inference.py and the analysis scripts import this so the same logic runs
everywhere. If the BAAI bge-m3 + bge-reranker-v2-m3 model directories are
present in the local HuggingFace cache AND each has a usable weights file,
we set HF_HUB_OFFLINE / TRANSFORMERS_OFFLINE so subsequent model loads
NEVER touch the network.

Override with HF_FORCE_NETWORK=1 if you really want to re-pull from the Hub.
"""
from __future__ import annotations

import os
import sys


def _has_usable_weights(model_dir: str) -> bool:
    """Walk a HF cache model directory and confirm at least one usable
    weight file is present. The directory existing isn't enough — a
    partial download (interrupted by network) leaves directories but no
    weights. If we flip offline mode on a partial cache, the actual
    model load later fails opaquely with `OSError: no file named ...`.
    """
    needles = ("model.safetensors", "pytorch_model.bin")
    snapshots_dir = os.path.join(model_dir, "snapshots")
    if not os.path.isdir(snapshots_dir):
        return False
    try:
        for entry in os.listdir(snapshots_dir):
            snap = os.path.join(snapshots_dir, entry)
            if not os.path.isdir(snap):
                continue
            try:
                names = os.listdir(snap)
            except OSError:
                continue
            if any(n in names for n in needles):
                return True
    except OSError:
        return False
    return False


def enforce_offline_if_cached(verbose: bool = True) -> bool:
    """Return True iff we just enforced offline mode (or it was already on).

    Requires not just the model directories to exist, but also a
    usable weights file inside each. Prevents offline-mode flipping on
    a partially downloaded cache (which would later crash at model load).
    """
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

    needed = ("models--BAAI--bge-m3", "models--BAAI--bge-reranker-v2-m3")
    for name in needed:
        path = os.path.join(hub_dir, name)
        if not os.path.isdir(path) or not _has_usable_weights(path):
            return False

    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    if verbose:
        print(
            "[offline-guard] HF cache complete (weights verified) — enforcing offline mode "
            "(HF_HUB_OFFLINE=1, TRANSFORMERS_OFFLINE=1)",
            file=sys.stderr,
        )
    return True
