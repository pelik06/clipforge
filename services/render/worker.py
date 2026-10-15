import datetime
import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import Any, Dict, Optional

from core.config.settings import Settings
from core.models.transcript import Word
from core.storage import save_render_job
from services.render.models import RenderJob, RenderJobState
from services.render.presets import get_preset_config
from services.render.progress import RenderProgressTracker
from services.render.retry import RenderRetryManager
from services.render.validator import RenderValidator, compute_file_sha256

RENDER_VERSION = "p4.1"
MIN_FREE_DISK_MB = 100


class RenderWorker:
    """Executes single render job with idempotency checking, progress reporting, validation, and cancellation support."""

    def __init__(
        self,
        cancellation_manager: Optional[RenderCancellationManager] = None,
        renders_dir: str = "data/renders",
    ):
        self.settings = Settings()
        self.cancellation_manager = cancellation_manager or RenderCancellationManager()
        self.retry_manager = RenderRetryManager(max_retries=2)
        self.validator = RenderValidator(duration_tolerance_sec=0.15)

        self.renders_dir = Path(renders_dir)
        self.tmp_dir = self.renders_dir / "tmp"
        self.final_dir = self.renders_dir / "final"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        self.final_dir.mkdir(parents=True, exist_ok=True)

    def check_disk_space(self) -> bool:
        """Verify host machine has sufficient free disk capacity before starting render."""
        try:
            total, used, free = shutil.disk_usage(str(self.renders_dir))
            free_mb = free / (1024 * 1024)
            return free_mb >= MIN_FREE_DISK_MB
        except Exception:
            return True

    def execute_job(self, job: RenderJob) -> RenderJob:
        tracker = RenderProgressTracker()
        job.started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # 1. Early Resource Check
        if not self.check_disk_space():
            job.status = RenderJobState.FAILED
            job.stage = "Failed: Insufficient disk space on host (minimum 100MB required)"
            job.error_message = "Insufficient free disk space"
            save_render_job(job.to_dict())
            return job

        # 2. Idempotency Check
        preset_cfg = get_preset_config(job.preset)
        variant = job.config.get("variant", "normal")
        final_filename = f"{job.clip_id}_{variant}_{job.preset}_{RENDER_VERSION}.mp4"
        final_path = self.final_dir / final_filename

        expected_dur = float(job.config.get("duration", 0.0))
        if final_path.exists() and final_path.stat().st_size > 1024:
            val_cached = self.validator.validate(
                str(final_path),
                expected_duration=expected_dur if expected_dur > 0 else None,
                expected_width=preset_cfg.width,
                expected_height=preset_cfg.height,
            )
            if val_cached.is_valid:
                job.status = RenderJobState.COMPLETED
                job.stage = "Completed: Reused existing verified render artifact (idempotent)"
                job.progress = tracker.complete()
                job.output_path = str(final_path)
                job.output_sha256 = val_cached.sha256
                job.completed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
                save_render_job(job.to_dict())
                return job

        # 3. Preparation Stage (0 - 5%)
        job.transition_to(RenderJobState.PREPARING, "Preparing render inputs and filters")
        job.progress = tracker.update(RenderJobState.PREPARING, 1.0)
        save_render_job(job.to_dict())

        src_path = Path(job.source_id)
        if not src_path.exists():
            job.status = RenderJobState.FAILED
            job.stage = f"Source media file not found: {job.source_id}"
            job.error_message = f"Missing source file: {job.source_id}"
            save_render_job(job.to_dict())
            return job

        tmp_output = self.tmp_dir / f"{job.id}_tmp.mp4"

        # 4. Rendering Stage (5 - 90%)
        job.transition_to(RenderJobState.RENDERING, f"Rendering {preset_cfg.width}x{preset_cfg.height} via FFmpeg ({job.preset})")
        job.progress = tracker.update(RenderJobState.RENDERING, 0.1)
        save_render_job(job.to_dict())

        start_sec = float(job.config.get("start_time", 0.0))
        duration_sec = float(job.config.get("duration", 0.0))
        vf_filter = job.config.get("vf_filter")

        try:
            if preset_cfg.name == "hyperframes":
                from services.render.hyperframes_composition import (
                    HyperframesCompositionBuilder,
                    HyperframesConfig,
                )
                from services.render.hyperframes_runner import HyperframesRunner

                comp_dir = work_dir / f"hf_{job.id}"
                builder = HyperframesCompositionBuilder()
                words_data = job.config.get("words", [])
                words = [Word(text=w.get("text", ""), start=float(w.get("start", 0)), end=float(w.get("end", 0))) for w in words_data]

                builder.build_composition(
                    output_dir=comp_dir,
                    source_video_path=src_path,
                    clip_duration=duration_sec if duration_sec > 0.0 else 60.0,
                    words=words,
                    config=HyperframesConfig(
                        title=job.config.get("title", "HIGHLIGHT MOMENT"),
                        caption_preset=job.config.get("caption_preset", "karaoke"),
                        caption_position=job.config.get("caption_position", "bottom_safe"),
                    ),
                )
                runner = HyperframesRunner(quality="draft", fps=preset_cfg.fps)
                res = runner.render(comp_dir, tmp_output)
                if not res.success:
                    raise RuntimeError(f"HyperFrames render failed: {res.error}")
            else:
                scale_crop = f"scale={preset_cfg.width}:{preset_cfg.height}:force_original_aspect_ratio=increase,crop={preset_cfg.width}:{preset_cfg.height}"
                combined_vf = f"{vf_filter},{scale_crop}" if vf_filter else scale_crop

                cmd = [
                    self.settings.ffmpeg_bin,
                    "-y",
                ]
                if start_sec > 0.0:
                    cmd.extend(["-ss", str(start_sec)])
                cmd.extend(["-i", str(src_path)])
                if duration_sec > 0.0:
                    cmd.extend(["-t", str(duration_sec)])

                cmd.extend([
                    "-vf", combined_vf,
                    "-c:v", "libx264",
                    "-preset", preset_cfg.ffmpeg_preset,
                    "-b:v", preset_cfg.video_bitrate,
                    "-crf", str(preset_cfg.crf),
                    "-r", str(preset_cfg.fps),
                    "-c:a", "aac",
                    "-b:a", preset_cfg.audio_bitrate,
                ])
                if preset_cfg.audio_normalize:
                    cmd.extend(["-af", "loudnorm=I=-16:TP=-1.5:LRA=11"])

                cmd.extend(["-movflags", "+faststart", str(tmp_output)])

                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.cancellation_manager.register_process(job.id, proc)

                stdout, stderr = proc.communicate(timeout=180.0)
                self.cancellation_manager.unregister_process(job.id)

                if self.cancellation_manager.is_cancelled(job.id):
                    job.status = RenderJobState.CANCELLED
                    job.stage = "Render cancelled by operator"
                    if tmp_output.exists():
                        tmp_output.unlink()
                    save_render_job(job.to_dict())
                    return job

                if proc.returncode != 0:
                    err_text = stderr.decode("utf-8", errors="replace")[-400:]
                    raise RuntimeError(f"FFmpeg render process failed (exit {proc.returncode}): {err_text}")
        except Exception as exc:
            self.cancellation_manager.unregister_process(job.id)
            if tmp_output.exists():
                tmp_output.unlink()

            if self.retry_manager.should_retry(exc, job.retry_count):
                job.status = RenderJobState.RETRYING
                job.retry_count += 1
                job.stage = f"Transient render failure; queued for retry #{job.retry_count}"
                job.error_message = str(exc)
            else:
                job.status = RenderJobState.FAILED
                job.stage = f"Render failed: {str(exc)}"
                job.error_message = str(exc)

            save_render_job(job.to_dict())
            return job

        # 5. Validation Stage (90 - 100%)
        job.transition_to(RenderJobState.VALIDATING, "Validating container streams and duration tolerance")
        job.progress = tracker.update(RenderJobState.VALIDATING, 0.5)
        save_render_job(job.to_dict())

        val_res = self.validator.validate(
            str(tmp_output),
            expected_duration=duration_sec if duration_sec > 0.0 else None,
            expected_width=preset_cfg.width,
            expected_height=preset_cfg.height,
        )

        if not val_res.is_valid:
            if tmp_output.exists():
                tmp_output.unlink()
            job.status = RenderJobState.FAILED
            job.stage = f"Validation failed: {', '.join(val_res.errors)}"
            job.error_message = "; ".join(val_res.errors)
            save_render_job(job.to_dict())
            return job

        # Move from tmp/ to final/
        shutil.move(str(tmp_output), str(final_path))
        job.output_path = str(final_path)
        job.output_sha256 = val_res.sha256
        job.transition_to(RenderJobState.COMPLETED, f"Render completed successfully ({preset_cfg.width}x{preset_cfg.height}, {val_res.file_size} bytes)")
        job.progress = tracker.complete()
        job.completed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save_render_job(job.to_dict())

        return job
