from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class TopicFamily:
    family_id: str
    topic_label: str
    keywords: List[str] = field(default_factory=list)
    members: List[str] = field(default_factory=list)
    avg_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "family_id": self.family_id,
            "topic_label": self.topic_label,
            "keywords": self.keywords,
            "members": self.members,
            "avg_score": round(self.avg_score, 1),
        }
