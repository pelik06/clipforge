import pytest
from core.models.transcript import Word
from services.captions.safe_area import CaptionSafeAreaManager
from services.captions.service import (
    CaptionRenderer,
    group_words_into_adaptive_chunks,
    is_emphasis_word,
)


def test_adaptive_chunking():
    # 4 words with punctuation on word 2 -> should split adaptively
    words = [
        Word(text="Halo", start=0.0, end=0.4),
        Word(text="kawan!", start=0.45, end=0.8),
        Word(text="Ini", start=0.85, end=1.1),
        Word(text="adalah", start=1.15, end=1.4),
        Word(text="contoh", start=1.45, end=1.8),
    ]
    chunks = group_words_into_adaptive_chunks(words, words_per_group=4, min_words_per_group=1)
    # First chunk should break on punctuation "kawan!"
    assert len(chunks) >= 2
    assert chunks[0][-1].text == "kawan!"


def test_sentence_boundary():
    # Sentence ending with dot should force chunk break
    words = [
        Word(text="Pertama.", start=0.0, end=0.5),
        Word(text="Kedua", start=0.6, end=1.0),
        Word(text="ketiga", start=1.1, end=1.5),
    ]
    chunks = group_words_into_adaptive_chunks(words, words_per_group=4, min_words_per_group=1)
    assert chunks[0][0].text == "Pertama."
    assert len(chunks[0]) == 1


def test_caption_safe_area():
    mgr = CaptionSafeAreaManager()

    # Face in bottom zone (y: 1500, h: 200 -> overlaps 1450-1820)
    face_boxes = [(400.0, 1500.0, 250.0, 200.0)]
    res = mgr.resolve_caption_position(face_boxes, preferred_position="bottom_safe")
    assert res.collision_avoided is True
    assert res.target_alignment == 8  # moved to top safe area


def test_face_collision():
    mgr = CaptionSafeAreaManager()

    # Face high up (y: 300, h: 300 -> does NOT overlap bottom 1450-1820)
    face_boxes = [(400.0, 300.0, 250.0, 300.0)]
    collision = mgr.check_face_collision(face_boxes, preferred_position="bottom_safe")
    assert collision is False

    res = mgr.resolve_caption_position(face_boxes, preferred_position="bottom_safe")
    assert res.collision_avoided is False
    assert res.target_alignment == 2  # stays at bottom safe area


def test_caption_hysteresis():
    mgr = CaptionSafeAreaManager(hysteresis_seconds=1.5)

    # Explicit top_safe should stay top_safe
    res = mgr.resolve_caption_position([], preferred_position="top_safe")
    assert res.target_alignment == 8

    # Explicit center should stay center
    res_center = mgr.resolve_caption_position([], preferred_position="center")
    assert res_center.target_alignment == 5
