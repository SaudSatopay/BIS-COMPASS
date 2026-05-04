"""Regression test: `python inference.py` must succeed with no network access
once the HF cache has been populated.

We can't truly disable the OS network stack from inside pytest, but we can
assert the SAME guarantees by:
  1. Verifying inference.py auto-enables HF_HUB_OFFLINE / TRANSFORMERS_OFFLINE
     when the cache is present (the function is exposed for testing).
  2. Verifying that with those env vars set, `from src.retrieval.retriever
     import Retriever; Retriever()` succeeds — i.e. the model loaders honour
     them and don't fail.
  3. Verifying the public eval still scores 100% Hit@3 in this mode (sanity).

If a future change accidentally re-introduces a network call in the eval
path, this test fails.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent


def _hf_cache_has_models() -> bool:
    """Cheap probe — same heuristic inference.py uses internally."""
    hf_home = os.environ.get("HF_HOME") or os.path.join(
        os.path.expanduser("~"), ".cache", "huggingface"
    )
    hub = Path(hf_home) / "hub"
    if not hub.is_dir():
        return False
    needed = {"models--BAAI--bge-m3", "models--BAAI--bge-reranker-v2-m3"}
    return needed.issubset({d.name for d in hub.iterdir()})


@pytest.mark.skipif(not _hf_cache_has_models(),
                    reason="HF cache not populated (run scripts/setup_offline.py first)")
class TestOfflineInference:
    def test_inference_auto_enables_offline_mode(self, tmp_path):
        """Run inference.py as a subprocess and check the offline-mode banner appears."""
        out = tmp_path / "out.json"
        env = {**os.environ}
        env.pop("HF_HUB_OFFLINE", None)
        env.pop("TRANSFORMERS_OFFLINE", None)
        env["HF_FORCE_NETWORK"] = "0"

        result = subprocess.run(
            [sys.executable, "inference.py",
             "--input", "datasets/public_test_set.json",
             "--output", str(out)],
            # encoding="utf-8" + errors="replace" force the parent process to
            # decode the child's stdout/stderr as UTF-8 instead of the parent's
            # locale (which is cp1252 on stock Windows cmd). inference.py's
            # offline_guard banner contains the ✓ glyph; without these args,
            # subprocess.run raises UnicodeDecodeError on Windows the moment
            # it tries to decode the banner.
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            cwd=str(ROOT), env=env, timeout=300,
        )
        assert result.returncode == 0, f"inference.py exited {result.returncode}: {result.stderr[-500:]}"
        assert "enforcing offline mode" in result.stderr.lower(), \
            f"expected offline-mode banner; got stderr:\n{result.stderr[-500:]}"

    def test_offline_inference_still_scores_100(self, tmp_path):
        """Eval pipeline, run with offline env vars set, still hits 100% Hit@3 on public."""
        out = tmp_path / "out.json"
        env = {**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}

        result = subprocess.run(
            [sys.executable, "inference.py",
             "--input", "datasets/public_test_set.json",
             "--output", str(out)],
            # See docstring of test_inference_auto_enables_offline_mode above
            # — UTF-8 decode is required on stock Windows cmd to avoid a
            # UnicodeDecodeError on the banner glyphs.
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            cwd=str(ROOT), env=env, timeout=300,
        )
        assert result.returncode == 0, f"inference.py exited {result.returncode}"
        data = json.loads(out.read_text(encoding="utf-8"))
        assert len(data) == 10

        # Schema check — required keys
        for item in data:
            assert "id" in item
            assert "retrieved_standards" in item
            assert "latency_seconds" in item
            assert isinstance(item["retrieved_standards"], list)
            assert len(item["retrieved_standards"]) == 5

        # Hit@3 sanity (we don't recompute the full metric — just confirm
        # at least one expected standard is in the top 3 for every query).
        import re
        def _norm(s): return re.sub(r"\s+", "", s).lower()
        for item in data:
            expected = {_norm(s) for s in item.get("expected_standards", [])}
            top3 = [_norm(c) for c in item["retrieved_standards"][:3]]
            assert any(c in expected for c in top3), \
                f"{item['id']} expected one of {expected} in top-3; got {top3}"
