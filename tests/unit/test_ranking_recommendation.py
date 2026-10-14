import pytest
from services.clip_quality.models import ClipQualityFeatures, QualityBreakdown
from services.clip_quality.ranking import ClipRanker
from services.recommendation.engine import RecommendationEngine


def test_score_order():
    ranker = ClipRanker()

    clips = [
        {"id": "c1", "title": "Clip 1", "score": "75/100", "score_raw": 75.0, "start_time": 0.0, "end_time": 20.0, "text": "Thought A"},
        {"id": "c2", "title": "Clip 2", "score": "92/100", "score_raw": 92.0, "start_time": 40.0, "end_time": 60.0, "text": "Thought B"},
        {"id": "c3", "title": "Clip 3", "score": "84/100", "score_raw": 84.0, "start_time": 80.0, "end_time": 100.0, "text": "Thought C"},
    ]

    ranked = ranker.rank_clips(clips)
    assert ranked[0]["id"] == "c2"
    assert ranked[0]["rank"] == 1
    assert ranked[1]["id"] == "c3"
    assert ranked[1]["rank"] == 2
    assert ranked[2]["id"] == "c1"
    assert ranked[2]["rank"] == 3


def test_duplicate_penalty():
    ranker = ClipRanker(temporal_overlap_threshold=0.35)

    # c1 and c2 heavily overlap (0-30s vs 5-35s)
    clips = [
        {"id": "c1", "title": "Clip 1", "score_raw": 90.0, "start_time": 0.0, "end_time": 30.0, "text": "Thought A"},
        {"id": "c2", "title": "Clip 2", "score_raw": 88.0, "start_time": 5.0, "end_time": 35.0, "text": "Thought A variant"},
    ]

    ranked = ranker.rank_clips(clips)
    # c2 should receive heavy overlap penalty
    assert ranked[0]["id"] == "c1"
    assert ranked[1]["score_value"] < 60.0


def test_diversity():
    ranker = ClipRanker(diversity_opening_penalty=10.0)

    # Both clips have identical 4-word opening
    clips = [
        {"id": "c1", "title": "Clip 1", "score_raw": 85.0, "start_time": 0.0, "end_time": 20.0, "text": "Ini adalah rahasia terbesar kita"},
        {"id": "c2", "title": "Clip 2", "score_raw": 83.0, "start_time": 50.0, "end_time": 70.0, "text": "Ini adalah rahasia terbesar kamu"},
    ]

    ranked = ranker.rank_clips(clips)
    assert ranked[0]["id"] == "c1"
    # c2 receives opening diversity penalty
    assert ranked[1]["score_value"] <= 73.0


def test_recommendation_top_k():
    engine = RecommendationEngine(default_top_k=2, min_score_threshold=70.0)

    clips = [
        {"id": "c1", "title": "Clip 1", "score_raw": 95.0, "start_time": 0.0, "end_time": 20.0, "text": "Thought A"},
        {"id": "c2", "title": "Clip 2", "score_raw": 88.0, "start_time": 30.0, "end_time": 50.0, "text": "Thought B"},
        {"id": "c3", "title": "Clip 3", "score_raw": 82.0, "start_time": 60.0, "end_time": 80.0, "text": "Thought C"},
        {"id": "c4", "title": "Clip 4", "score_raw": 45.0, "start_time": 90.0, "end_time": 110.0, "text": "Thought D"},
    ]

    recs = engine.recommend_clips(clips)
    assert recs[0]["is_recommended"] is True
    assert recs[1]["is_recommended"] is True
    # c3 is above threshold but deferred by Top-2 limit
    assert recs[2]["is_recommended"] is False
    # c4 is below threshold
    assert recs[3]["is_recommended"] is False
