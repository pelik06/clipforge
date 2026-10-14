import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CandidateMoment:
    start: float
    end: float
    score: float = 0.0
    reasons: List[str] = field(default_factory=list)
    signals: Dict[str, float] = field(default_factory=dict)
    moment_id: str = field(default_factory=lambda: f"mom_{uuid.uuid4().hex[:8]}")
    rank: int = 1
    source_start: float = 0.0
    source_end: float = 0.0
    output_path: Optional[str] = None
    status: str = "detected"
    variant: str = "normal"
    parent_moment_id: Optional[str] = None
    def __post_init__(self):
        if not self.source_start:
            self.source_start = self.start
        if not self.source_end:
            self.source_end = self.end

    @property
    def duration(self) -> float:
        return max(0.0, round(self.end - self.start, 3))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "moment_id": self.moment_id,
            "rank": self.rank,
            "source_start": round(self.source_start, 2),
            "source_end": round(self.source_end, 2),
            "start": round(self.start, 2),
            "end": round(self.end, 2),
            "duration": self.duration,
            "score": round(self.score, 3),
            "reasons": self.reasons,
            "signals": self.signals,
            "output_path": self.output_path,
            "status": self.status,
            "variant": self.variant,
            "parent_moment_id": self.parent_moment_id,
        }
