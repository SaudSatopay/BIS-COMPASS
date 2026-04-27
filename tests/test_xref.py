"""Unit tests for cross-reference extraction."""
from src.ingestion.xref import extract_xrefs, IS_INLINE_RE


def _std(code: str, code_norm: str, body: str) -> dict:
    return {
        "is_code": code,
        "is_code_norm": code_norm,
        "title": "TEST",
        "scope": "",
        "revision": None,
        "page_start": 1,
        "page_end": 1,
        "full_text": body,
    }


class TestExtractXrefs:
    def test_basic_reference(self):
        standards = [
            _std("IS 269: 1989", "is269:1989", "Refer to IS 4031:1988 for testing."),
            _std("IS 4031: 1988", "is4031:1988", "Methods of physical tests."),
        ]
        xrefs = extract_xrefs(standards)
        assert "IS 269: 1989" in xrefs
        assert "IS 4031: 1988" in xrefs["IS 269: 1989"]

    def test_self_reference_skipped(self):
        standards = [
            _std("IS 269: 1989", "is269:1989", "See IS 269:1989 itself."),
        ]
        xrefs = extract_xrefs(standards)
        assert "IS 269: 1989" not in xrefs  # only self-ref → no edges → not in dict

    def test_external_reference_skipped(self):
        # IS 9999:2099 is NOT in our corpus, so the edge should be dropped.
        standards = [
            _std("IS 269: 1989", "is269:1989", "See IS 9999:2099 for guidance."),
        ]
        xrefs = extract_xrefs(standards)
        assert "IS 269: 1989" not in xrefs

    def test_part_reference(self):
        standards = [
            _std("IS 269: 1989", "is269:1989", "Refer to IS 4031 (Part 1):1988."),
            _std("IS 4031 (Part 1): 1988", "is4031(part1):1988", "Test methods."),
        ]
        xrefs = extract_xrefs(standards)
        assert "IS 4031 (Part 1): 1988" in xrefs["IS 269: 1989"]


class TestInlineRegex:
    def test_matches_with_year(self):
        assert IS_INLINE_RE.search("Refer to IS 269:1989 for details.")

    def test_matches_with_part(self):
        assert IS_INLINE_RE.search("As per IS 2185 (Part 2): 1983.")

    def test_does_not_match_without_year(self):
        # Bare "IS 269" without ":YYYY" is too vague — we skip it.
        assert IS_INLINE_RE.search("see IS 269 for cement") is None
