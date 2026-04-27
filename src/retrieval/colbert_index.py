"""ColBERT (multi-vector) index over the SP 21 standards.

We piggy-back on bge-m3's `colbert_vecs` output: each document becomes a list
of per-token 1024-d vectors. At query time we compute MaxSim late-interaction
between query tokens and doc tokens — this is more sensitive to specific
terms (e.g. 'M30', 'mortice') than the pooled dense vector.

Storage is via numpy `.npz` (one entry per doc) — small (~50 MB for 559 docs)
and fast to load.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from src.retrieval.embedder import encode_with_colbert, colbert_score
from src.retrieval.index import build_embedding_text

INDEX_FILE = "colbert.npz"
META_FILE = "colbert_meta.json"


def build_index(standards_path: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with standards_path.open(encoding="utf-8") as f:
        standards = json.load(f)
    texts = [build_embedding_text(s) for s in standards]
    print(f"Encoding {len(texts)} standards with bge-m3 (dense + ColBERT) ...")
    _, colbert = encode_with_colbert(texts, batch_size=8, max_length=1024)
    print(f"  ColBERT vector counts: min={min(len(v) for v in colbert)} "
          f"max={max(len(v) for v in colbert)} "
          f"mean={sum(len(v) for v in colbert) / len(colbert):.1f}")

    # Save as npz with a key per doc
    arrays = {f"d{i:04d}": v for i, v in enumerate(colbert)}
    np.savez_compressed(out_dir / INDEX_FILE, **arrays)
    meta = {"n_docs": len(colbert)}
    (out_dir / META_FILE).write_text(json.dumps(meta), encoding="utf-8")
    size_mb = (out_dir / INDEX_FILE).stat().st_size / 1e6
    print(f"  -> {out_dir / INDEX_FILE} ({size_mb:.1f} MB)")


class ColBERTIndex:
    """Lazy-loaded ColBERT index. Vectors are mmap-loaded on first access."""

    def __init__(self, index_dir: Path):
        path = index_dir / INDEX_FILE
        if not path.exists():
            raise FileNotFoundError(f"ColBERT index not built: {path}")
        self._npz = np.load(path)
        self._meta = json.loads((index_dir / META_FILE).read_text(encoding="utf-8"))
        self.n_docs = self._meta["n_docs"]
        self._cache: dict[int, np.ndarray] = {}

    def doc(self, idx: int) -> np.ndarray:
        if idx not in self._cache:
            self._cache[idx] = self._npz[f"d{idx:04d}"]
        return self._cache[idx]

    def score_candidates(
        self, query_vecs: np.ndarray, candidate_idxs: list[int]
    ) -> list[float]:
        """Score a list of candidate doc indices against query token vectors."""
        return [colbert_score(query_vecs, self.doc(i)) for i in candidate_idxs]


def main():
    build_index(Path("data/parsed_standards.json"), Path("data/index"))


if __name__ == "__main__":
    main()
