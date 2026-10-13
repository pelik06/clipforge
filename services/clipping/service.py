from pathlib import Path
import subprocess
from core.config.settings import Settings


class ClipRenderer:
    """FFmpeg-backed renderer for extracting short-form clips."""

    def render(self, source_path: str, start: float, end: float, output_path: str) -> str:
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"Source video file not found: {source_path}")
        if not source.is_file():
            raise ValueError(f"Source path is not a file: {source_path}")
        if start < 0:
            raise ValueError(f"Start timestamp cannot be negative: {start}")
        if end <= start:
            raise ValueError(f"End timestamp ({end}) must be greater than start ({start})")

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        duration = end - start

        s = Settings()
        cmd = [
            s.ffmpeg_bin,
            "-y",
            "-ss", f"{start:.3f}",
            "-i", str(source),
            "-t", f"{duration:.3f}",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "22",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            str(out),
        ]

        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120,
        )

        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg clipping failed (code {proc.returncode}): {proc.stderr[-400:]}")

        if not out.exists() or out.stat().st_size == 0:
            raise RuntimeError(f"FFmpeg clipping succeeded but output file is missing or empty: {output_path}")

        return str(out)
