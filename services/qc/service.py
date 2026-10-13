from dataclasses import dataclass
from pathlib import Path
import json
import subprocess
from core.config.settings import Settings


@dataclass
class QCResult:
    passed: bool
    checks: dict[str, bool]
    errors: list[str]


class QualityController:
    """Verifies technical quality and playback integrity of generated video clips."""

    def check(self, video_path: str) -> QCResult:
        path = Path(video_path)
        checks = {
            "file_exists": False,
            "non_empty": False,
            "valid_container": False,
            "video_stream": False,
            "valid_duration": False,
        }
        errors = []

        if not path.exists():
            errors.append(f"Video file does not exist: {video_path}")
            return QCResult(passed=False, checks=checks, errors=errors)

        checks["file_exists"] = True

        if path.stat().st_size <= 1024:
            errors.append(f"Video file is too small or empty ({path.stat().st_size} bytes)")
            return QCResult(passed=False, checks=checks, errors=errors)

        checks["non_empty"] = True

        s = Settings()
        cmd = [
            s.ffprobe_bin,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(path),
        ]

        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
            if proc.returncode != 0:
                errors.append(f"FFprobe failed to inspect file: {proc.stderr[:200]}")
                return QCResult(passed=False, checks=checks, errors=errors)

            data = json.loads(proc.stdout)
            checks["valid_container"] = True

            streams = data.get("streams", [])
            video_streams = [st for st in streams if st.get("codec_type") == "video"]
            if video_streams:
                checks["video_stream"] = True
            else:
                errors.append("No video stream found in media file.")

            fmt = data.get("format", {})
            duration = float(fmt.get("duration", 0.0))
            if duration > 0.1:
                checks["valid_duration"] = True
            else:
                errors.append(f"Invalid duration: {duration}s")

        except Exception as exc:
            errors.append(f"Inspection error: {str(exc)}")

        passed = all(checks.values()) and len(errors) == 0
        return QCResult(passed=passed, checks=checks, errors=errors)
