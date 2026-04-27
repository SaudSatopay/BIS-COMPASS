"""Ablation study: measure Hit@3, MRR@5, latency for several retriever variants
on the same eval sets. Writes results to data/results/ablation.json + a
markdown table for the README/slide deck.

Variants compared:
  - dense_only     : bge-m3 dense + FAISS, no BM25, no rerank
  - bm25_only      : BM25 sparse only, no dense, no rerank
  - hybrid_no_rrf  : dense top-5 (BM25 unused) + cross-encoder rerank
  - hybrid_rrf     : BM25 + dense + RRF, no rerank
  - full           : BM25 + dense + RRF + rerank + category boost (current default)

Usage:
    python -m scripts.ablation
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from src.offline_guard import enforce_offline_if_cached  # noqa: E402

enforce_offline_if_cached()

import numpy as np  # noqa: E402

from src.retrieval.bm25_index import BM25Index  # noqa: E402
from src.retrieval.embedder import encode_query_cached, get_embedder, warmup  # noqa: E402
from src.retrieval.index import DenseIndex  # noqa: E402
from src.retrieval.citation_prior import CitationPrior  # noqa: E402
from src.retrieval.colbert_index import ColBERTIndex  # noqa: E402
from src.retrieval.metadata import category_overlap_boost, detect_categories  # noqa: E402
from src.retrieval.phrase_boost import phrase_boost as phrase_boost_fn  # noqa: E402
from src.retrieval.reranker import get_reranker, rerank  # noqa: E402

INDEX_DIR = Path("data/index")


@dataclass
class Variant:
    name: str
    description: str


VARIANTS = [
    Variant("dense_only",          "bge-m3 dense + FAISS only"),
    Variant("bm25_only",           "BM25 sparse only"),
    Variant("hybrid_rrf",          "BM25 + dense + RRF (no rerank)"),
    Variant("hybrid_rerank",       "BM25 + dense + RRF + cross-encoder rerank"),
    Variant("full",                "Hybrid + ColBERT + rerank + category boost (production)"),
    Variant("full_phrase_cite",    "Production + phrase boost + citation prior (ablation)"),
]


class AblationRetriever:
    """Single retriever object that can run any variant on demand."""

    def __init__(self):
        self.dense = DenseIndex(INDEX_DIR)
        self.sparse = BM25Index(INDEX_DIR)
        try:
            self.colbert = ColBERTIndex(INDEX_DIR)
        except FileNotFoundError:
            self.colbert = None
        self.citation_prior = CitationPrior()
        get_embedder()
        get_reranker()
        warmup()

    def _passage(self, m: dict) -> str:
        parts = [f"{m['is_code']} {m['title']}"]
        if m.get("scope"):
            parts.append(m["scope"])
        return ". ".join(parts)

    def _rrf(self, lists: list[list[tuple[int, float]]], c: int = 60) -> list[int]:
        scores: dict[int, float] = {}
        for lst in lists:
            for rank, (idx, _) in enumerate(lst, start=1):
                scores[idx] = scores.get(idx, 0.0) + 1.0 / (c + rank)
        return [idx for idx, _ in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)]

    def search(self, query: str, variant: str, top_k: int = 5) -> tuple[list[str], float]:
        t0 = time.perf_counter()

        if variant == "dense_only":
            qv = encode_query_cached(query)
            hits = self.dense.search(qv, top_k=top_k)
            codes = [self.dense.meta[i]["is_code"] for i, _ in hits]

        elif variant == "bm25_only":
            hits = self.sparse.search(query, top_k=top_k)
            codes = [self.dense.meta[i]["is_code"] for i, _ in hits]

        elif variant == "hybrid_rrf":
            qv = encode_query_cached(query)
            d = self.dense.search(qv, top_k=25)
            s = self.sparse.search(query, top_k=25)
            order = self._rrf([d, s])[:top_k]
            codes = [self.dense.meta[i]["is_code"] for i in order]

        elif variant == "hybrid_rerank":
            qv = encode_query_cached(query)
            d = self.dense.search(qv, top_k=25)
            s = self.sparse.search(query, top_k=25)
            cand_idxs = self._rrf([d, s])[:25]
            cand_metas = [self.dense.meta[i] for i in cand_idxs]
            cand_pas = [self._passage(m) for m in cand_metas]
            scores = rerank(query, cand_pas)
            order = sorted(range(len(cand_idxs)), key=lambda k: scores[k], reverse=True)[:top_k]
            codes = [cand_metas[k]["is_code"] for k in order]

        elif variant in ("full", "full_phrase_cite"):
            qv = encode_query_cached(query)
            d = self.dense.search(qv, top_k=25)
            s = self.sparse.search(query, top_k=25)

            # ColBERT: late-interaction over the union of dense+sparse candidates
            extra_lists: list[list[tuple[int, float]]] = []
            if self.colbert is not None:
                pool = list({i for i, _ in d[:50]} | {i for i, _ in s[:50]})
                from src.retrieval.embedder import encode_query_colbert_cached
                qv_cb = encode_query_colbert_cached(query)
                cb = self.colbert.score_candidates(qv_cb, pool)
                extra_lists.append(sorted(zip(pool, cb), key=lambda kv: kv[1], reverse=True)[:25])

            cand_idxs = self._rrf([d, s, *extra_lists])[:25]
            cand_metas = [self.dense.meta[i] for i in cand_idxs]
            cand_pas = [self._passage(m) for m in cand_metas]
            scores = rerank(query, cand_pas)
            qcats = detect_categories(query)
            adj = []
            for k in range(len(cand_idxs)):
                bonus = category_overlap_boost(qcats, cand_pas[k])
                if variant == "full_phrase_cite":
                    bonus += phrase_boost_fn(query, cand_pas[k])
                    bonus += self.citation_prior.boost(cand_metas[k]["is_code"])
                adj.append(scores[k] + bonus)
            order = sorted(range(len(cand_idxs)), key=lambda k: adj[k], reverse=True)[:top_k]
            codes = [cand_metas[k]["is_code"] for k in order]

        else:
            raise ValueError(f"Unknown variant: {variant}")

        return codes, time.perf_counter() - t0


def normalize(s: str) -> str:
    import re
    return re.sub(r"\s+", "", s).lower()


def evaluate(retriever: AblationRetriever, variant: str, queries: list[dict]) -> dict:
    hits3 = 0
    mrr_sum = 0.0
    total_latency = 0.0
    per_query = []
    for q in queries:
        retrieved, lat = retriever.search(q["query"], variant)
        total_latency += lat
        expected = {normalize(s) for s in q.get("expected_standards", [])}
        normed = [normalize(c) for c in retrieved]
        hit3 = any(c in expected for c in normed[:3])
        if hit3:
            hits3 += 1
        mrr = 0.0
        for rank, c in enumerate(normed[:5], start=1):
            if c in expected:
                mrr = 1.0 / rank
                break
        mrr_sum += mrr
        per_query.append({"id": q["id"], "retrieved": retrieved, "hit@3": hit3, "rr": mrr, "lat": round(lat, 3)})
    n = max(1, len(queries))
    return {
        "variant": variant,
        "n": len(queries),
        "hit_at_3": round(100.0 * hits3 / n, 2),
        "mrr_at_5": round(mrr_sum / n, 4),
        "avg_latency_s": round(total_latency / n, 3),
        "per_query": per_query,
    }


def main():
    eval_sets = {
        "public":    Path("datasets/public_test_set.json"),
        "bootstrap": Path("data/bootstrap_test_set.json"),
    }
    print("Loading retriever (one-time model load) ...")
    R = AblationRetriever()

    out: dict = {"variants": [v.name for v in VARIANTS], "descriptions": {v.name: v.description for v in VARIANTS}, "results": {}}

    for set_name, path in eval_sets.items():
        if not path.exists():
            print(f"skip {set_name}: file missing")
            continue
        with path.open(encoding="utf-8") as f:
            queries = json.load(f)
        print(f"\nEval set: {set_name} ({len(queries)} queries)")
        out["results"][set_name] = {}
        for v in VARIANTS:
            res = evaluate(R, v.name, queries)
            out["results"][set_name][v.name] = res
            print(f"  {v.name:18s}  Hit@3 {res['hit_at_3']:6.2f}%   MRR@5 {res['mrr_at_5']:.4f}   {res['avg_latency_s']:.3f}s")

    out_path = Path("data/results/ablation.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\nWrote {out_path}")

    # Build a markdown table
    md_path = Path("docs/ablation.md")
    lines = ["# Retrieval ablation\n"]
    for set_name, set_results in out["results"].items():
        lines.append(f"\n## {set_name} test set ({set_results[VARIANTS[0].name]['n']} queries)\n")
        lines.append("| Variant | Description | Hit@3 | MRR@5 | Avg latency |")
        lines.append("|---|---|---:|---:|---:|")
        for v in VARIANTS:
            r = set_results[v.name]
            lines.append(
                f"| `{v.name}` | {v.description} | {r['hit_at_3']:.2f}% | {r['mrr_at_5']:.4f} | {r['avg_latency_s']:.3f}s |"
            )
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
