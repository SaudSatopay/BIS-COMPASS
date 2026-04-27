"""Calibrate the rerank-score → confidence-band mapping against the bootstrap
eval set. Today's thresholds (0.65 / 0.35) were hand-set; this script measures
the actual correctness rate at each rerank-score percentile and recommends
data-driven thresholds.

Method: run the retriever over the bootstrap set; for every (rank, rerank_score,
correct?) tuple, find score thresholds that maximise the precision difference
between bands while keeping HIGH band ≥85% precision.
"""
from __future__ import annotations

import json
import re
import statistics
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from src.offline_guard import enforce_offline_if_cached  # noqa: E402

enforce_offline_if_cached()

from src.retrieval.retriever import Retriever  # noqa: E402


def normalize(s: str) -> str:
    return re.sub(r"\s+", "", s).lower()


def main():
    queries_path = Path("data/bootstrap_test_set.json")
    queries = json.loads(queries_path.read_text(encoding="utf-8"))
    retriever = Retriever()

    # Collect every top-5 hit with whether it was correct.
    samples: list[tuple[float, bool]] = []
    for q in queries:
        expected = {normalize(s) for s in q.get("expected_standards", [])}
        for h in retriever.search(q["query"]):
            samples.append((h.rerank_score, normalize(h.is_code) in expected))

    samples.sort(key=lambda x: x[0], reverse=True)
    print(f"\nCollected {len(samples)} (score, correct) samples from "
          f"{len(queries)} queries × top-5\n")

    # Score histogram by score bucket
    buckets = [(0.95, 1.01), (0.85, 0.95), (0.70, 0.85), (0.55, 0.70),
               (0.40, 0.55), (0.25, 0.40), (0.10, 0.25), (0.0, 0.10)]
    print(f"{'score range':>14}  {'n':>4}  {'correct':>7}  {'precision':>10}")
    for lo, hi in buckets:
        in_bucket = [s for s in samples if lo <= s[0] < hi]
        if not in_bucket:
            continue
        n = len(in_bucket)
        correct = sum(1 for _, ok in in_bucket if ok)
        prec = correct / n
        print(f"  [{lo:.2f}, {hi:.2f})  {n:4d}  {correct:7d}  {prec:>9.1%}")

    # Recommend thresholds:
    #   HIGH band: precision ≥ 0.85 (conservative — only label "high" when
    #              the rerank score reliably marks a correct hit)
    #   MEDIUM:    precision ≥ 0.40
    #   LOW:       everything else
    correct_counts = []
    cum_total = 0
    cum_correct = 0
    high_threshold: float | None = None
    medium_threshold: float | None = None
    for score, ok in samples:
        cum_total += 1
        if ok:
            cum_correct += 1
        prec = cum_correct / cum_total
        # The HIGH cutoff is the LOWEST score where cumulative precision is ≥ 0.85
        if high_threshold is None and cum_total >= 5 and prec < 0.85:
            high_threshold = score
        if medium_threshold is None and cum_total >= 10 and prec < 0.40:
            medium_threshold = score

    print(f"\nRecommended thresholds (calibrated on bootstrap):")
    print(f"  HIGH   >= {high_threshold:.3f}" if high_threshold else "  HIGH   >= 0.65 (default)")
    print(f"  MEDIUM >= {medium_threshold:.3f}" if medium_threshold else "  MEDIUM >= 0.35 (default)")

    out = {
        "n_samples": len(samples),
        "n_queries": len(queries),
        "buckets": [
            {
                "lo": lo, "hi": hi,
                "n": sum(1 for score, _ in samples if lo <= score < hi),
                "correct": sum(1 for score, ok in samples if lo <= score < hi and ok),
            }
            for lo, hi in buckets
        ],
        "recommended": {
            "high_threshold": high_threshold or 0.65,
            "medium_threshold": medium_threshold or 0.35,
        },
    }
    Path("data/results").mkdir(parents=True, exist_ok=True)
    Path("data/results/confidence_calibration.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8"
    )
    print(f"\nWrote data/results/confidence_calibration.json")


if __name__ == "__main__":
    main()
