from dataclasses import dataclass
from pathlib import Path
import os
import shutil

KNOWN_FFMPEG_PATHS = [
    Path.home() / "AppData/Local/hermes/tools/ffmpeg-9.0.1-win32-x64/bin",
    Path.home() / "AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.2-full_build-shared/bin",
]

def find_binary(name: str) -> str:
    """Find binary from env, PATH, or known local tool directories."""
    env_val = os.getenv(f"CLIPFORGE_{name.upper()}_BIN")
    if env_val and Path(env_val).exists():
        return env_val

    found = shutil.which(name)
    if found:
        return found

    for candidate_dir in KNOWN_FFMPEG_PATHS:
        binary_file = candidate_dir / f"{name}.exe"
        if binary_file.exists():
            # Add to PATH so submodules and child processes can find it
            if str(candidate_dir) not in os.environ.get("PATH", ""):
                os.environ["PATH"] = f"{candidate_dir};" + os.environ.get("PATH", "")
            return str(binary_file)

    return name


@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv("CLIPFORGE_ENV", "development")
    data_dir: str = os.getenv("CLIPFORGE_DATA_DIR", "./data")
    ffmpeg_bin: str = find_binary("ffmpeg")
    ffprobe_bin: str = find_binary("ffprobe")
    max_candidates: int = int(os.getenv("CLIPFORGE_MAX_CANDIDATES", "20"))
    min_clips: int = int(os.getenv("CLIPFORGE_MIN_CLIPS", "1"))
    max_clips: int = int(os.getenv("CLIPFORGE_MAX_CLIPS", "3"))
    min_clip_seconds: int = int(os.getenv("CLIPFORGE_MIN_CLIP_SECONDS", "30"))
    max_clip_seconds: int = int(os.getenv("CLIPFORGE_MAX_CLIP_SECONDS", "120"))
    min_clip_duration: float = float(os.getenv("CLIPFORGE_MIN_CLIP_DURATION", "30.0"))
    max_clip_duration: float = float(os.getenv("CLIPFORGE_MAX_CLIP_DURATION", "120.0"))
    max_temporal_overlap: float = float(os.getenv("CLIPFORGE_MAX_TEMPORAL_OVERLAP", "0.35"))
    caption_words_per_group: int = int(os.getenv("CLIPFORGE_CAPTION_WORDS_PER_GROUP", "4"))
    scene_cut_snap: bool = os.getenv("CLIPFORGE_SCENE_CUT_SNAP", "true").lower() in ("true", "1")
    track_timeout: float = float(os.getenv("CLIPFORGE_TRACK_TIMEOUT", "1.5"))
    reframe_smoothing: float = float(os.getenv("CLIPFORGE_REFRAME_SMOOTHING", "0.55"))
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
