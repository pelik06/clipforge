from dataclasses import dataclass, field
import datetime
from enum import Enum
import json
from typing import Any, Dict, List, Optional
import uuid


class EditorStatus(str, Enum):
    DRAFT = "DRAFT"
    PREVIEWED = "PREVIEWED"
    APPROVED = "APPROVED"
    EXPORTED = "EXPORTED"


@dataclass
class CropConfig:
    x: float = 0.0
    y: float = 0.0
    width: float = 1.0
    height: float = 1.0
    scale: float = 1.0
    mode: str = "auto"  # "auto" | "manual"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x": round(self.x, 3),
            "y": round(self.y, 3),
            "width": round(self.width, 3),
            "height": round(self.height, 3),
            "scale": round(self.scale, 2),
            "mode": self.mode,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CropConfig":
        return cls(
            x=float(d.get("x", 0.0)),
            y=float(d.get("y", 0.0)),
            width=float(d.get("width", 1.0)),
            height=float(d.get("height", 1.0)),
            scale=float(d.get("scale", 1.0)),
            mode=str(d.get("mode", "auto")),
        )


@dataclass
class AudioConfig:
    volume: float = 1.0  # 0.0 to 2.0 (1.0 = 100%)
    mute: bool = False
    fade_in: float = 0.0
    fade_out: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "volume": round(self.volume, 2),
            "mute": self.mute,
            "fade_in": round(self.fade_in, 2),
            "fade_out": round(self.fade_out, 2),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AudioConfig":
        return cls(
            volume=float(d.get("volume", 1.0)),
            mute=bool(d.get("mute", False)),
            fade_in=float(d.get("fade_in", 0.0)),
            fade_out=float(d.get("fade_out", 0.0)),
        )


@dataclass
class CaptionSegment:
    id: str
    start: float  # Relative to clip start
    end: float
    text: str
    style: Dict[str, Any] = field(default_factory=dict)
    emphasis: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "text": self.text,
            "style": self.style,
            "emphasis": self.emphasis,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CaptionSegment":
        return cls(
            id=str(d.get("id", f"cap_{uuid.uuid4().hex[:6]}")),
            start=float(d.get("start", 0.0)),
            end=float(d.get("end", 0.0)),
            text=str(d.get("text", "")),
            style=dict(d.get("style", {})),
            emphasis=bool(d.get("emphasis", False)),
        )


@dataclass
class EditorState:
    clip_id: str
    source_id: str
    source_duration: float
    source_start: float
    source_end: float
    crop: CropConfig = field(default_factory=CropConfig)
    layout: str = "AUTO"  # "AUTO" | "TRACK" | "SPLIT"
    captions: List[CaptionSegment] = field(default_factory=list)
    audio: AudioConfig = field(default_factory=AudioConfig)
    output: Dict[str, Any] = field(default_factory=dict)
    ai_suggestions: Dict[str, Any] = field(default_factory=dict)
    user_overrides: Dict[str, Any] = field(default_factory=dict)
    editor_version: int = 1
    status: EditorStatus = EditorStatus.DRAFT
    updated_at: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

    @property
    def clip_duration(self) -> float:
        return max(0.0, round(self.source_end - self.source_start, 3))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "clip_id": self.clip_id,
            "source_id": self.source_id,
            "source_duration": round(self.source_duration, 3),
            "source_start": round(self.source_start, 3),
            "source_end": round(self.source_end, 3),
            "clip_duration": self.clip_duration,
            "crop": self.crop.to_dict(),
            "layout": self.layout,
            "captions": [c.to_dict() for c in self.captions],
            "audio": self.audio.to_dict(),
            "output": self.output,
            "ai_suggestions": self.ai_suggestions,
            "user_overrides": self.user_overrides,
            "editor_version": self.editor_version,
            "status": self.status.value if isinstance(self.status, EditorStatus) else str(self.status),
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "EditorState":
        raw_status = d.get("status", "DRAFT")
        status = EditorStatus(raw_status) if raw_status in EditorStatus._value2member_map_ else EditorStatus.DRAFT
        return cls(
            clip_id=str(d.get("clip_id", "")),
            source_id=str(d.get("source_id", "")),
            source_duration=float(d.get("source_duration", 300.0)),
            source_start=float(d.get("source_start", 0.0)),
            source_end=float(d.get("source_end", 30.0)),
            crop=CropConfig.from_dict(d.get("crop", {})),
            layout=str(d.get("layout", "AUTO")),
            captions=[CaptionSegment.from_dict(c) for c in d.get("captions", [])],
            audio=AudioConfig.from_dict(d.get("audio", {})),
            output=dict(d.get("output", {})),
            ai_suggestions=dict(d.get("ai_suggestions", {})),
            user_overrides=dict(d.get("user_overrides", {})),
            editor_version=int(d.get("editor_version", 1)),
            status=status,
            updated_at=str(d.get("updated_at", datetime.datetime.now(datetime.timezone.utc).isoformat())),
        )

    def clone(self) -> "EditorState":
        """Produce an isolated deep copy of the editor state."""
        import copy
        return copy.deepcopy(self)

@dataclass
class RenderSnapshot:
    snapshot_id: str
    clip_id: str
    editor_version: int
    editor_state: Dict[str, Any]
    preset: str
    render_version: str = "p4.1"
    created_at: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "clip_id": self.clip_id,
            "editor_version": self.editor_version,
            "editor_state": self.editor_state,
            "preset": self.preset,
            "render_version": self.render_version,
            "created_at": self.created_at,
        }
