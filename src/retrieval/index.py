"""Build and load the FAISS dense index over parsed BIS standards."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import faiss
import numpy as np

from src.retrieval.embedder import encode

INDEX_FILE = "bge_m3_dense.faiss"
META_FILE = "standards_meta.json"


@dataclass
class StandardMeta:
    is_code: str
    is_code_norm: str
    title: str
    scope: str
    revision: str | None
    page_start: int
    page_end: int


def build_embedding_text(s: dict) -> str:
    """The text we embed per standard.

    Engineering choices:
      1. Title is repeated TWICE (once at top, once after scope) so its tokens
         dominate the pooled embedding — empirically the highest-signal field
         for query→standard matching.
      2. We frame the document with "Indian Standard for ..." prefix to align
         with the kind of paraphrase MSE owners actually type.
      3. Scope is included verbatim — it's the closest thing to a description
         the original document offers.
      4. First 1000 chars of body give the embedder extra technical vocabulary
         (e.g. specific grade ranges, test methods).
    """
    title = s["title"].strip()
    code = s["is_code"]
    scope = (s.get("scope") or "").strip()
    body_excerpt = (s.get("full_text") or "")[:1000]
    parts = [
        f"Indian Standard for {title}.",
        f"{code} — {title}.",
    ]
    if scope:
        parts.append(f"Scope: {scope}")
    parts.append(f"Title: {title}.")  # second mention; pool will weight it more
    if body_excerpt:
        parts.append(body_excerpt)
    return "\n".join(parts)


def build_index(standards_path: Path, out_dir: Path, force: bool = False) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_idx = out_dir / INDEX_FILE
    out_meta = out_dir / META_FILE

    # Idempotency: skip if a non-empty index already exists. This file is
    # committed in the repo so a fresh `git clone` already has it — there's
    # no need to recompute embeddings (which on CPU takes ~7 min).
    # Set force=True to override.
    if (
        not force
        and out_idx.exists()
        and out_meta.exists()
        and out_idx.stat().st_size > 1024
    ):
        print(f"Dense index already exists at {out_idx} ({out_idx.stat().st_size:,} bytes) — skipping rebuild.")
        print("(Set force=True or delete the file to recompute embeddings.)")
        return

    with standards_path.open(encoding="utf-8") as f:
        standards = json.load(f)

    texts = [build_embedding_text(s) for s in standards]
    print(f"Embedding {len(texts)} standards with bge-m3 ...")
    vecs = encode(texts, batch_size=16, max_length=1024)
    print(f"  dense vectors shape: {vecs.shape}")

    dim = vecs.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(vecs)

    faiss.write_index(index, str(out_dir / INDEX_FILE))

    meta = [{
        "is_code": s["is_code"],
        "is_code_norm": s["is_code_norm"],
        "title": s["title"],
        "scope": s["scope"],
        "revision": s.get("revision"),
        "page_start": s["page_start"],
        "page_end": s["page_end"],
    } for s in standards]
    (out_dir / META_FILE).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  -> {out_dir / INDEX_FILE}")
    print(f"  -> {out_dir / META_FILE}")


class DenseIndex:
    """In-memory dense FAISS index loaded once at startup."""

    def __init__(self, index_dir: Path):
        self.index = faiss.read_index(str(index_dir / INDEX_FILE))
        with (index_dir / META_FILE).open(encoding="utf-8") as f:
            self.meta: list[dict] = json.load(f)

    def search(self, query_vec: np.ndarray, top_k: int = 20) -> list[tuple[int, float]]:
        """Return list of (doc_idx, score) sorted by descending score."""
        if query_vec.ndim == 1:
            query_vec = query_vec[None, :]
        scores, idxs = self.index.search(query_vec.astype(np.float32), top_k)
        return [(int(i), float(s)) for i, s in zip(idxs[0], scores[0]) if i >= 0]


def main():
    from pathlib import Path
    build_index(Path("data/parsed_standards.json"), Path("data/index"))


if __name__ == "__main__":
    main()
