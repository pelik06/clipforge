import pytest
from core.models.configuration import JobConfig
from core.models.transcript import TranscriptSegment, Word
from services.captions.service import (
    CaptionRenderer,
    group_words_into_adaptive_chunks,
)


def test_line_balance():
    # Long words exceeding 24 characters total -> should balance into 2 chunks
    words = [
        Word(text="Rencana", start=0.0, end=0.8),
        Word(text="strategi", start=0.85, end=1.6),
        Word(text="eksekusi", start=1.65, end=2.3),
        Word(text="bisnis", start=2.35, end=3.0),
    ]
    chunks = group_words_into_adaptive_chunks(words, words_per_group=4)
    # Balanced into 2 chunks rather than 1 overly wide 4-word chunk
    assert len(chunks) == 2
    assert len(chunks[0]) == 2
    assert len(chunks[1]) == 2


def test_orphan_word():
    # 5 words: normally 4 + 1 (leaving "hebat" as an awkward 1-word orphan).
    # Rebalancer should adjust to 3 + 2!
    words = [
        Word(text="Saya", start=0.0, end=0.3),
        Word(text="pikir", start=0.35, end=0.6),
        Word(text="ini", start=0.65, end=0.9),
        Word(text="sangat", start=0.95, end=1.2),
        Word(text="hebat", start=1.25, end=1.6),
    ]
    chunks = group_words_into_adaptive_chunks(words, words_per_group=4)
    assert len(chunks) == 2
    assert len(chunks[0]) == 3
    assert len(chunks[1]) == 2
    assert chunks[1][-1].text == "hebat"


def test_punctuation_reset():
    cr = CaptionRenderer()
    words = [
        Word(text="Keren.", start=0.1, end=0.8),
        Word(text="Lanjut", start=0.85, end=1.5),
    ]
    seg = [TranscriptSegment(text="Keren. Lanjut", start=0.1, end=1.5, words=words)]
    ass_text = cr.generate_ass_script(seg, JobConfig(caption_preset="karaoke"))
    # Word with dot should trigger {\rDefault} reset
    assert "{\\rDefault}" in ass_text or "Keren." in ass_text
