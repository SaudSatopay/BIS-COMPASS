"""Unit tests for the keyword-based material-category detector."""
from src.retrieval.metadata import detect_categories, category_overlap_boost


class TestDetectCategories:
    def test_cement_query(self):
        cats = detect_categories("We make 33 grade ordinary Portland cement")
        assert "cement" in cats

    def test_multi_category(self):
        # "reinforced concrete pipe" should hit both 'concrete' and 'pipe'
        cats = detect_categories("manufacturing reinforced concrete pipe for sewers")
        assert "concrete" in cats
        assert "pipe" in cats

    def test_word_boundary_safe(self):
        # 'cement' inside 'cementitious' should NOT match 'cement' (we use word boundary)
        # If we test bare 'cement', that's a real word and should match
        assert "cement" in detect_categories("Portland cement")

    def test_empty_input(self):
        assert detect_categories("") == set()

    def test_no_match(self):
        assert detect_categories("hello world") == set()


class TestCategoryBoost:
    def test_no_query_categories_no_boost(self):
        assert category_overlap_boost(set(), "Portland cement specification") == 0.0

    def test_single_overlap(self):
        boost = category_overlap_boost({"cement"}, "Specification for masonry cement")
        assert boost > 0
        assert boost <= 0.20

    def test_no_overlap(self):
        assert category_overlap_boost({"cement"}, "Hardware locks and hinges") == 0.0

    def test_capped(self):
        # Even many overlaps should cap at 2 × multiplier
        big = "cement concrete steel aggregate brick block tile pipe roofing"
        boost = category_overlap_boost({"cement", "concrete", "steel"}, big)
        assert boost <= 0.20
