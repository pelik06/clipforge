"""HyperFrames CLI execution runner.

Drives deterministic headless MP4 rendering from an authored HyperFrames project directory.
"""

from dataclasses import dataclass
import json
import logging
from pathlib import Path
import subprocess
import time
from typing import Optional

from core.config.settings import Settings

logger = logging.getLogger("clipforge.hyperframes.runner")


@dataclass
class HyperframesRenderResult:
    success: bool
    output_path: Path
    duration: float
    file_size_bytes: int
    elapsed_sec: float
    error: Optional[str] = None


class HyperframesRunner:
    """Executes HyperFrames render CLI with deterministic headless browser pipeline."""

    def __init__(self, quality: str = "draft", fps: int = 30):
        self.quality = quality
        self.fps = fps
        self.settings = Settings()

    def render(
        self,
        composition_dir: Path,
        output_mp4_path: Path,
        quality: Optional[str] = None,
        timeout_sec: int = 240,
    ) -> HyperframesRenderResult:
        comp_path = Path(composition_dir).resolve()
        out_path = Path(output_mp4_path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        q = quality or self.quality

        cmd = [
            "npx",
            "hyperframes",
            "render",
            str(comp_path),
            "-o",
            str(out_path),
            "--fps",
            str(self.fps),
            "-q",
            q,
            "--best-effort",
        ]

        t0 = time.time()
        logger.info(f"Executing HyperFrames render: {' '.join(cmd)}")

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            shell=True,
        )

        elapsed = round(time.time() - t0, 2)

        if proc.returncode != 0 or not out_path.exists() or out_path.stat().st_size == 0:
            err_msg = proc.stderr[-800:] if proc.stderr else (proc.stdout[-800:] if proc.stdout else "Unknown CLI error")
            logger.error(f"HyperFrames render failed: {err_msg}")
            return HyperframesRenderResult(
                success=False,
                output_path=out_path,
                duration=0.0,
                file_size_bytes=0,
                elapsed_sec=elapsed,
                error=err_msg,
            )

        # Inspect duration via ffprobe
        dur = self._probe_duration(out_path)
        file_size = out_path.stat().st_size

        logger.info(f"HyperFrames render completed successfully: {out_path} ({file_size} bytes, {dur}s, {elapsed}s wall)")
        return HyperframesRenderResult(
            success=True,
            output_path=out_path,
            duration=dur,
            file_size_bytes=file_size,
            elapsed_sec=elapsed,
            error=None,
        )

    def _probe_duration(self, mp4_path: Path) -> float:
        try:
            cmd = [
                self.settings.ffprobe_bin,
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                str(mp4_path),
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                return float(data.get("format", {}).get("duration", 0.0))
        except Exception:
            pass
        return 0.0
