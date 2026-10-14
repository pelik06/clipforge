import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional

ANALYSIS_VERSION = "p3.1"


class FeatureCacheManager:
    """Manages persistent disk caching of expensive audio, visual, transcription, and quality features."""

    def __init__(self, cache_dir: str = "data/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.version = ANALYSIS_VERSION

    def compute_source_hash(self, source_str: str) -> str:
        """Derive consistent hash for local file or remote URL."""
        p = Path(source_str)
        if p.exists() and p.is_file():
            stat = p.stat()
            raw = f"{p.name}:{stat.st_size}:{stat.st_mtime}"
        else:
            raw = str(source_str).strip()
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def _build_cache_path(self, source_hash: str, feature_name: str, version: Optional[str] = None) -> Path:
        ver = version or self.version
        filename = f"{source_hash}_{feature_name}_{ver}.json"
        return self.cache_dir / filename

    def get(self, source_str: str, feature_name: str, version: Optional[str] = None) -> Optional[Any]:
        """Retrieve cached analysis artifact if valid."""
        src_hash = self.compute_source_hash(source_str)
        cache_file = self._build_cache_path(src_hash, feature_name, version=version)
        if not cache_file.exists():
            return None
        try:
            payload = json.loads(cache_file.read_text(encoding="utf-8"))
            if payload.get("version") != (version or self.version):
                return None
            return payload.get("data")
        except Exception:
            return None

    def set(self, source_str: str, feature_name: str, data: Any, version: Optional[str] = None):
        """Persist analysis artifact to cache."""
        src_hash = self.compute_source_hash(source_str)
        cache_file = self._build_cache_path(src_hash, feature_name, version=version)
        payload = {
            "source_hash": src_hash,
            "feature": feature_name,
            "version": version or self.version,
            "data": data,
        }
        cache_file.write_text(json.dumps(payload, default=str), encoding="utf-8")

    def has(self, source_str: str, feature_name: str, version: Optional[str] = None) -> bool:
        """Check if cache hit exists for source and feature."""
        return self.get(source_str, feature_name, version=version) is not None

    def invalidate(self, source_str: str, feature_name: Optional[str] = None):
        """Invalidate cached entries for given source and feature."""
        src_hash = self.compute_source_hash(source_str)
        pattern = f"{src_hash}_{feature_name or '*'}_*.json"
        for f in self.cache_dir.glob(pattern):
            try:
                f.unlink()
            except Exception:
                pass

    def clear(self):
        """Wipe all cached feature files."""
        for f in self.cache_dir.glob("*.json"):
            try:
                f.unlink()
            except Exception:
                pass
