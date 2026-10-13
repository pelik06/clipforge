from pathlib import Path
import shutil
import subprocess
from typing import Optional, Dict, Any
from core.config.settings import Settings


def validate_source(path: str) -> Path:
    """Validate that local source file exists and is a file."""
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Source does not exist: {source}")
    if not source.is_file():
        raise ValueError(f"Source is not a file: {source}")
    return source


def check_media_dependencies() -> Dict[str, Any]:
    """Check availability of external media processing tools."""
    s = Settings()
    ffmpeg_path = s.ffmpeg_bin if Path(s.ffmpeg_bin).exists() else shutil.which("ffmpeg")
    ffprobe_path = s.ffprobe_bin if Path(s.ffprobe_bin).exists() else shutil.which("ffprobe")
    
    ytdlp_available = False
    try:
        import yt_dlp
        ytdlp_available = True
    except ImportError:
        pass
        
    return {
        "ffmpeg_available": ffmpeg_path is not None and (Path(ffmpeg_path).exists() or shutil.which(ffmpeg_path) is not None),
        "ffmpeg_path": str(ffmpeg_path) if ffmpeg_path else None,
        "ffprobe_available": ffprobe_path is not None and (Path(ffprobe_path).exists() or shutil.which(ffprobe_path) is not None),
        "ffprobe_path": str(ffprobe_path) if ffprobe_path else None,
        "ytdlp_available": ytdlp_available,
    }


def extract_youtube_metadata(url: str) -> Dict[str, Any]:
    """Extract real YouTube video metadata using yt-dlp without downloading full video.
    
    Falls back gracefully to structural parsed info if network or extractor fails.
    """
    clean_url = url.strip()
    try:
        import yt_dlp
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "skip_download": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(clean_url, download=False)
            if info:
                return {
                    "success": True,
                    "title": info.get("title") or "YouTube Stream",
                    "duration": info.get("duration"),
                    "uploader": info.get("uploader") or info.get("channel") or "Unknown Streamer",
                    "thumbnail": info.get("thumbnail"),
                    "view_count": info.get("view_count"),
                    "webpage_url": info.get("webpage_url") or clean_url,
                    "source": "yt-dlp",
                }
    except Exception:
        pass

    # Fallback when yt-dlp metadata extraction encounters network or parsing error
    return {
        "success": False,
        "title": f"YouTube Video ({clean_url[:35]}...)",
        "duration": None,
        "uploader": "Streamer / Creator",
        "thumbnail": None,
        "view_count": None,
        "webpage_url": clean_url,
        "source": "fallback",
    }


def download_youtube_segment(
    url: str,
    output_path: str,
    start_sec: float = 0.0,
    duration_sec: float = 15.0,
    max_filesize_mb: int = 50,
) -> Path:
    """Download a short segment of a YouTube video safely to avoid downloading huge files."""
    import yt_dlp
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    
    s = Settings()
    ffmpeg_loc = str(Path(s.ffmpeg_bin).parent) if Path(s.ffmpeg_bin).exists() else None
    
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "outtmpl": str(out.with_suffix("")),
        "format": "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4][height<=1080]/best",
        "download_ranges": yt_dlp.utils.download_range_func(None, [(start_sec, start_sec + duration_sec)]),
        "force_keyframes_at_cuts": True,
        "max_filesize": max_filesize_mb * 1024 * 1024,
    }
    if ffmpeg_loc:
        ydl_opts["ffmpeg_location"] = ffmpeg_loc

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    # yt-dlp might append .mp4 or other extension
    if out.exists():
        return out
    mp4_cand = out.with_suffix(".mp4")
    if mp4_cand.exists():
        return mp4_cand

    # Check any generated file with matching stem
    for f in out.parent.glob(f"{out.stem}*"):
        if f.is_file() and f.stat().st_size > 0:
            return f

    raise FileNotFoundError(f"Failed to produce downloaded segment for {url} at {output_path}")
