"""Cross-reference graph: extract IS-code mentions from each standard's body.

Many SP 21 standards cite each other ("see IS 4031 for testing methods", "as
laid down in IS 269:1989"). We parse those mentions, normalise them, and
build an undirected graph: standard → list of related standards.

This powers the "Related standards" section in the UI without any LLM call.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

# Match IS codes that appear inside body text. We accept several shapes:
#   IS 269:1989, IS 269: 1989, IS 4031 (Part 1), IS 4031 (Part 1) : 1996, IS 269.
# But we deliberately skip codes like "IS 269" without a year — too vague and
# usually points to a family of revisions.
IS_INLINE_RE = re.compile(
    r"\bIS\s+(\d{2,5})(?:\s*\(\s*Part\s*[IVX0-9]+\s*\))?\s*:\s*(\d{4})",
    re.IGNORECASE,
)


def extract_xrefs(standards: list[dict]) -> dict[str, list[str]]:
    """Return a map {is_code: [related_is_code, ...]} sorted by frequency."""
    norm_to_canonical: dict[str, str] = {s["is_code_norm"]: s["is_code"] for s in standards}

    raw_xrefs: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for s in standards:
        own_norm = s["is_code_norm"]
        text = (s.get("full_text") or "")
        # Reconstruct canonicalised IS codes from inline mentions
        for m in IS_INLINE_RE.finditer(text):
            num = m.group(1)
            year = m.group(2)
            # Detect (Part X) inside the matched span
            part_match = re.search(r"\(Part\s*([IVX0-9]+)\)", m.group(0), re.IGNORECASE)
            if part_match:
                inferred = f"IS {num} (Part {part_match.group(1).upper()}): {year}"
            else:
                inferred = f"IS {num}: {year}"
            inferred_norm = re.sub(r"\s+", "", inferred).lower()
            if inferred_norm == own_norm:
                continue  # self-reference, skip
            if inferred_norm not in norm_to_canonical:
                continue  # references a standard outside SP 21 (e.g. IS 4031)
            raw_xrefs[own_norm][inferred_norm] += 1

    out: dict[str, list[str]] = {}
    for own_norm, related_counts in raw_xrefs.items():
        canonical = norm_to_canonical[own_norm]
        related_codes = [
            norm_to_canonical[r] for r, _ in sorted(
                related_counts.items(), key=lambda kv: kv[1], reverse=True
            )
        ]
        out[canonical] = related_codes
    return out


def main():
    standards_path = Path("data/parsed_standards.json")
    out_path = Path("data/xrefs.json")
    with standards_path.open(encoding="utf-8") as f:
        standards = json.load(f)
    xrefs = extract_xrefs(standards)
    n_pairs = sum(len(v) for v in xrefs.values())
    print(f"Extracted {n_pairs} cross-reference edges across {len(xrefs)} standards.")
    # Top-5 most cited
    citation_counts: dict[str, int] = defaultdict(int)
    for related in xrefs.values():
        for r in related:
            citation_counts[r] += 1
    top = sorted(citation_counts.items(), key=lambda kv: kv[1], reverse=True)[:5]
    print("Most-cited standards in SP 21:")
    for code, n in top:
        print(f"  {n:3d}  {code}")
    out_path.write_text(json.dumps(xrefs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
