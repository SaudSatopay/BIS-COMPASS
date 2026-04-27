"""Technical-phrase boost for retrieval.

The cross-encoder reranker tends to under-weight rare technical tokens that
sit on word boundaries (M30, 33 grade, OPC, mortice ...). This module
extracts those tokens from the query and gives a small additive bonus to
candidates whose title/scope mentions them verbatim.

Multiplicative boost is intentionally small (~0.05 per matched phrase, capped
at +0.20 total) so it CAN break ties between near-equal-quality reranks but
CANNOT promote a clearly worse candidate.
"""
from __future__ import annotations

import re

# Per-pattern weights are intentionally tiny. The phrase boost is meant to
# nudge near-tie reranks, not override the cross-encoder. We focus on
# (a) Part qualifiers — high-precision, usually disambiguating
# (b) cement-grade qualifiers — very specific tokens
# (c) a couple of high-signal nouns that we observed the reranker missing
# Each capped at +0.04 cumulative.
BOOST_PATTERNS: list[tuple[str, float]] = [
    # IS Part qualifiers ("Part 2") — when query says "Part 2", we strongly
    # prefer that exact part.
    (r"\bPart\s*[IVX0-9]+\b", 0.04),
    # Cement-grade qualifiers: 33 grade, 43 grade, 53 grade.
    (r"\b\d{2,3}\s*grade\b", 0.03),
    # M-grade fasteners. Lower weight because it can fire spuriously on
    # non-fastener mentions (e.g. M3 used as a section number).
    (r"\bM\d{2,3}\b", 0.02),
    # High-signal nouns that the dense embedder under-weights.
    (r"\bmortice\b", 0.02),
    (r"\bsupersulphated\b", 0.03),
    (r"\bhydrophobic\b", 0.03),
    (r"\bcorrugated\b", 0.02),
]

_COMPILED = [(re.compile(p, re.IGNORECASE), w) for p, w in BOOST_PATTERNS]


def extract_phrases(text: str) -> list[tuple[str, float]]:
    """Find all phrase patterns that fire on `text`. Returns list of
    (matched_substring, weight) — there can be multiple matches per pattern.
    """
    if not text:
        return []
    out: list[tuple[str, float]] = []
    for pat, w in _COMPILED:
        for m in pat.finditer(text):
            out.append((m.group(0), w))
    return out


def phrase_boost(query: str, passage: str, max_boost: float = 0.04) -> float:
    """Return additive boost for `passage` based on technical-phrase overlap.

    A boost is awarded ONLY when the same phrase pattern fires on both the
    query and the passage (case-insensitive, word-bounded). This prevents
    rewarding candidates that just happen to mention 'M30' when the user
    didn't ask about M30.
    """
    q_phrases = extract_phrases(query)
    if not q_phrases:
        return 0.0
    p_phrases = extract_phrases(passage)
    if not p_phrases:
        return 0.0
    p_lower = {ph.lower() for ph, _ in p_phrases}
    bonus = 0.0
    seen: set[tuple[str, float]] = set()
    for ph, w in q_phrases:
        key = (ph.lower(), w)
        if key in seen:
            continue
        seen.add(key)
        if ph.lower() in p_lower:
            bonus += w
    return min(bonus, max_boost)
