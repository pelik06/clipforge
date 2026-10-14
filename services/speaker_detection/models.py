from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SpeechSegment:
    start: float
    end: float
    confidence: float = 1.0


@dataclass
class MouthActivity:
    track_id: int
    start: float
    end: float
    score: float


@dataclass
class SpeakerSegment:
    start: float
    end: float
    track_id: int
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start": round(self.start, 2),
            "end": round(self.end, 2),
            "track_id": f"face_{self.track_id:02d}",
            "confidence": round(self.confidence, 3),
        }


@dataclass
class SpeakerTimeline:
    segments: List[SpeakerSegment] = field(default_factory=list)
    active_tracks: List[int] = field(default_factory=list)
    speaker_mode: str = "active_speaker"  # "active_speaker" or "fallback_tracking"
    fallback_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "speaker_mode": self.speaker_mode,
            "fallback_reason": self.fallback_reason,
            "active_tracks": self.active_tracks,
            "segments": [s.to_dict() for s in self.segments],
        }


@dataclass
class SpeakerDetectorConfig:
    speech_weight: float = 0.45
    mouth_weight: float = 0.30
    face_weight: float = 0.15
    temporal_weight: float = 0.10
    switch_margin: float = 0.12
    switch_confirmation_frames: int = 5
    min_active_speaker_duration: float = 0.5
    min_confidence_threshold: float = 0.35
