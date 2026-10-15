"""HyperFrames Composition Data Models.

Defines layer-based composition schema, layer types, animation types,
and serializable HyperframesComposition model.
"""

from dataclasses import dataclass, field
from enum import Enum
import json
from typing import Any, Dict, List, Optional
import uuid


class LayerType(str, Enum):
    VIDEO = "video"
    IMAGE = "image"
    PERSON = "person"
    TEXT = "text"
    HOOK = "hook"
    CAPTION = "caption"
    SHAPE = "shape"
    PROGRESS_BAR = "progress_bar"
    OVERLAY = "overlay"


class AnimationType(str, Enum):
    NONE = "none"
    FADE = "fade"
    POP = "pop"
    SCALE = "scale"
    SLIDE_UP = "slide_up"
    SLIDE_DOWN = "slide_down"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"
    WORD_POP = "word_pop"
    WORD_HIGHLIGHT = "word_highlight"
    SPRING = "spring"


class TemplateType(str, Enum):
    VIRAL_PODCAST = "VIRAL_PODCAST"
    TWO_SPEAKER = "TWO_SPEAKER"
    INTERVIEW = "INTERVIEW"
    FINANCE = "FINANCE"
    MINIMAL = "MINIMAL"


@dataclass
class CompositionLayer:
    """Single layer in a HyperFrames multi-track composition."""

    id: str
    type: LayerType
    start: float  # Relative to clip start
    end: float
    x: float = 540.0  # Center X coordinate in 1080x1920
    y: float = 960.0  # Center Y coordinate
    width: float = 1080.0
    height: float = 1920.0
    scale: float = 1.0
    rotation: float = 0.0  # Degrees
    opacity: float = 1.0  # 0.0 to 1.0
    z_index: int = 1
    visible: bool = True
    animation_in: Dict[str, Any] = field(default_factory=lambda: {"type": "fade", "duration": 0.4})
    animation_out: Dict[str, Any] = field(default_factory=lambda: {"type": "fade", "duration": 0.4})
    animation_loop: Dict[str, Any] = field(default_factory=lambda: {"type": "none"})
    data: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> float:
        return max(0.0, round(self.end - self.start, 3))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value if isinstance(self.type, LayerType) else str(self.type),
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "duration": self.duration,
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "width": round(self.width, 2),
            "height": round(self.height, 2),
            "scale": round(self.scale, 3),
            "rotation": round(self.rotation, 2),
            "opacity": round(self.opacity, 3),
            "z_index": self.z_index,
            "visible": self.visible,
            "animation_in": self.animation_in,
            "animation_out": self.animation_out,
            "animation_loop": self.animation_loop,
            "data": self.data,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CompositionLayer":
        raw_type = d.get("type", "video")
        layer_type = LayerType(raw_type) if raw_type in LayerType._value2member_map_ else LayerType.TEXT
        return cls(
            id=str(d.get("id", f"layer_{uuid.uuid4().hex[:6]}")),
            type=layer_type,
            start=float(d.get("start", 0.0)),
            end=float(d.get("end", 5.0)),
            x=float(d.get("x", 540.0)),
            y=float(d.get("y", 960.0)),
            width=float(d.get("width", 1080.0)),
            height=float(d.get("height", 1920.0)),
            scale=float(d.get("scale", 1.0)),
            rotation=float(d.get("rotation", 0.0)),
            opacity=float(d.get("opacity", 1.0)),
            z_index=int(d.get("z_index", 1)),
            visible=bool(d.get("visible", True)),
            animation_in=dict(d.get("animation_in", {"type": "fade", "duration": 0.4})),
            animation_out=dict(d.get("animation_out", {"type": "fade", "duration": 0.4})),
            animation_loop=dict(d.get("animation_loop", {"type": "none"})),
            data=dict(d.get("data", {})),
        )


@dataclass
class HyperframesComposition:
    """Complete multi-layer HyperFrames composition document."""

    composition_id: str
    clip_id: str
    template: str = TemplateType.VIRAL_PODCAST.value
    width: int = 1080
    height: int = 1920
    duration: float = 60.0
    layers: List[CompositionLayer] = field(default_factory=list)
    captions: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: int = 1

    def get_layer(self, layer_id: str) -> Optional[CompositionLayer]:
        for layer in self.layers:
            if layer.id == layer_id:
                return layer
        return None

    def add_layer(self, layer: CompositionLayer) -> None:
        self.layers.append(layer)
        self.layers.sort(key=lambda l: l.z_index)

    def remove_layer(self, layer_id: str) -> bool:
        initial_len = len(self.layers)
        self.layers = [l for l in self.layers if l.id != layer_id]
        return len(self.layers) < initial_len

    def to_dict(self) -> Dict[str, Any]:
        return {
            "composition_id": self.composition_id,
            "clip_id": self.clip_id,
            "template": self.template,
            "width": self.width,
            "height": self.height,
            "duration": round(self.duration, 3),
            "layers": [l.to_dict() for l in self.layers],
            "captions": self.captions,
            "metadata": self.metadata,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "HyperframesComposition":
        return cls(
            composition_id=str(d.get("composition_id", f"comp_{uuid.uuid4().hex[:8]}")),
            clip_id=str(d.get("clip_id", "")),
            template=str(d.get("template", TemplateType.VIRAL_PODCAST.value)),
            width=int(d.get("width", 1080)),
            height=int(d.get("height", 1920)),
            duration=float(d.get("duration", 60.0)),
            layers=[CompositionLayer.from_dict(l) for l in d.get("layers", [])],
            captions=list(d.get("captions", [])),
            metadata=dict(d.get("metadata", {})),
            version=int(d.get("version", 1)),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "HyperframesComposition":
        return cls.from_dict(json.loads(json_str))
