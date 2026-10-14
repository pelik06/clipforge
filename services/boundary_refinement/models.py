from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BoundaryEvaluation:
    is_clean_start: bool
    is_clean_end: bool
    dangling_start_word: Optional[str] = None
    dangling_end_word: Optional[str] = None
    start_penalty: float = 0.0
    end_penalty: float = 0.0
    reasons: List[str] = field(default_factory=list)


@dataclass
class RefinedBoundary:
    original_start: float
    original_end: float
    refined_start: float
    refined_end: float
    duration: float
    start_adjustment: float
    end_adjustment: float
    reasons: List[str] = field(default_factory=list)
    boundary_flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_start": round(self.original_start, 2),
            "original_end": round(self.original_end, 2),
            "refined_start": round(self.refined_start, 2),
            "refined_end": round(self.refined_end, 2),
            "duration": round(self.duration, 2),
            "start_adjustment": round(self.start_adjustment, 2),
            "end_adjustment": round(self.end_adjustment, 2),
            "reasons": self.reasons,
            "boundary_flags": self.boundary_flags,
        }
