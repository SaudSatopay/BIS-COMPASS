"""Hackathon entry point. Judges run:

    python inference.py --input <input.json> --output <output.json>

Input JSON: list of objects each with at least `id` and `query` (and optionally
`expected_standards`, which we pass through unchanged).

Output JSON: same list with two fields added per item:
    - retrieved_standards : list[str]   (top-5 BIS codes)
    - latency_seconds     : float       (per-query wall-clock retrieval time)

Reliability guarantees:
  * Every item in the input produces exactly ONE output dict — no skips, no
    duplicates. This means `len(output) == len(input)` always, even when
    individual queries are malformed.
  * Output schema is uniform: every dict has `id`, `retrieved_standards`,
    `latency_seconds`. Original input fields (`query`, `expected_standards`)
    pass through when present.
  * `retrieved_standards` is at most 5 items. For empty / malformed queries
    we emit an empty list — the eval script tolerates this and counts the
    query as a miss, which is the honest behaviour.
  * `inference.py` makes ZERO network calls. The HF model cache is read at
    startup; set `HF_HUB_OFFLINE=1` to enforce this strictly after running
    `python scripts/setup_offline.py`.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


from src.offline_guard import enforce_offline_if_cached

enforce_offline_if_cached()

# Lazy-import retriever after env vars are loaded
from src.retrieval.retriever import Retriever  # noqa: E402


def _build_passthrough(item: dict, qid: str, retrieved: list[str], latency: float) -> dict:
    """Construct the per-item output. Always emits the three required keys
    (id, retrieved_standards, latency_seconds) plus any input fields we want
    to round-trip for the evaluator (query, expected_standards)."""
    out: dict = {"id": qid}
    if "query" in item:
        out["query"] = item["query"]
    if "expected_standards" in item:
        out["expected_standards"] = item["expected_standards"]
    out["retrieved_standards"] = retrieved
    out["latency_seconds"] = round(float(latency), 3)
    return out


def run(input_path: Path, output_path: Path) -> None:
    if not input_path.exists():
        print(f"[inference] input file does not exist: {input_path}", file=sys.stderr)
        sys.exit(2)

    try:
        with input_path.open(encoding="utf-8") as f:
            items = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[inference] input is not valid JSON: {e}", file=sys.stderr)
        sys.exit(2)

    if not isinstance(items, list):
        print(f"[inference] expected a JSON array at the root, got {type(items).__name__}", file=sys.stderr)
        sys.exit(2)

    print(f"[inference] Loaded {len(items)} queries from {input_path}", file=sys.stderr)

    print("[inference] Loading retriever (this loads bge-m3 + reranker once)...", file=sys.stderr)
    t0 = time.perf_counter()
    retriever = Retriever()
    print(f"[inference]   ready in {time.perf_counter() - t0:.1f}s", file=sys.stderr)

    results = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            qid = f"Q-{i:04d}"
            print(f"[inference]   {qid}: not a dict, returning empty result", file=sys.stderr)
            results.append(_build_passthrough({}, qid, [], 0.0))
            continue

        qid = str(item.get("id", f"Q-{i:04d}"))
        query = item.get("query", "")
        if not isinstance(query, str) or not query.strip():
            print(f"[inference]   {qid}: empty/non-string query, returning empty result", file=sys.stderr)
            results.append(_build_passthrough(item, qid, [], 0.0))
            continue

        t = time.perf_counter()
        try:
            hits = retriever.search(query)
        except Exception as e:
            # We never let one bad query take down the whole eval run.
            print(f"[inference]   {qid}: retriever raised {type(e).__name__}: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            results.append(_build_passthrough(item, qid, [], 0.0))
            continue
        latency = time.perf_counter() - t
        retrieved = [h.is_code for h in hits[:5]]
        results.append(_build_passthrough(item, qid, retrieved, latency))
        print(f"[inference]   {qid}: {latency*1000:.0f}ms -> {retrieved}", file=sys.stderr)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"[inference] Wrote {output_path}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="BIS RAG inference entry point")
    parser.add_argument("--input", type=Path, required=True, help="Path to input JSON")
    parser.add_argument("--output", type=Path, required=True, help="Path to write output JSON")
    args = parser.parse_args()
    run(args.input, args.output)


if __name__ == "__main__":
    main()
