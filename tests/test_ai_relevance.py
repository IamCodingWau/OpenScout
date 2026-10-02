import pytest
from app.ai.relevance import clean_and_parse_json, simulated_open_weight_fallback, RelevanceEngine

def test_clean_and_parse_json_valid():
    raw = """```json
    {
      "relevance_score": 0.92,
      "matched_interests": ["DevOps", "Kubernetes"],
      "reason": "Direct match with Kubernetes architecture workshop.",
      "should_notify": true
    }
    ```"""
    parsed = clean_and_parse_json(raw)
    assert parsed["relevance_score"] == 0.92
    assert parsed["matched_interests"] == ["DevOps", "Kubernetes"]
    assert parsed["should_notify"] is True
    assert "Kubernetes" in parsed["reason"]

def test_clean_and_parse_json_clamping():
    raw = '{"relevance_score": 1.5, "matched_interests": [], "reason": "Over max", "should_notify": false}'
    parsed = clean_and_parse_json(raw)
    assert parsed["relevance_score"] == 1.0

def test_simulated_open_weight_fallback_match():
    interests = ["DevOps", "Kubernetes", "Cloud"]
    locations = ["Pune", "Online"]
    res = simulated_open_weight_fallback(
        interests=interests,
        locations=locations,
        title="Kubernetes and DevOps Pune Meetup",
        description="Production Kubernetes clusters in AWS Cloud",
        topics=["DevOps", "Kubernetes"],
        event_location="Pune, India",
        is_online=False,
        threshold=0.80
    )
    assert res["relevance_score"] >= 0.80
    assert "Kubernetes" in res["matched_interests"]
    assert res["should_notify"] is True
    assert "Pune" in res["reason"]

def test_simulated_open_weight_fallback_non_match():
    interests = ["DevOps", "Kubernetes"]
    locations = ["Pune"]
    res = simulated_open_weight_fallback(
        interests=interests,
        locations=locations,
        title="Knitting and Gardening Circle",
        description="Learn how to knit wool socks",
        topics=["Crafts"],
        event_location="Bengaluru",
        is_online=False,
        threshold=0.80
    )
    assert res["relevance_score"] < 0.50
    assert len(res["matched_interests"]) == 0
    assert res["should_notify"] is False