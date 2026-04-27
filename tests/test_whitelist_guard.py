"""Tests for the IS-code whitelist anti-hallucination guard."""
import json
from pathlib import Path

import pytest


def _whitelist():
    p = Path("data/is_code_whitelist.json")
    if not p.exists():
        pytest.skip("Whitelist not built — run `python -m src.ingestion.pdf_parser` first")
    return json.loads(p.read_text(encoding="utf-8"))


class TestWhitelistShape:
    def test_loads(self):
        wl = _whitelist()
        assert "canonical" in wl and "normalized" in wl
        assert isinstance(wl["canonical"], list)
        assert isinstance(wl["normalized"], list)

    def test_normalized_lowercased_and_stripped(self):
        wl = _whitelist()
        for code in wl["normalized"]:
            assert " " not in code
            assert code == code.lower()

    def test_contains_known_public_test_codes(self):
        wl = _whitelist()
        normed = set(wl["normalized"])
        # Pulled from datasets/public_test_set.json
        for code in [
            "IS 269: 1989", "IS 383: 1970", "IS 458: 2003",
            "IS 2185 (Part 2): 1983", "IS 459: 1992",
            "IS 455: 1989", "IS 1489 (Part 2): 1991",
            "IS 3466: 1988", "IS 6909: 1990", "IS 8042: 1989",
        ]:
            normalized = code.replace(" ", "").lower()
            assert normalized in normed, f"Public test code missing from whitelist: {code}"


class TestRetrieverGuard:
    """Smoke-test that the production retriever respects the whitelist."""

    def test_is_valid_code(self):
        # Lazy import so the test file collects cleanly even if the index
        # hasn't been built yet.
        try:
            from src.retrieval.retriever import Retriever
        except Exception:
            pytest.skip("Retriever import failed — env likely not initialised")
        try:
            r = Retriever()
        except FileNotFoundError:
            pytest.skip("Index not built — run scripts.build_index first")
        assert r.is_valid_code("IS 269: 1989") is True
        assert r.is_valid_code("IS 99999: 2999") is False
        # Casing / spacing tolerated
        assert r.is_valid_code("is269:1989") is True
