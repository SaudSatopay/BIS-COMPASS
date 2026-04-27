"""Lightweight, dependency-free material-category detector.

We do NOT use an LLM here — `inference.py` must run with zero network calls.
Instead we use a curated keyword map distilled from SP 21's section structure.

The detector returns a *set* of categories (not just one), because real MSE
queries often touch multiple materials (e.g. "reinforced concrete pipe" hits
both 'concrete' and 'pipe'). Categories then act as a *soft* score boost in
the retriever — never a hard filter, so we never drop the correct answer.
"""
from __future__ import annotations

import re

# Each category maps to verbatim tokens / phrases that strongly imply it.
# Order matters only insofar as we preserve insertion order in the result.
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "cement": [
        "cement", "opc", "ppc", "portland", "pozzolana", "slag cement",
        "supersulphated", "hydrophobic", "masonry cement",
    ],
    "concrete": [
        "concrete", "rcc", "reinforced concrete", "precast", "prestressed",
        "ferrocement", "lightweight concrete",
    ],
    "aggregate": [
        "aggregate", "sand", "gravel", "fine aggregate", "coarse aggregate",
        "stone dust",
    ],
    "steel": [
        "steel", "rebar", "tor steel", "tmt", "structural steel", "wire rod",
        "high tensile",
    ],
    "iron": [
        "cast iron", "wrought iron", "ductile iron", "iron casting", "iron pipe",
    ],
    "brick": [
        "brick", "burnt clay", "fly ash brick", "calcium silicate",
    ],
    "block": [
        "block", "masonry block", "concrete block", "aac", "lightweight block",
        "hollow block", "solid block",
    ],
    "tile": [
        "tile", "ceramic tile", "vitrified", "marble tile", "mosaic",
    ],
    "pipe": [
        "pipe", "tube", "conduit", "duct", "drain pipe", "sewer", "watermain",
    ],
    "roofing": [
        "roof", "roofing", "asbestos cement sheet", "corrugated", "cladding",
        "shingle",
    ],
    "glass": ["glass", "glazing", "tempered glass", "float glass"],
    "wood": ["wood", "timber", "plywood", "particle board", "block board"],
    "paint": [
        "paint", "varnish", "lacquer", "primer", "emulsion", "enamel", "coating",
    ],
    "polymer": [
        "polymer", "plastic", "pvc", "hdpe", "ldpe", "abs", "polyethylene",
        "polypropylene",
    ],
    "insulation": ["insulation", "thermal insulation", "vermiculite", "mineral wool"],
    "lock_hardware": [
        "lock", "mortice", "padlock", "hinge", "door fitting", "bolt", "screw",
        "nail", "fastener",
    ],
    "lime_gypsum": ["lime", "hydrated lime", "gypsum", "plaster of paris"],
    "asbestos": ["asbestos"],
}


def _build_re(keywords: list[str]) -> re.Pattern:
    # Word-boundary safe; case-insensitive.
    parts = [re.escape(k) for k in sorted(keywords, key=len, reverse=True)]
    return re.compile(r"(?<![A-Za-z])(?:" + "|".join(parts) + r")(?![A-Za-z])", re.IGNORECASE)


_PATTERNS: dict[str, re.Pattern] = {cat: _build_re(kws) for cat, kws in CATEGORY_KEYWORDS.items()}


def detect_categories(text: str) -> set[str]:
    """Return all categories that fire on the given text. Empty set if none match."""
    if not text:
        return set()
    return {cat for cat, pat in _PATTERNS.items() if pat.search(text)}


def category_overlap_boost(
    query_cats: set[str], passage_text: str, multiplier: float = 0.10
) -> float:
    """Return a small additive boost for documents whose text shares categories
    with the query. Capped at multiplier × 2 so it can't dominate the rerank
    score — this is a tiebreaker, not a re-ranker.
    """
    if not query_cats:
        return 0.0
    passage_cats = detect_categories(passage_text)
    overlap = query_cats & passage_cats
    if not overlap:
        return 0.0
    return min(multiplier * len(overlap), multiplier * 2)
