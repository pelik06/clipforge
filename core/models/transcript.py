from dataclasses import dataclass, field
from typing import List


@dataclass
class Word:
    text: str
    start: float
    end: float


@dataclass
class TranscriptSegment:
    text: str
    start: float
    end: float
    words: List[Word] = field(default_factory=list)


@dataclass
class SentenceWindow:
    start: float
    end: float
    text: str
    words: List[Word] = field(default_factory=list)
    confidence: float = 1.0

    @property
    def duration(self) -> float:
        return max(0.0, round(self.end - self.start, 3))


@dataclass
class ThoughtWindow:
    sentences: List[SentenceWindow] = field(default_factory=list)
    start: float = 0.0
    end: float = 0.0
    text: str = ""
    words: List[Word] = field(default_factory=list)
    hook_text: str = ""
    payoff_text: str = ""
    has_hook: bool = False
    has_payoff: bool = False

    @property
    def duration(self) -> float:
        return max(0.0, round(self.end - self.start, 3))
