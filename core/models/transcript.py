from dataclasses import dataclass


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
    words: list[Word]
