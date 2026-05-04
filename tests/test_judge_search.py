"""Regression tests for the /judge_search endpoint.

The endpoint is the backend of the in-app Eval Sandbox panel and must
mirror `inference.py`'s output exactly. Anything that changes its shape
or makes it diverge from inference.py would silently break the judge UX
and the displayed Hit@3 / MRR@5 / latency numbers.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


def _ensure_indexed():
    """Skip the suite cleanly if the indices aren't built yet."""
    must_exist = [
        Path("data/index/bge_m3_dense.faiss"),
        Path("data/index/bm25.pkl"),
        Path("data/parsed_standards.json"),
    ]
    for p in must_exist:
        if not p.exists():
            pytest.skip(f"Indices not built: {p} missing — run setup.py first")


@pytest.fixture(scope="module")
def client():
    """Boot the FastAPI app once for the module via TestClient.

    TestClient triggers the lifespan handler, which loads the retriever
    just like the live demo backend. Heavy (~10-30 s) but only happens
    once per test session.
    """
    _ensure_indexed()
    try:
        from fastapi.testclient import TestClient

        from src.api.main import app
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"Could not import FastAPI app: {e}")
    with TestClient(app) as c:
        yield c


class TestJudgeSearchEndpoint:
    def test_route_registered(self):
        from src.api.main import app

        paths = {r.path for r in app.routes}
        assert "/judge_search" in paths

    def test_response_shape(self, client):
        r = client.post("/judge_search", json={"query": "ordinary portland cement 53 grade"})
        assert r.status_code == 200, r.text
        data = r.json()
        # Exactly the two keys we promise in JudgeSearchResponse.
        assert set(data.keys()) == {"retrieved_standards", "latency_seconds"}
        assert isinstance(data["retrieved_standards"], list)
        assert all(isinstance(x, str) for x in data["retrieved_standards"])
        assert len(data["retrieved_standards"]) <= 5
        assert isinstance(data["latency_seconds"], (int, float))
        assert data["latency_seconds"] >= 0

    def test_empty_query_rejected(self, client):
        # Pydantic Field(min_length=1) should reject empty input with 422.
        r = client.post("/judge_search", json={"query": ""})
        assert r.status_code == 422

    def test_parity_with_inference_py(self, client):
        """The endpoint must return the same retrieved codes as inference.py
        on the same query — this is the whole point of having a separate
        judge endpoint instead of reusing /search."""
        public = Path("datasets/public_test_set.json")
        if not public.exists():
            pytest.skip("public_test_set.json not present")
        items = json.loads(public.read_text(encoding="utf-8"))
        # Import the retriever directly — same object the lifespan built.
        from src.api.main import STATE

        retriever = STATE["retriever"]
        for it in items[:3]:  # 3 of 10 — keeps test runtime modest
            direct = [h.is_code for h in retriever.search(it["query"])[:5]]
            r = client.post("/judge_search", json={"query": it["query"]})
            assert r.status_code == 200
            via_api = r.json()["retrieved_standards"]
            assert direct == via_api, (
                f"Parity failure on {it['id']}: "
                f"retriever.search()={direct} vs /judge_search={via_api}"
            )

    def test_oversized_query_rejected(self, client):
        # Field(max_length=2000) — anything bigger should 422.
        r = client.post("/judge_search", json={"query": "x" * 2500})
        assert r.status_code == 422
