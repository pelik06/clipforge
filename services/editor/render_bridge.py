import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import uuid

from core.config.settings import Settings
from core.models.configuration import JobConfig
from core.models.transcript import TranscriptSegment, Word
from core.storage import save_editor_state, save_export_artifact
from services.captions.service import CaptionRenderer
from services.editor.models import (
    EditorState,
    EditorStatus,
    RenderSnapshot,
)
from services.render.job_manager import RenderJobManager
from services.render.models import RenderJob, RenderJobState


class StudioRenderBridge:
    """Bridges EditorState snapshots into P4 production render queue and registers final exports."""

    def __init__(self, render_manager: Optional[RenderJobManager] = None):
        self.settings = Settings()
        self.render_manager = render_manager or RenderJobManager()
        self.caption_renderer = CaptionRenderer()

    def create_snapshot(self, state: EditorState, preset: str = "tiktok") -> RenderSnapshot:
        snap_id = f"snap_{uuid.uuid4().hex[:8]}"
        return RenderSnapshot(
            snapshot_id=snap_id,
            clip_id=state.clip_id,
            editor_version=state.editor_version,
            editor_state=state.to_dict(),
            preset=preset,
            created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )

    def prepare_render_config(self, state: EditorState, preset: str = "tiktok") -> Tuple[Dict[str, Any], Optional[str]]:
        """Synthesize FFmpeg filters for manual/auto crop, audio volume, and updated captions."""
        work_dir = Path("data/work")
        work_dir.mkdir(parents=True, exist_ok=True)

        vf_parts = []
        af_parts = []

        # 1. Manual Crop vs Auto Reframing
        if state.crop.mode == "manual":
            # Normalized crop [0.0, 1.0] mapped to source dimensions (default 1920x1080)
            cw = f"iw*{max(0.1, min(1.0, state.crop.width)):.3f}"
            ch = f"ih*{max(0.1, min(1.0, state.crop.height)):.3f}"
            cx = f"iw*{max(0.0, min(1.0, state.crop.x)):.3f}"
            cy = f"ih*{max(0.0, min(1.0, state.crop.y)):.3f}"
            vf_parts.append(f"crop={cw}:{ch}:{cx}:{cy}")

        # 2. Burn Custom Edited Captions
        ass_path_str = None
        if state.captions:
            # Convert CaptionSegment list to TranscriptSegment
            segments = []
            for c in state.captions:
                words = [Word(text=tok, start=c.start, end=c.end) for tok in c.text.split()]
                segments.append(
                    TranscriptSegment(
                        text=c.text,
                        start=c.start,
                        end=c.end,
                        words=words,
                    )
                )

            preset_style = state.output.get("caption_preset", "clean")
            ass_content = self.caption_renderer.generate_ass_script(
                segments=segments,
                config=JobConfig(caption_preset=preset_style),
                clip_start=0.0,
                clip_end=state.clip_duration,
            )
            ass_file = work_dir / f"editor_{state.clip_id}_v{state.editor_version}.ass"
            ass_file.write_text(ass_content, encoding="utf-8")

            escaped = str(ass_file.resolve()).replace("\\", "/").replace(":", "\\:")
            vf_parts.append(f"ass=filename='{escaped}'")
            ass_path_str = str(ass_file)

        # 3. Audio Volume / Mute
        if state.audio.mute:
            af_parts.append("volume=0.0")
        elif abs(state.audio.volume - 1.0) > 0.01:
            af_parts.append(f"volume={state.audio.volume:.2f}")

        config = {
            "start_time": state.source_start,
            "duration": state.clip_duration,
            "variant": f"v{state.editor_version}",
            "vf_filter": ",".join(vf_parts) if vf_parts else None,
            "af_filter": ",".join(af_parts) if af_parts else None,
            "composition": state.user_overrides.get("composition") or state.output.get("composition"),
        }
        return config, ass_path_str

    def submit_render(
        self,
        state: EditorState,
        preset: str = "tiktok",
        render_type: str = "final",
        priority: int = 15,
    ) -> Tuple[RenderJob, RenderSnapshot]:
        snapshot = self.create_snapshot(state, preset=preset)
        cfg, _ = self.prepare_render_config(state, preset=preset)
        cfg["snapshot"] = snapshot.to_dict()

        job = self.render_manager.submit_job(
            clip_id=state.clip_id,
            source_id=state.source_id,
            preset=preset,
            render_type=render_type,
            priority=priority,
            config=cfg,
        )

        return job, snapshot

    def finalize_export_record(
        self,
        job: RenderJob,
        state: EditorState,
        render_type: str = "final",
    ) -> Dict[str, Any]:
        """Record completed render artifact into SQLite exports library."""
        exp_id = f"exp_{uuid.uuid4().hex[:8]}"
        out_path = Path(job.output_path) if job.output_path else None
        file_size = out_path.stat().st_size if (out_path and out_path.exists()) else 0

        record = {
            "id": exp_id,
            "clip_id": state.clip_id,
            "editor_version": state.editor_version,
            "render_job_id": job.id,
            "preset": job.preset,
            "render_type": render_type,
            "output_path": job.output_path or "",
            "output_sha256": job.output_sha256,
            "file_size": file_size,
            "duration": state.clip_duration,
            "resolution": "720x1280" if job.preset in {"preview", "draft"} else "1080x1920",
            "status": "EXPORTED" if render_type == "final" else "PREVIEWED",
        }
        save_export_artifact(record)

        # Update editor state status
        state.status = EditorStatus.EXPORTED if render_type == "final" else EditorStatus.PREVIEWED
        save_editor_state({
            "clip_id": state.clip_id,
            "editor_version": state.editor_version,
            "status": state.status.value,
            "state_json": state.to_dict(),
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        })

        return record
