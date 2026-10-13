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
    min_clip_seconds: int = int(os.getenv("CLIPFORGE_MIN_CLIP_SECONDS", "15"))
    max_clip_seconds: int = int(os.getenv("CLIPFORGE_MAX_CLIP_SECONDS", "90"))
