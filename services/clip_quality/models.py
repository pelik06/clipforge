from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class QualityBreakdown:
    semantic: float = 0.0            # max 35.0
    hook: float = 0.0                # max 15.0
    payoff: float = 0.0              # max 10.0
    information: float = 0.0         # max 10.0
    emotion: float = 0.0             # max 10.0
    speaker_framing: float = 0.0     # max 10.0
    caption: float = 0.0             # max 5.0
    duration_continuity: float = 0.0 # max 5.0
    total: float = 0.0               # max 100.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "semantic": round(self.semantic, 1),
            "hook": round(self.hook, 1),
            "payoff": round(self.payoff, 1),
            "information": round(self.information, 1),
            "emotion": round(self.emotion, 1),
            "speaker_framing": round(self.speaker_framing, 1),
            "caption": round(self.caption, 1),
            "duration_continuity": round(self.duration_continuity, 1),
            "total": round(self.total, 1),
        }


@dataclass
class ClipQualityFeatures:
    clip_id: str
    breakdown: QualityBreakdown
    reasons: List[str] = field(default_factory=list)
    penalties: List[str] = field(default_factory=list)
    raw_metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "clip_id": self.clip_id,
            "score": round(self.breakdown.total, 1),
            "breakdown": self.breakdown.to_dict(),
            "reasons": self.reasons,
            "penalties": self.penalties,
            "raw_metrics": self.raw_metrics,
        }
