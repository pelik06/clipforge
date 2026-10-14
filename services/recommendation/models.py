from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RecommendationItem:
    clip_id: str
    rank: int
    score: float
    is_recommended: bool
    reasons: List[str] = field(default_factory=list)
    variant: str = "normal"
    speaker: str = "face_01"
    layout: str = "TRACK"
    duration: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "clip_id": self.clip_id,
            "rank": self.rank,
            "score": round(self.score, 1),
            "is_recommended": self.is_recommended,
            "reasons": self.reasons,
            "variant": self.variant,
            "speaker": self.speaker,
            "layout": self.layout,
            "duration": round(self.duration, 1),
        }
