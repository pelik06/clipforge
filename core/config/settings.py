from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv("CLIPFORGE_ENV", "development")
    data_dir: str = os.getenv("CLIPFORGE_DATA_DIR", "./data")
    ffmpeg_bin: str = os.getenv("CLIPFORGE_FFMPEG_BIN", "ffmpeg")
    ffprobe_bin: str = os.getenv("CLIPFORGE_FFPROBE_BIN", "ffprobe")
    max_candidates: int = int(os.getenv("CLIPFORGE_MAX_CANDIDATES", "20"))
    min_clip_seconds: int = int(os.getenv("CLIPFORGE_MIN_CLIP_SECONDS", "15"))
    max_clip_seconds: int = int(os.getenv("CLIPFORGE_MAX_CLIP_SECONDS", "90"))
