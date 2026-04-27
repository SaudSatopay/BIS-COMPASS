"""Parse SP 21 PDF into structured per-standard records.

The PDF is laid out so that each standard is bounded by a 'SUMMARY OF' header
followed by an IS code line. We scan the full text page-by-page, segment by
those headers, and extract metadata + body for each standard.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path

import fitz

IS_CODE_RE = re.compile(
    r"IS\s+(\d+)\s*(\(Part\s*[IVX0-9]+\))?\s*:\s*(\d{4})",
    re.IGNORECASE,
)
SUMMARY_HDR_RE = re.compile(r"SUMMARY\s+OF\s*\n\s*(IS\s+[^\n]+)", re.IGNORECASE)
REVISION_TAIL_RE = re.compile(r"\((First|Second|Third|Fourth|Fifth)\s+Revision\)\s*$", re.IGNORECASE)


@dataclass
class Standard:
    is_code: str           # canonical: "IS 3466: 1988" or "IS 2185 (Part 2): 1983"
    is_code_norm: str      # normalized: "is3466:1988" — matches eval_script normalization
    title: str             # e.g. "MASONRY CEMENT"
    revision: str | None   # e.g. "Second Revision" or None
    page_start: int        # 1-indexed
    page_end: int
    scope: str             # extracted "Scope" body if found
    full_text: str         # entire body text (post header)


def normalize_is_code(s: str) -> str:
    return re.sub(r"\s+", "", s).lower()


def canonicalize_is_code(part_num: str | None, number: str, year: str) -> str:
    """Canonical form mirrors the public_test_set.json style: 'IS 2185 (Part 2): 1983'."""
    if part_num:
        # Normalize whitespace and title-case the word 'Part'
        part_clean = re.sub(r"\s+", " ", part_num.strip())
        part_clean = re.sub(r"^\(\s*part\s*", "(Part ", part_clean, flags=re.IGNORECASE)
        return f"IS {number} {part_clean}: {year}"
    return f"IS {number}: {year}"


def extract_standards(pdf_path: Path) -> list[Standard]:
    """Walk every page, detect 'SUMMARY OF\\nIS ...' anchors, slice the doc accordingly."""
    doc = fitz.open(pdf_path)

    # Build a list of (page_idx, page_text). Append page markers so we can map back.
    pages_text: list[str] = []
    for page in doc:
        pages_text.append(page.get_text("text"))
    doc.close()

    # Find anchors per page
    anchors: list[tuple[int, str, str, str | None, str, str, str | None]] = []
    # (page_idx_0based, raw_header_line, is_number, part, year, title, revision)

    for page_idx, text in enumerate(pages_text):
        for m in SUMMARY_HDR_RE.finditer(text):
            header_line = m.group(1).strip()
            code_match = IS_CODE_RE.search(header_line)
            if not code_match:
                continue
            number = code_match.group(1)
            part = code_match.group(2)
            year = code_match.group(3)

            # Title = everything in header_line after the IS code.
            # The "(X Revision)" tag may appear inline OR on one of the next
            # 1–3 lines (some entries break the title onto multiple lines).
            after_code = header_line[code_match.end():].strip()
            tail_after_anchor = text[m.end():m.end() + 400]
            tail_lines = [ln.strip() for ln in tail_after_anchor.lstrip().split("\n") if ln.strip()]

            # If the title is empty after the IS-code line, take the next
            # non-empty line as the title (some standards put it there).
            if not after_code and tail_lines:
                after_code = tail_lines[0]
                tail_lines = tail_lines[1:]

            # Search for a revision marker in the title or in any of the next
            # ~3 short lines (gives multi-line titles a chance).
            revision = None
            rev_match = REVISION_TAIL_RE.search(after_code)
            if rev_match:
                revision = rev_match.group(0).strip("() ")
                after_code = REVISION_TAIL_RE.sub("", after_code).strip()
            else:
                _REV_LINE_RE = re.compile(
                    r"^\(?\s*(First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth)"
                    r"\s+Revision\s*\)?\s*$",
                    re.IGNORECASE,
                )
                for cand in tail_lines[:3]:
                    if _REV_LINE_RE.match(cand):
                        revision = re.sub(r"[()]", "", cand).strip()
                        break

            title = after_code.strip()

            anchors.append((page_idx, header_line, number, part, year, title, revision))

    # Build standards by slicing pages_text from anchor i to anchor i+1
    standards: list[Standard] = []
    for i, (page_idx, header_line, number, part, year, title, revision) in enumerate(anchors):
        start_page = page_idx
        end_page = (anchors[i + 1][0] - 1) if i + 1 < len(anchors) else len(pages_text) - 1
        # If the next anchor is on the same page, the standard ends on this page
        if i + 1 < len(anchors) and anchors[i + 1][0] == page_idx:
            end_page = page_idx

        body_chunks: list[str] = []
        for p in range(start_page, end_page + 1):
            body_chunks.append(pages_text[p])
        full_text = "\n".join(body_chunks).strip()

        # Extract Scope: text after "Scope" / "1. Scope" until next numbered heading
        scope = _extract_scope(full_text)

        canonical = canonicalize_is_code(part, number, year)
        standards.append(Standard(
            is_code=canonical,
            is_code_norm=normalize_is_code(canonical),
            title=title,
            revision=revision,
            page_start=start_page + 1,
            page_end=end_page + 1,
            scope=scope,
            full_text=full_text,
        ))
    return standards


# Note: NO re.IGNORECASE here — we rely on uppercase-letter classes acting as
# case-sensitive markers. The lookahead terminates on next numbered section
# (e.g. "2. ..."), an uppercase-only heading line, or "SUMMARY OF" (start of
# next standard).
_SCOPE_RE = re.compile(
    r"(?:^|\n)\s*1[\.\s]+(?:Scope|SCOPE)[\s\-\u2014\u2013:]*"
    r"([\s\S]+?)"
    r"(?=\n\s*(?:\d+\.\s|[A-Z][A-Z][A-Z]+\b|SUMMARY\s+OF))"
)


def _extract_scope(full_text: str) -> str:
    m = _SCOPE_RE.search(full_text)
    if not m:
        return ""
    scope = m.group(1).strip()
    scope = re.sub(r"\s+", " ", scope)
    return scope[:1500]


def main():
    pdf_path = Path("datasets/dataset.pdf")
    out_standards = Path("data/parsed_standards.json")
    out_whitelist = Path("data/is_code_whitelist.json")

    standards = extract_standards(pdf_path)
    print(f"Extracted {len(standards)} standards from {pdf_path}")

    # Save full structured output
    out_standards.parent.mkdir(parents=True, exist_ok=True)
    with out_standards.open("w", encoding="utf-8") as f:
        json.dump([asdict(s) for s in standards], f, ensure_ascii=False, indent=2)
    print(f"  -> {out_standards}")

    # Save whitelist (canonical + normalized) for hallucination guard
    whitelist = {
        "canonical": sorted({s.is_code for s in standards}),
        "normalized": sorted({s.is_code_norm for s in standards}),
    }
    with out_whitelist.open("w", encoding="utf-8") as f:
        json.dump(whitelist, f, ensure_ascii=False, indent=2)
    print(f"  -> {out_whitelist} ({len(whitelist['canonical'])} unique IS codes)")

    # Print a quick sanity check vs public test set expectations
    print("\nSanity check vs public_test_set.json expected_standards:")
    with open("datasets/public_test_set.json", encoding="utf-8") as f:
        pub = json.load(f)
    norm_set = set(whitelist["normalized"])
    miss = []
    for q in pub:
        for exp in q["expected_standards"]:
            n = normalize_is_code(exp)
            mark = "OK " if n in norm_set else "MISS"
            print(f"  {mark} {exp}")
            if n not in norm_set:
                miss.append(exp)
    if miss:
        print(f"\nMissing {len(miss)}/10 expected codes — investigate parser.")
    else:
        print("\nAll 10 expected codes present in whitelist.")


if __name__ == "__main__":
    main()
