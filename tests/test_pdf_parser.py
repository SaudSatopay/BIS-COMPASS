"""Unit tests for the SP 21 PDF parser.

These tests exercise pure-Python helpers that don't need the actual PDF —
parser correctness on the real PDF is verified by the sanity-check section
in `src.ingestion.pdf_parser.main` which prints OK/MISS for all 10 expected
codes from the public test set.
"""
from src.ingestion.pdf_parser import (
    canonicalize_is_code,
    normalize_is_code,
    _extract_scope,
)


class TestCanonicalize:
    def test_no_part(self):
        assert canonicalize_is_code(None, "269", "1989") == "IS 269: 1989"

    def test_with_part(self):
        assert canonicalize_is_code("(Part 2)", "2185", "1983") == "IS 2185 (Part 2): 1983"

    def test_uppercase_part_normalised_to_titlecase(self):
        # Source PDF sometimes has '(PART 2)' — we canonicalise to '(Part 2)'
        assert canonicalize_is_code("(PART 2)", "2185", "1983") == "IS 2185 (Part 2): 1983"

    def test_extra_whitespace_collapsed(self):
        assert canonicalize_is_code("(Part   2)", "2185", "1983") == "IS 2185 (Part 2): 1983"


class TestNormalize:
    def test_strips_whitespace_and_lowercases(self):
        assert normalize_is_code("IS 269: 1989") == "is269:1989"

    def test_part_handled(self):
        assert normalize_is_code("IS 2185 (Part 2): 1983") == "is2185(part2):1983"

    def test_already_normalised_is_idempotent(self):
        assert normalize_is_code(normalize_is_code("IS 269: 1989")) == "is269:1989"


class TestScopeExtraction:
    def test_scope_extracted_until_next_section(self):
        text = (
            "1.14\nSP 21 : 2005\n"
            "1. Scope — Requirements for masonry cement to be used for all general purposes.\n"
            "SUMMARY OF\nIS 3466 : 1988  MASONRY CEMENT\n"
            "(Second Revision)\n"
            "2. Physical Requirements — See TABLE 1.\n"
        )
        scope = _extract_scope(text)
        assert "Requirements for masonry cement" in scope
        # Should NOT spill into the next numbered section
        assert "Physical Requirements" not in scope

    def test_no_scope_returns_empty(self):
        assert _extract_scope("just some random text") == ""

    def test_handles_uppercase_scope_marker(self):
        text = "1. SCOPE — Covers fasteners.\n2. Requirements.\n"
        scope = _extract_scope(text)
        assert "Covers fasteners" in scope
