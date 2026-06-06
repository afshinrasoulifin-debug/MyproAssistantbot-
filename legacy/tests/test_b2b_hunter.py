
from __future__ import annotations
"""
tests/test_b2b_hunter.py — B2B Hunter Engine Tests
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest

@pytest.fixture
def hunter():
    from utils.b2b_hunter_engine import B2BHunterEngine
    return B2BHunterEngine(max_results_per_query=10, cooldown_hours=0.001)

@pytest.fixture
def sample_category():
    return {"id": "hotels", "name_en": "Boutique Hotels", "search_terms": ["boutique hotel", "design hotel"]}

class TestQueryBuilding:
    def test_builds_queries(self, hunter, sample_category):
        queries = hunter._build_queries("Helsinki, Finland", sample_category)
        assert len(queries) > 0
        assert all("query" in q for q in queries)

    def test_includes_region(self, hunter, sample_category):
        queries = hunter._build_queries("Stockholm, Sweden", sample_category)
        assert any("Stockholm" in q["query"] for q in queries)

    def test_multiple_types(self, hunter, sample_category):
        queries = hunter._build_queries("Helsinki, Finland", sample_category)
        types = set(q["type"] for q in queries)
        assert len(types) > 1

class TestExtraction:
    def test_extract_from_dict(self, hunter):
        result = {"title": "Hotel Kämp Helsinki", "url": "https://hotelkamp.com", "snippet": "Contact +358 9 576111"}
        query = {"query": "hotel Helsinki", "type": "general", "term": "hotel"}
        prospect = hunter._extract_business_from_result(result, query)
        assert prospect is not None
        assert "Hotel" in prospect.business_name

    def test_extracts_email(self, hunter):
        result = {"title": "Gallery Nord", "url": "https://gallerynord.fi", "snippet": "Contact: info@gallerynord.fi"}
        query = {"query": "gallery Helsinki", "type": "general", "term": "gallery"}
        prospect = hunter._extract_business_from_result(result, query)
        assert prospect is not None
        assert prospect.email == "info@gallerynord.fi"

    def test_skips_wikipedia(self, hunter):
        result = {"title": "Hotels - Wikipedia", "url": "https://en.wikipedia.org/wiki/Hotels", "snippet": "Hotels are..."}
        query = {"query": "hotel", "type": "general", "term": "hotel"}
        assert hunter._extract_business_from_result(result, query) is None

    def test_empty_title(self, hunter):
        result = {"title": "", "url": "https://x.com", "snippet": "text"}
        query = {"query": "test", "type": "general", "term": "test"}
        assert hunter._extract_business_from_result(result, query) is None

class TestCleanName:
    def test_removes_booking(self, hunter):
        assert "Hotel ABC" == hunter._clean_business_name("Hotel ABC - Booking.com reviews")

    def test_removes_tripadvisor(self, hunter):
        cleaned = hunter._clean_business_name("Hotel XYZ | TripAdvisor")
        assert "TripAdvisor" not in cleaned

class TestDeduplication:
    def test_removes_duplicates(self, hunter):
        from utils.b2b_hunter_engine import RawProspect
        prospects = [
            RawProspect(business_name="Hotel ABC", website="https://hotelabc.com"),
            RawProspect(business_name="Hotel ABC", website="https://hotelabc.com"),
            RawProspect(business_name="Hotel XYZ", website="https://hotelxyz.com"),
        ]
        unique = hunter._deduplicate(prospects)
        assert len(unique) == 2

    def test_keeps_different(self, hunter):
        from utils.b2b_hunter_engine import RawProspect
        prospects = [
            RawProspect(business_name="Hotel A", website="https://a.com"),
            RawProspect(business_name="Hotel B", website="https://b.com"),
        ]
        assert len(hunter._deduplicate(prospects)) == 2

class TestStats:
    def test_get_stats(self, hunter):
        stats = hunter.get_stats()
        assert isinstance(stats, dict)
        assert "max_results_per_query" in stats

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


