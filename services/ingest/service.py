from pathlib import Path
import json
import shutil
import subprocess
import uuid
from typing import Optional, Dict, Any, List
from core.config.settings import Settings
from core.models.transcript import TranscriptSegment, Word


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
    """Extract real YouTube video metadata using yt-dlp without downloading full video."""
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

    video_id = "unknown"
    if "youtu.be/" in clean_url:
        video_id = clean_url.split("youtu.be/")[1].split("?")[0].split("&")[0]
    elif "watch?v=" in clean_url:
        video_id = clean_url.split("watch?v=")[1].split("&")[0]

    return {
        "success": True,
        "title": f"YouTube Video ({video_id})",
        "duration": None,
        "uploader": "YouTube Streamer",
        "thumbnail": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg" if video_id != "unknown" else None,
        "view_count": None,
        "webpage_url": clean_url,
        "source": "fallback",
    }


def fetch_youtube_transcript(
    url: str,
    cache_dir: Optional[Path] = None,
    preferred_langs: Optional[List[str]] = None,
) -> List[TranscriptSegment]:
    """Fetch complete timestamped transcript from YouTube auto-captions or subtitles using yt-dlp.
    
    Returns parsed TranscriptSegment list with word-level timestamps in < 3 seconds.
    """
    import yt_dlp
    work_dir = Path(cache_dir) if cache_dir else Path("data/work")
    work_dir.mkdir(parents=True, exist_ok=True)
    temp_stem = f"yt_sub_{uuid.uuid4().hex[:8]}"
    out_tmpl = str(work_dir / temp_stem)

    langs = preferred_langs or ["id", "en"]
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": langs,
        "subtitlesformat": "json3",
        "outtmpl": out_tmpl,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception:
        pass

    json_files = list(work_dir.glob(f"{temp_stem}*.json3"))
    if not json_files:
        return []

    target_file = json_files[0]
    for lang in langs:
        for f in json_files:
            if f".{lang}." in f.name:
                target_file = f
                break

    try:
        data = json.loads(target_file.read_text(encoding="utf-8"))
        events = data.get("events", [])
        segments: List[TranscriptSegment] = []

        for ev in events:
            t_start = ev.get("tStartMs", 0) / 1000.0
            d_dur = ev.get("dDurationMs", 0) / 1000.0
            t_end = t_start + d_dur
            segs = ev.get("segs", [])

            words: List[Word] = []
            text_parts: List[str] = []

            for s_idx, s in enumerate(segs):
                w_text = s.get("utf8", "")
                t_offset = s.get("tOffsetMs", 0) / 1000.0
                clean_tok = w_text.strip()
                if clean_tok and w_text != "\n":
                    text_parts.append(clean_tok)
                    w_t0 = t_start + t_offset
                    if s_idx < len(segs) - 1 and "tOffsetMs" in segs[s_idx + 1]:
                        next_offset = segs[s_idx + 1].get("tOffsetMs", 0) / 1000.0
                        w_t1 = t_start + next_offset
                    else:
                        w_t1 = max(w_t0 + 0.20, t_end)
                    words.append(
                        Word(
                            text=clean_tok,
                            start=round(w_t0, 3),
                            end=round(max(w_t0 + 0.05, w_t1), 3),
                        )
                    )

            full_text = " ".join(text_parts).strip()
            if full_text:
                segments.append(
                    TranscriptSegment(
                        text=full_text,
                        start=round(t_start, 3),
                        end=round(t_end, 3),
                        words=words,
                    )
                )

        try:
            for jf in json_files:
                jf.unlink()
        except Exception:
            pass

        return segments
    except Exception:
        return []


def download_youtube_segment(
    url: str,
    output_path: str,
    start_sec: float = 0.0,
    duration_sec: float = 15.0,
    max_filesize_mb: int = 50,
) -> Path:
    """Download a targeted segment of a YouTube video using download_ranges."""
    import yt_dlp
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    
    s = Settings()
    ffmpeg_loc = str(Path(s.ffmpeg_bin).parent) if Path(s.ffmpeg_bin).exists() else None
    
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "outtmpl": str(out.with_suffix("")),
        "format": "bestvideo[protocol=https]+bestaudio[protocol=https]/bestvideo[protocol=m3u8_native]+bestaudio/bestvideo+bestaudio/best",
        "download_ranges": yt_dlp.utils.download_range_func(None, [(start_sec, start_sec + duration_sec)]),
        "force_keyframes_at_cuts": True,
        "max_filesize": max_filesize_mb * 1024 * 1024,
    }
    if ffmpeg_loc:
        ydl_opts["ffmpeg_location"] = ffmpeg_loc

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    if out.exists():
        return out
    mp4_cand = out.with_suffix(".mp4")
    if mp4_cand.exists():
        return mp4_cand

    for f in out.parent.glob(f"{out.stem}*"):
        if f.is_file() and f.stat().st_size > 0:
            return f

    raise FileNotFoundError(f"Failed to produce downloaded segment for {url} at {output_path}")
