import pytest
from core.models.transcript import Word
from services.boundary_refinement import SentenceBoundaryAnalyzer, SmartBoundaryRefiner
from services.detection.thought_detector import SentenceWindow


def test_sentence_boundary():
    analyzer = SentenceBoundaryAnalyzer()
    res = analyzer.evaluate("Ini adalah strategi pemasaran terbaik di tahun 2026.")
    assert res.is_clean_start is True
    assert res.is_clean_end is True
    assert res.start_penalty == 0.0
    assert res.end_penalty == 0.0


def test_incomplete_start():
    analyzer = SentenceBoundaryAnalyzer()
    res = analyzer.evaluate("terus gue bilang ke dia jangan pernah menyerah.")
    assert res.is_clean_start is False
    assert res.dangling_start_word == "terus"
    assert res.start_penalty > 0.0


def test_incomplete_end():
    analyzer = SentenceBoundaryAnalyzer()
    res = analyzer.evaluate("Semua orang sebenarnya setuju karena")
    assert res.is_clean_end is False
    assert res.dangling_end_word == "karena"
    assert res.end_penalty > 0.0


def test_pause_expansion():
    refiner = SmartBoundaryRefiner(max_start_expansion=2.0, max_end_expansion=3.0)
    words = [
        Word(text="Dan", start=1.0, end=1.3),
        Word(text="inilah", start=1.35, end=1.8),
        Word(text="strateginya.", start=1.85, end=2.5),
        Word(text="Kalian", start=3.5, end=4.0), # Pause between 2.5 and 3.5 (1.0s gap)
    ]
    # Candidate ends at 2.8s (inside silence valley) -> snap should align cleanly
    b_res = refiner.refine(candidate_start=1.0, candidate_end=2.8, words=words, min_duration=1.0)
    # Starts on "Dan" -> dangling trimmed, snaps to "inilah" at 1.35s
    assert b_res.refined_start >= 1.30
    assert "TRIMMED_DANGLING_START" in b_res.boundary_flags


def test_max_expansion():
    refiner = SmartBoundaryRefiner(max_start_expansion=2.0, max_end_expansion=3.0)
    sentences = [
        SentenceWindow(start=10.0, end=20.0, text="Kalimat pembuka yang sangat panjang."),
        SentenceWindow(start=20.5, end=35.0, text="Kalimat kedua yang sangat lengkap penjelasannya."),
    ]
    # Candidate starts at 15.0s (5s after sentence start) -> exceeds max_start_expansion=2.0s -> cannot expand all 5s back
    b_res = refiner.refine(candidate_start=15.0, candidate_end=25.0, sentences=sentences, min_duration=5.0)
    assert (15.0 - b_res.refined_start) <= 2.01
