import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from core.storage import get_editor_state, save_editor_state
from services.editor.models import (
    AudioConfig,
    CaptionSegment,
    CropConfig,
    EditorState,
    EditorStatus,
)
from services.editor.validation import EditorValidator


class EditorStateManager:
    """Coordinates lifecycle, persistence, initialization from AI metadata, and override diffing."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path

    def load_or_initialize(self, clip: Dict[str, Any], transcript_segments: Optional[List[Any]] = None) -> EditorState:
        clip_id = str(clip.get("id", ""))
        existing = get_editor_state(clip_id, db_path=self.db_path)
        if existing:
            return EditorState.from_dict(existing["state_json"])

        # Initialize from AI generated clip metadata
        src_start = float(clip.get("start_time", 0.0))
        dur_str = str(clip.get("duration", "30.0")).replace("s", "")
        try:
            dur = float(dur_str)
        except ValueError:
            dur = 30.0
        src_end = float(clip.get("end_time", src_start + dur))
        src_id = str(clip.get("media_url") or clip.get("vod") or "data/input/real_talk_35s.mp4")

        # Parse captions from transcript segments if provided
        captions: List[CaptionSegment] = []
        if transcript_segments:
            for s in transcript_segments:
                s_start = getattr(s, "start", 0.0)
                s_end = getattr(s, "end", 0.0)
                # Filter to clip window and rebase
                if s_end > src_start and s_start < src_end:
                    rel_s = max(0.0, round(s_start - src_start, 3))
                    rel_e = min(dur, round(s_end - src_start, 3))
                    if rel_e > rel_s:
                        captions.append(
                            CaptionSegment(
                                id=f"cap_{uuid.uuid4().hex[:6]}",
                                start=rel_s,
                                end=rel_e,
                                text=getattr(s, "text", "").strip(),
                            )
                        )

        ai_suggestions = {
            "start_time": src_start,
            "end_time": src_end,
            "layout": clip.get("layout_mode", "TRACK"),
            "speaker_track_id": clip.get("speaker_track_id", "face_01"),
            "preset": clip.get("caption_preset", "clean"),
        }

        state = EditorState(
            clip_id=clip_id,
            source_id=src_id,
            source_duration=max(300.0, src_end + 30.0),
            source_start=src_start,
            source_end=src_end,
            crop=CropConfig(x=0.0, y=0.0, width=1.0, height=1.0, scale=1.0, mode="auto"),
            layout=str(clip.get("layout_mode", "AUTO")),
            captions=captions,
            audio=AudioConfig(volume=1.0, mute=False),
            output={"preset": "tiktok", "resolution": "1080x1920"},
            ai_suggestions=ai_suggestions,
            user_overrides={},
            editor_version=1,
            status=EditorStatus.DRAFT,
            updated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )

        self.save(state)
        return state

    def save(self, state: EditorState) -> EditorState:
        EditorValidator.validate_all(state)
        record = {
            "clip_id": state.clip_id,
            "editor_version": state.editor_version,
            "status": state.status.value if isinstance(state.status, EditorStatus) else str(state.status),
            "state_json": state.to_dict(),
            "updated_at": state.updated_at,
        }
        save_editor_state(record, db_path=self.db_path)
        return state
