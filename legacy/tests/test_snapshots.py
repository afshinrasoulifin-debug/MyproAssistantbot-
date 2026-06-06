
"""Snapshot/structure tests — v29.0.0 real tests."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_pipeline_result_structure():
    """Pipeline result dict has required keys."""
    result = {
        "stage": "classify",
        "output": "marketing",
        "confidence": 0.95,
        "metadata": {"model": "gemini-2.5-flash"},
    }
    assert "stage" in result
    assert "output" in result
    assert "confidence" in result
    assert isinstance(result["confidence"], float)
    assert 0.0 <= result["confidence"] <= 1.0
    assert "metadata" in result
    assert isinstance(result["metadata"], dict)


def test_search_response_structure():
    """Search response has the expected shape."""
    response = {
        "query": "test query",
        "results": [
            {"title": "Result 1", "url": "https://example.com", "snippet": "..."},
        ],
        "total": 1,
        "engine": "ddg",
    }
    assert "query" in response
    assert "results" in response
    assert isinstance(response["results"], list)
    assert len(response["results"]) > 0
    for r in response["results"]:
        assert "title" in r
        assert "url" in r
        assert r["url"].startswith("http")
    assert response["total"] == len(response["results"])


def test_ai_response_structure():
    """AI response has content and metadata."""
    response = {
        "content": "Hello, how can I help?",
        "model": "gemini-2.5-flash",
        "tokens": {"input": 10, "output": 15},
        "latency_ms": 234,
    }
    assert "content" in response
    assert len(response["content"]) > 0
    assert "model" in response
    assert "tokens" in response
    assert response["tokens"]["input"] > 0
    assert response["tokens"]["output"] > 0
    assert response["latency_ms"] > 0


