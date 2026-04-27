"""Singleton wrapper around BAAI/bge-reranker-v2-m3 via sentence-transformers.

Using sentence-transformers' CrossEncoder is more robust across transformers
versions than FlagEmbedding's wrapper.
"""
from __future__ import annotations

import os
import torch
from sentence_transformers import CrossEncoder

_RERANKER: CrossEncoder | None = None


def get_reranker() -> CrossEncoder:
    """Singleton bge-reranker-v2-m3 loader. Honours HF_HUB_OFFLINE /
    TRANSFORMERS_OFFLINE for air-gapped runs."""
    global _RERANKER
    if _RERANKER is None:
        model_name = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _RERANKER = CrossEncoder(model_name, device=device, max_length=512)
    return _RERANKER


def rerank(query: str, passages: list[str]) -> list[float]:
    """Score (query, passage) pairs. Higher = more relevant.

    Scores are sigmoid-normalised to [0, 1] for stability.
    """
    if not passages:
        return []
    model = get_reranker()
    pairs = [(query, p) for p in passages]
    raw = model.predict(pairs, convert_to_numpy=True, show_progress_bar=False)
    # bge-reranker emits logits; squash to [0, 1]
    import numpy as np
    return (1.0 / (1.0 + np.exp(-raw))).tolist()
