from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class VisualCompositionEvaluation:
    visual_quality_score: float      # [0.0, 100.0]
    headroom_score: float            # [0.0, 100.0]
    face_size_score: float           # [0.0, 100.0]
    speaker_balance_score: float     # [0.0, 100.0]
    caption_collision: bool
    reasons: List[str] = field(default_factory=list)
    penalties: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "visual_quality_score": round(self.visual_quality_score, 1),
            "headroom_score": round(self.headroom_score, 1),
            "face_size_score": round(self.face_size_score, 1),
            "speaker_balance_score": round(self.speaker_balance_score, 1),
            "caption_collision": self.caption_collision,
            "reasons": self.reasons,
            "penalties": self.penalties,
        }
