from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class AudioReaction:
    start: float
    end: float
    label: str  # "high_energy_reaction", "laughter", "applause", "cheering"
    confidence: float
    score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start": round(self.start, 2),
            "end": round(self.end, 2),
            "duration": round(self.end - self.start, 2),
            "label": self.label,
            "confidence": round(self.confidence, 3),
            "score": round(self.score, 3),
        }
