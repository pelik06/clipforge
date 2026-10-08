from dataclasses import dataclass, field


@dataclass
class CandidateMoment:
    start: float
    end: float
    score: float = 0.0
    reasons: list[str] = field(default_factory=list)
    signals: dict[str, float] = field(default_factory=dict)

    @property
    def duration(self) -> float:
        return self.end - self.start
