import pytest
from services.cache.manager import ANALYSIS_VERSION, FeatureCacheManager


def test_p3_cache_version(tmp_path):
    cache = FeatureCacheManager(cache_dir=str(tmp_path))
    # Version must be bumped to p3.1
    assert cache.version == "p3.1"
    assert ANALYSIS_VERSION == "p3.1"

    # Verify invalidation on version mismatch
    source_url = "https://youtube.com/watch?v=version_test"
    cache.set(source_url, "context", {"completeness": 0.95}, version="p2.1")
    # Querying with p3.1 should return None (invalidated)
    assert cache.get(source_url, "context") is None
