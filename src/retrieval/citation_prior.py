"""Citation-count prior — uses the cross-reference graph as a proxy for how
'canonical' a standard is within SP 21.

Intuition: when several near-titled standards exist (IS 2209 'MORTICE LOCKS
(VERTICAL TYPE)' vs IS 7540 'MORTICE DEAD LOCKS' vs IS 8760 ...), the one
that other SP 21 standards CITE more is usually the more general / primary
reference. Tagging the most-cited entry with a small score boost helps the
reranker pick it on ambiguous queries.

The boost is logarithmic in citation count and capped — never large enough
to override a strong rerank decision.
"""
from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path


class CitationPrior:
    def __init__(self, xrefs_path: Path = Path("data/xrefs.json")):
        self.in_degree: dict[str, int] = defaultdict(int)
        if xrefs_path.exists():
            xrefs = json.loads(xrefs_path.read_text(encoding="utf-8"))
            for src, related in xrefs.items():
                for r in related:
                    self.in_degree[r] += 1

    def boost(self, is_code: str, max_boost: float = 0.025) -> float:
        """Return a TINY log-scaled additive boost. Designed to break ties
        between near-equal reranks, never to override the cross-encoder.

        - 0 citations  -> 0
        - 1 citation   -> ~0.008
        - 5 citations  -> ~0.018
        - 10 citations -> ~0.025 (capped)
        """
        n = self.in_degree.get(is_code, 0)
        if n <= 0:
            return 0.0
        raw = math.log(1 + n) * 0.011
        return min(raw, max_boost)
