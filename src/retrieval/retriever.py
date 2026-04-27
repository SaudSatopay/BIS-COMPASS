"""Hybrid retriever: BM25 + dense FAISS, fused via Reciprocal Rank Fusion,
then rerank top-K with bge-reranker-v2-m3 for final ordering.

All heavy state is loaded once at construction so per-query latency is
dominated by inference (embed + rerank), not I/O.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from src.retrieval.bm25_index import BM25Index
from src.retrieval.citation_prior import CitationPrior
from src.retrieval.colbert_index import ColBERTIndex
from src.retrieval.embedder import (
    encode_query_cached,
    encode_query_colbert_cached,
    get_embedder,
    warmup as warmup_embedder,
)
from src.retrieval.index import DenseIndex
from src.retrieval.metadata import category_overlap_boost, detect_categories
from src.retrieval.phrase_boost import phrase_boost
from src.retrieval.reranker import get_reranker, rerank


@dataclass
class Hit:
    is_code: str
    title: str
    scope: str
    dense_score: float
    bm25_score: float
    rrf_score: float
    rerank_score: float
    rank: int
    categories: tuple[str, ...] = ()
    category_boost: float = 0.0
    colbert_score: float = 0.0
    phrase_boost: float = 0.0
    citation_boost: float = 0.0


class Retriever:
    def __init__(
        self,
        index_dir: Path = Path("data/index"),
        whitelist_path: Path = Path("data/is_code_whitelist.json"),
        dense_k: int = 25,
        bm25_k: int = 25,
        rerank_k: int = 25,
        final_k: int = 5,
        rrf_c: int = 60,
        # ColBERT (multi-vector) is disabled by default. Ablation showed no
        # measurable Hit@3 / MRR@5 gain on either eval set, while it adds
        # ~50ms latency and ~470 MB index file. Set use_colbert=True only
        # for ablation runs.
        use_colbert: bool = False,
        colbert_pool_k: int = 50,
        # Phrase boost and citation prior are off by default. They each
        # marginally help on hard queries (e.g. BS-004 mortice locks) but
        # introduce ranking noise on the broader eval. Toggle on for ablation.
        use_phrase_boost: bool = False,
        use_citation_prior: bool = False,
    ):
        self.dense = DenseIndex(index_dir)
        self.sparse = BM25Index(index_dir)
        # ColBERT is optional — falls back gracefully if the index isn't built.
        self.colbert: ColBERTIndex | None = None
        if use_colbert:
            try:
                self.colbert = ColBERTIndex(index_dir)
            except FileNotFoundError:
                self.colbert = None
        self.colbert_pool_k = colbert_pool_k
        self.dense_k = dense_k
        self.bm25_k = bm25_k
        self.rerank_k = rerank_k
        self.final_k = final_k
        self.rrf_c = rrf_c
        self.use_phrase_boost = use_phrase_boost
        self.use_citation_prior = use_citation_prior

        with whitelist_path.open(encoding="utf-8") as f:
            wl = json.load(f)
        self.whitelist_norm: set[str] = set(wl["normalized"])

        self.citation_prior = CitationPrior()

        # Eagerly load both models so first query isn't slow
        get_embedder()
        get_reranker()
        # Warm up the embedder with a tiny throwaway encode so the first real
        # query doesn't pay tokenizer / kernel-init overhead (~120 ms).
        warmup_embedder()

    def _passage_text(self, meta: dict) -> str:
        parts = [f"{meta['is_code']} {meta['title']}"]
        if meta.get("scope"):
            parts.append(meta["scope"])
        return ". ".join(parts)

    def _rrf_fuse(
        self,
        dense: list[tuple[int, float]],
        sparse: list[tuple[int, float]],
    ) -> list[tuple[int, float, float, float]]:
        """Backward-compatible 2-list fuse. Returns (idx, rrf, dense, bm25)."""
        c = self.rrf_c
        rrf: dict[int, float] = {}
        dscore: dict[int, float] = {}
        bscore: dict[int, float] = {}
        for rank, (idx, score) in enumerate(dense, start=1):
            rrf[idx] = rrf.get(idx, 0.0) + 1.0 / (c + rank)
            dscore[idx] = score
        for rank, (idx, score) in enumerate(sparse, start=1):
            rrf[idx] = rrf.get(idx, 0.0) + 1.0 / (c + rank)
            bscore[idx] = score
        fused = sorted(rrf.items(), key=lambda kv: kv[1], reverse=True)
        return [(idx, score, dscore.get(idx, 0.0), bscore.get(idx, 0.0)) for idx, score in fused]

    def _rrf_fuse_multi(
        self, ranked_lists: list[list[tuple[int, float]]]
    ) -> list[tuple[int, float, float, float]]:
        """Generalised RRF over an arbitrary number of ranked lists.

        Convention: the first list is treated as the canonical 'dense' list,
        the second as 'sparse', and any further lists are auxiliary (e.g. from
        multi-query expansion). The dense_score and bm25_score in the output
        carry the *original* dense/BM25 scores for tracing — fused score is
        the sum of RRF contributions.
        """
        c = self.rrf_c
        rrf: dict[int, float] = {}
        dscore: dict[int, float] = {}
        bscore: dict[int, float] = {}
        for li, lst in enumerate(ranked_lists):
            for rank, (idx, score) in enumerate(lst, start=1):
                rrf[idx] = rrf.get(idx, 0.0) + 1.0 / (c + rank)
                if li == 0:  # canonical dense
                    dscore.setdefault(idx, score)
                elif li == 1:  # canonical sparse
                    bscore.setdefault(idx, score)
        fused = sorted(rrf.items(), key=lambda kv: kv[1], reverse=True)
        return [(idx, score, dscore.get(idx, 0.0), bscore.get(idx, 0.0)) for idx, score in fused]

    def search(
        self,
        query: str,
        dense_query: str | None = None,
        multi_queries: list[str] | None = None,
    ) -> list[Hit]:
        """Retrieve top-K hits.

        `dense_query` lets a rewriter pass an expanded version for embedding while
        keeping the original `query` for BM25 (which prefers verbatim user terminology).

        `multi_queries`, when provided, are additional paraphrased variants. We
        retrieve dense+sparse for EACH and RRF-merge all the lists. This widens
        the candidate pool and tends to lift recall on out-of-vocabulary queries.
        """
        # 1) Dense recall (use expanded query if provided) — cached path
        qv = encode_query_cached(dense_query or query)
        dense_hits = self.dense.search(qv, top_k=self.dense_k)
        # 2) Sparse recall on the literal user query
        sparse_hits = self.sparse.search(query, top_k=self.bm25_k)

        # 2b) Multi-query expansion: pull dense+sparse for each variant and feed
        # them all into RRF. Each variant adds two more ranked lists.
        extra_lists: list[list[tuple[int, float]]] = []
        for v in (multi_queries or [])[:5]:
            v = v.strip()
            if not v or v == query:
                continue
            extra_lists.append(self.dense.search(encode_query_cached(v), top_k=self.dense_k))
            extra_lists.append(self.sparse.search(v, top_k=self.bm25_k))

        # 2c) ColBERT late-interaction: score the union of dense+sparse top
        # candidates and sort to produce a third ranked list. Late interaction
        # is much more sensitive to specific terms (M30, mortice) than the
        # pooled dense vector — a known win for technical domains.
        colbert_scores_by_idx: dict[int, float] = {}
        if self.colbert is not None:
            cand_pool = list({i for i, _ in dense_hits[: self.colbert_pool_k]} |
                             {i for i, _ in sparse_hits[: self.colbert_pool_k]})
            if cand_pool:
                qv_cb = encode_query_colbert_cached(query)
                cb_scores = self.colbert.score_candidates(qv_cb, cand_pool)
                colbert_ranked = sorted(zip(cand_pool, cb_scores), key=lambda kv: kv[1], reverse=True)
                colbert_scores_by_idx = dict(zip(cand_pool, cb_scores))
                extra_lists.append(colbert_ranked[: self.dense_k])

        # 3) Reciprocal Rank Fusion across all available ranked lists
        fused = self._rrf_fuse_multi([dense_hits, sparse_hits, *extra_lists])
        if not fused:
            return []

        candidates = fused[: self.rerank_k]
        cand_meta = [self.dense.meta[i] for i, _, _, _ in candidates]
        cand_passages = [self._passage_text(m) for m in cand_meta]

        # 4) Cross-encoder rerank (uses original query — capture the user's intent literally)
        rerank_scores = rerank(query, cand_passages)

        # 5) Score-time priors — each is a small additive bonus on the rerank
        # score, capped so they can only break ties between near-equal reranks.
        #   (a) category overlap: query material vs candidate material  [always on]
        #   (b) phrase boost: shared technical n-grams                  [opt-in]
        #   (c) citation prior: how often this code is cited in SP 21   [opt-in]
        query_cats = detect_categories(query)
        cat_boosts: list[float] = []
        phrase_boosts_l: list[float] = []
        cite_boosts: list[float] = []
        cand_cats: list[set[str]] = []
        for k in range(len(candidates)):
            passage = cand_passages[k]
            cats = detect_categories(passage)
            cand_cats.append(cats)
            cat_boosts.append(category_overlap_boost(query_cats, passage))
            phrase_boosts_l.append(phrase_boost(query, passage) if self.use_phrase_boost else 0.0)
            cite_boosts.append(
                self.citation_prior.boost(cand_meta[k]["is_code"])
                if self.use_citation_prior else 0.0
            )
        adjusted = [
            rerank_scores[k] + cat_boosts[k] + phrase_boosts_l[k] + cite_boosts[k]
            for k in range(len(candidates))
        ]
        order = sorted(range(len(candidates)), key=lambda k: adjusted[k], reverse=True)

        hits: list[Hit] = []
        seen: set[str] = set()
        for k in order:
            idx, rrf_s, d_s, b_s = candidates[k]
            meta = cand_meta[k]
            code = meta["is_code"]
            if code in seen:
                continue
            seen.add(code)
            hits.append(Hit(
                is_code=code,
                title=meta["title"],
                scope=meta.get("scope", ""),
                dense_score=d_s,
                bm25_score=b_s,
                rrf_score=rrf_s,
                rerank_score=float(rerank_scores[k]),
                rank=len(hits) + 1,
                categories=tuple(sorted(cand_cats[k])),
                category_boost=float(cat_boosts[k]),
                colbert_score=float(colbert_scores_by_idx.get(idx, 0.0)),
                phrase_boost=float(phrase_boosts_l[k]),
                citation_boost=float(cite_boosts[k]),
            ))
            if len(hits) >= self.final_k:
                break
        return hits

    def is_valid_code(self, code: str) -> bool:
        import re
        norm = re.sub(r"\s+", "", code).lower()
        return norm in self.whitelist_norm
