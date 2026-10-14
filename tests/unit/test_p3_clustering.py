import pytest
from services.clustering import SemanticSimilarityProvider, TopicClusterer


def test_topic_family():
    clusterer = TopicClusterer(similarity_threshold=0.25)
    clips = [
        {"id": "c1", "title": "Investasi saham untuk pemula", "text": "Cara memulai investasi saham dan reksadana"},
        {"id": "c2", "title": "Saham dividen terbaik", "text": "Memilih saham dividen untuk investasi jangka panjang"},
        {"id": "c3", "title": "Resep memasak rendang daging", "text": "Bumbu rahasia memasak rendang daging sapi empuk"},
    ]
    families = clusterer.cluster_clips(clips)
    # c1 and c2 should cluster into the same family (saham/investasi)
    assert len(families) == 2
    f_saham = next(f for f in families if "c1" in f.members)
    assert "c2" in f_saham.members
    assert "c3" not in f_saham.members


def test_family_diversity():
    clusterer = TopicClusterer()
    # 4 clips from family_01, 1 from family_02
    clips = [
        {"id": "c1", "topic_family": "family_01", "score_value": 90.0},
        {"id": "c2", "topic_family": "family_01", "score_value": 88.0},
        {"id": "c3", "topic_family": "family_01", "score_value": 85.0},
        {"id": "c4", "topic_family": "family_01", "score_value": 82.0},
        {"id": "c5", "topic_family": "family_02", "score_value": 80.0},
    ]
    diversified = clusterer.enforce_family_diversity(clips, max_per_family=2)
    # Top 3 should be [c1, c2, c5] rather than 4 clips of family_01 in a row!
    assert diversified[0]["id"] == "c1"
    assert diversified[1]["id"] == "c2"
    assert diversified[2]["id"] == "c5"


def test_semantic_duplicate():
    provider = SemanticSimilarityProvider(mode="none")
    sim_high = provider.compute_similarity("Tips investasi saham dividen", "Cara investasi saham dan dividen")
    sim_low = provider.compute_similarity("Tips investasi saham dividen", "Tutorial servis mesin motor matic")
    assert sim_high > 0.40
    assert sim_low < 0.10
