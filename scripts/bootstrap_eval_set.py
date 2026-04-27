"""Bootstrap a synthetic eval set from SP 21 standards using Gemini.

Strategy: stratified sample across page ranges (which serve as a proxy for
material category in SP 21), then ask Gemini to write a realistic MSE-owner
question for each. We dedupe and write a JSON shaped exactly like
public_test_set.json so eval_script.py works on it directly.

Usage:
    python scripts/bootstrap_eval_set.py --n 50 --out data/bootstrap_test_set.json
"""
from __future__ import annotations

import argparse
import json
import random
import re
import time
from pathlib import Path

from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

from src.llm.gemini_client import GeminiClient  # noqa: E402

CATEGORY_ANCHORS = [
    # SP 21 is laid out by section: cement, lime, concrete, aggregates, bricks,
    # tiles, pipes, steel, glass, paints, etc. Page ranges below are coarse
    # buckets and get filled in by sampling. Standards in the front matter
    # (pages < 20) are skipped.
    ("cement",       (20, 80)),
    ("aggregates",   (80, 120)),
    ("concrete",     (120, 220)),
    ("masonry",      (220, 280)),
    ("steel",        (280, 380)),
    ("pipes",        (380, 460)),
    ("tiles_glass",  (460, 540)),
    ("paint_polymer",(540, 620)),
    ("misc_low",     (620, 760)),
    ("misc_high",    (760, 929)),
]


def stratified_sample(standards: list[dict], n: int, seed: int = 42) -> list[dict]:
    rng = random.Random(seed)
    bucket_to_stds: dict[str, list[dict]] = {name: [] for name, _ in CATEGORY_ANCHORS}
    for s in standards:
        ps = s.get("page_start", 0)
        for name, (lo, hi) in CATEGORY_ANCHORS:
            if lo <= ps < hi:
                bucket_to_stds[name].append(s)
                break

    per_bucket = max(1, n // len(CATEGORY_ANCHORS))
    chosen: list[dict] = []
    for _, items in bucket_to_stds.items():
        if not items:
            continue
        sample = rng.sample(items, k=min(per_bucket, len(items)))
        chosen.extend(sample)

    # Top up if buckets were under-filled
    rng.shuffle(chosen)
    if len(chosen) < n:
        leftover = [s for s in standards if s not in chosen]
        rng.shuffle(leftover)
        chosen.extend(leftover[: n - len(chosen)])
    return chosen[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--standards", type=Path, default=Path("data/parsed_standards.json"))
    ap.add_argument("--out", type=Path, default=Path("data/bootstrap_test_set.json"))
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    with args.standards.open(encoding="utf-8") as f:
        standards = json.load(f)
    print(f"Loaded {len(standards)} standards")

    sampled = stratified_sample(standards, args.n, seed=args.seed)
    print(f"Sampled {len(sampled)} standards across {len(CATEGORY_ANCHORS)} buckets")

    client = GeminiClient()
    test_items: list[dict] = []
    # Free-tier on gemini-2.0-flash: ~15 RPM. Sleeping 4.2 s between requests
    # keeps us at ~14 RPM with safety margin and avoids 429s.
    THROTTLE_SECONDS = 4.5
    last_call = 0.0
    consecutive_errors = 0
    for i, s in enumerate(tqdm(sampled, desc="Generating queries")):
        # Throttle
        now = time.time()
        delta = now - last_call
        if delta < THROTTLE_SECONDS:
            time.sleep(THROTTLE_SECONDS - delta)
        last_call = time.time()

        q = client.generate_eval_query(s)
        if not q:
            consecutive_errors += 1
            # Exponential back-off if rate-limit cascade
            if consecutive_errors >= 3:
                wait = min(60, 5 * (2 ** (consecutive_errors - 3)))
                tqdm.write(f"  cooling off {wait}s after {consecutive_errors} consecutive failures")
                time.sleep(wait)
            continue
        consecutive_errors = 0
        # Reject if Gemini accidentally leaked the IS code
        if re.search(r"IS\s*\d{2,5}", q):
            continue
        test_items.append({
            "id": f"BS-{len(test_items) + 1:03d}",
            "query": q,
            "expected_standards": [s["is_code"]],
        })

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        json.dump(test_items, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(test_items)} eval items -> {args.out}")


if __name__ == "__main__":
    main()
