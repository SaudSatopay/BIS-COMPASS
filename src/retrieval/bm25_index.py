"""BM25 sparse index over the same standards as the dense FAISS index.

Fast, in-memory, ~100KB serialised. Used in hybrid retrieval alongside dense
embeddings to catch queries with rare technical terms (e.g. "mortice lock",
"M30", specific grade codes) where lexical match outperforms semantics.
"""
from __future__ import annotations

import json
import pickle
import re
from pathlib import Path

from rank_bm25 import BM25Okapi

INDEX_FILE = "bm25.pkl"


_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-]*|\d+")


def tokenize(text: str) -> list[str]:
    """Lowercase, alphanumeric tokenisation. Preserves grade codes like 'M30', 'OPC33'."""
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


def build_corpus_text(s: dict) -> str:
    """Tokenisation target. The title is repeated 3× because BM25 IDF treats
    each occurrence as an independent term hit — multiple title mentions
    boost rare-term scores (e.g. 'mortice' becomes a stronger signal for
    standards whose title contains it)."""
    title = s["title"]
    parts = [
        s["is_code"],
        title, title, title,           # title-reweighting
        s.get("scope") or "",
        (s.get("full_text") or "")[:1500],
    ]
    return " ".join(parts)


def build_index(standards_path: Path, out_dir: Path, force: bool = False) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_idx = out_dir / INDEX_FILE

    # Idempotency: skip if a non-empty index already exists. Committed in
    # the repo so a fresh clone has it. Pass force=True to override.
    if not force and out_idx.exists() and out_idx.stat().st_size > 1024:
        print(f"BM25 index already exists at {out_idx} — skipping rebuild.")
        return

    with standards_path.open(encoding="utf-8") as f:
        standards = json.load(f)
    docs_tokens = [tokenize(build_corpus_text(s)) for s in standards]
    bm25 = BM25Okapi(docs_tokens)
    with out_idx.open("wb") as f:
        pickle.dump({"bm25": bm25, "n_docs": len(docs_tokens)}, f)
    print(f"BM25 index built ({len(docs_tokens)} docs) -> {out_idx}")


class BM25Index:
    def __init__(self, index_dir: Path):
        with (index_dir / INDEX_FILE).open("rb") as f:
            obj = pickle.load(f)
        self.bm25: BM25Okapi = obj["bm25"]

    def search(self, query: str, top_k: int = 25) -> list[tuple[int, float]]:
        toks = tokenize(query)
        if not toks:
            return []
        scores = self.bm25.get_scores(toks)
        # argsort descending
        idxs = scores.argsort()[::-1][:top_k]
        return [(int(i), float(scores[i])) for i in idxs if scores[i] > 0]


def main():
    build_index(Path("data/parsed_standards.json"), Path("data/index"))


if __name__ == "__main__":
    main()
