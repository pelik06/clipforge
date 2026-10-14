from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SentenceRole(str, Enum):
    HOOK = "HOOK"
    BRIDGE = "BRIDGE"
    CONTENT = "CONTENT"
    PAYOFF = "PAYOFF"
    FILLER = "FILLER"


@dataclass
class SentenceAnalysis:
    text: str
    role: SentenceRole
    confidence: float
    reason: str


@dataclass
class ContextEvaluation:
    context_score: float             # [0.0, 100.0]
    context_completeness: float      # [0.0, 1.0]
    has_unresolved_pronoun: bool
    unresolved_references: List[str] = field(default_factory=list)
    bridge_count: int = 0
    bridge_sentences: List[str] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)
    penalties: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_score": round(self.context_score, 1),
            "context_completeness": round(self.context_completeness, 2),
            "has_unresolved_pronoun": self.has_unresolved_pronoun,
            "unresolved_references": self.unresolved_references,
            "bridge_count": self.bridge_count,
            "bridge_sentences": self.bridge_sentences,
            "reasons": self.reasons,
            "penalties": self.penalties,
        }
