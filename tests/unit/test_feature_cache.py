import pytest
from services.cache.invalidation import IncrementalDependencyTracker
from services.cache.manager import FeatureCacheManager


def test_cache_hit_and_miss(tmp_path):
    cache = FeatureCacheManager(cache_dir=str(tmp_path))

    source_url = "https://youtube.com/watch?v=sample123"

    # Miss
    assert cache.get(source_url, "transcript") is None
    assert cache.has(source_url, "transcript") is False

    # Set
    cache.set(source_url, "transcript", {"segments": ["Halo dunia"]})

    # Hit
    assert cache.has(source_url, "transcript") is True
    res = cache.get(source_url, "transcript")
    assert res == {"segments": ["Halo dunia"]}


def test_cache_version_invalidation(tmp_path):
    cache = FeatureCacheManager(cache_dir=str(tmp_path))
    source_url = "https://youtube.com/watch?v=sample123"

    cache.set(source_url, "face_tracks", {"tracks": [1, 2]}, version="p2.0")

    # Invalidate when asking for current version ("p2.1")
    assert cache.get(source_url, "face_tracks", version="p2.1") is None


def test_incremental_dependency():
    tracker = IncrementalDependencyTracker()

    # Changing caption preset only invalidates captions and renders
    inv1 = tracker.get_invalidated_artifacts(["caption_preset"])
    assert "captions" in inv1
    assert "renders" in inv1
    assert "transcript" not in inv1

    # Changing asr invalidates transcript, captions, semantic, renders
    inv2 = tracker.get_invalidated_artifacts(["asr"])
    assert "transcript" in inv2
    assert "semantic_score" in inv2
    assert "renders" in inv2
