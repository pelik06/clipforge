from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any, Dict, List, Optional

from core.config.settings import Settings


@dataclass
class RenderValidationResult:
    is_valid: bool
    duration: float = 0.0
    width: int = 0
    height: int = 0
    video_codec: str = ""
    audio_codec: str = ""
    file_size: int = 0
    sha256: Optional[str] = None
    errors: List[str] = field(default_factory=list)


def compute_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class RenderValidator:
    """Validates final rendered video containers, stream codecs, dimensions, and duration tolerances."""

    def __init__(self, duration_tolerance_sec: float = 0.15):
        self.settings = Settings()
        self.duration_tolerance_sec = duration_tolerance_sec

    def validate(
        self,
        output_path: str,
        expected_duration: Optional[float] = None,
        expected_width: int = 1080,
        expected_height: int = 1920,
    ) -> RenderValidationResult:
        p = Path(output_path)
        errors = []

        if not p.exists():
            return RenderValidationResult(is_valid=False, errors=[f"Render output file not found: {output_path}"])

        size = p.stat().st_size
        if size <= 1024:
            return RenderValidationResult(is_valid=False, file_size=size, errors=[f"Render output is suspiciously empty ({size} bytes)"])

        # FFprobe inspection
        cmd = [
            self.settings.ffprobe_bin,
            "-v", "error",
            "-show_entries", "stream=index,codec_type,codec_name,width,height:format=format_name,duration,size",
            "-of", "json",
            str(p),
        ]

        try:
            r = subprocess.run(cmd, capture_output=True, text=True, check=True)
            info = json.loads(r.stdout)
        except Exception as exc:
            return RenderValidationResult(is_valid=False, file_size=size, errors=[f"FFprobe failed to inspect container: {str(exc)}"])

        fmt = info.get("format", {})
        streams = info.get("streams", [])

        # Format / container check
        fmt_name = fmt.get("format_name", "")
        if "mp4" not in fmt_name and "mov" not in fmt_name:
            errors.append(f"Invalid container format '{fmt_name}', expected MP4")

        actual_duration = float(fmt.get("duration", 0.0))
        if actual_duration <= 0.0:
            errors.append("Invalid duration: zero or negative")

        # Stream checks
        v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        a_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

        if not v_stream:
            errors.append("Missing video stream in MP4 container")
        if not a_stream:
            errors.append("Missing audio stream in MP4 container")

        v_codec = v_stream.get("codec_name", "") if v_stream else ""
        a_codec = a_stream.get("codec_name", "") if a_stream else ""

        if v_codec not in {"h264", "avc1"}:
            errors.append(f"Invalid video codec '{v_codec}', expected H.264")

        w = int(v_stream.get("width", 0)) if v_stream else 0
        h = int(v_stream.get("height", 0)) if v_stream else 0

        if expected_width > 0 and w != expected_width:
            errors.append(f"Width mismatch: actual {w} != expected {expected_width}")
        if expected_height > 0 and h != expected_height:
            errors.append(f"Height mismatch: actual {h} != expected {expected_height}")

        # Duration tolerance check (baseline: <= 0.15s)
        if expected_duration is not None and expected_duration > 0:
            dur_error = abs(actual_duration - expected_duration)
            if dur_error > self.duration_tolerance_sec:
                errors.append(
                    f"Duration error {dur_error:.3f}s exceeds tolerance of {self.duration_tolerance_sec:.3f}s (expected {expected_duration:.2f}s, actual {actual_duration:.2f}s)"
                )

        sha = compute_file_sha256(p) if not errors else None

        return RenderValidationResult(
            is_valid=(len(errors) == 0),
            duration=round(actual_duration, 2),
            width=w,
            height=h,
            video_codec=v_codec,
            audio_codec=a_codec,
            file_size=size,
            sha256=sha,
            errors=errors,
        )
