from dataclasses import dataclass, field
from enum import Enum
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional


class RenderJobState(str, Enum):
    QUEUED = "QUEUED"
    PREPARING = "PREPARING"
    RENDERING = "RENDERING"
    VALIDATING = "VALIDATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    RETRYING = "RETRYING"


class RenderType(str, Enum):
    FINAL = "final"
    PREVIEW = "preview"
    DRAFT = "draft"


class RenderPreset(str, Enum):
    TIKTOK = "tiktok"
    HIGH_QUALITY = "high_quality"
    DRAFT = "draft"
    PREVIEW = "preview"
    HYPERFRAMES = "hyperframes"

VALID_TRANSITIONS = {
    RenderJobState.QUEUED: {RenderJobState.PREPARING, RenderJobState.CANCELLED},
    RenderJobState.PREPARING: {RenderJobState.RENDERING, RenderJobState.FAILED, RenderJobState.CANCELLED},
    RenderJobState.RENDERING: {RenderJobState.VALIDATING, RenderJobState.FAILED, RenderJobState.CANCELLED, RenderJobState.RETRYING},
    RenderJobState.VALIDATING: {RenderJobState.COMPLETED, RenderJobState.FAILED, RenderJobState.RETRYING},
    RenderJobState.RETRYING: {RenderJobState.PREPARING, RenderJobState.FAILED, RenderJobState.CANCELLED},
    RenderJobState.COMPLETED: set(),
    RenderJobState.FAILED: set(),
    RenderJobState.CANCELLED: set(),
}


@dataclass
class ExportPresetConfig:
    name: str
    width: int
    height: int
    fps: int = 30
    video_bitrate: str = "4500k"
    audio_bitrate: str = "192k"
    crf: int = 20
    ffmpeg_preset: str = "fast"
    audio_normalize: bool = False

    def validate(self):
        if self.width <= 0 or self.height <= 0:
            raise ValueError(f"Invalid dimensions: {self.width}x{self.height}")
        if self.width % 2 != 0 or self.height % 2 != 0:
            raise ValueError(f"Dimensions must be even for H.264: {self.width}x{self.height}")
        if self.fps <= 0 or self.fps > 120:
            raise ValueError(f"Invalid framerate: {self.fps}")
        if not self.video_bitrate or not self.audio_bitrate:
            raise ValueError("Bitrate settings must be non-empty")


@dataclass
class RenderJob:
    id: str
    clip_id: str
    source_id: str
    status: RenderJobState = RenderJobState.QUEUED
    stage: str = "Queued in render queue"
    progress: float = 0.0
    preset: str = "tiktok"
    render_type: str = "final"
    output_path: Optional[str] = None
    output_sha256: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    priority: int = 10                  # Higher integer = higher priority
    config: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def transition_to(self, new_state: RenderJobState, stage_detail: Optional[str] = None):
        """Enforce strict monotonic state machine transitions."""
        allowed = VALID_TRANSITIONS.get(self.status, set())
        if new_state not in allowed:
            raise ValueError(
                f"Invalid state transition for RenderJob {self.id}: cannot transition from {self.status.value} to {new_state.value}"
            )
        self.status = new_state
        if stage_detail:
            self.stage = stage_detail

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "clip_id": self.clip_id,
            "source_id": self.source_id,
            "status": self.status.value if isinstance(self.status, RenderJobState) else str(self.status),
            "stage": self.stage,
            "progress": round(self.progress, 1),
            "preset": self.preset,
            "render_type": self.render_type,
            "output_path": self.output_path,
            "output_sha256": self.output_sha256,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "priority": self.priority,
            "config": self.config,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }
