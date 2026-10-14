import pytest
import numpy as np

from services.audio_reaction.models import AudioReaction
from services.audio_reaction.detector import AudioReactionDetector
from services.detection.thought_detector import ThoughtDetector, ThoughtWindow
from core.models.transcript import SentenceWindow, Word


def test_audio_reaction_detection():
    """Verify audio reaction detector detects energy burst and assigns truthful high_energy_reaction label."""
    detector = AudioReactionDetector(sample_rate=16000)

    # 4 seconds of quiet background (RMS ~0.005)
    silence = np.random.normal(0, 0.005, 16000 * 4).astype(np.float32)
    # 1 second of high energy reaction burst (RMS ~0.15, > 2.2x ratio)
    burst = np.random.normal(0, 0.15, 16000 * 1).astype(np.float32)
    # 3 seconds of quiet background
    tail = np.random.normal(0, 0.005, 16000 * 3).astype(np.float32)

    pcm = np.concatenate([silence, burst, tail])
    reactions = detector.analyze(pcm)

    assert len(reactions) >= 1
    r = reactions[0]
    # Truthful label: no fake classifier claim
    assert r.label == "high_energy_reaction"
    assert 3.5 <= r.start <= 4.5
    assert r.confidence > 0.0
    assert r.score <= 10.0


def test_audio_reaction_scoring():
    """Verify audio reaction provides at most 10% boost and semantic quality stays dominant."""
    detector = AudioReactionDetector(max_score_contribution=10.0)
    reactions = [
        AudioReaction(start=10.0, end=12.0, label="high_energy_reaction", confidence=0.9),
    ]

    # Candidate window overlapping reaction [8.0 - 15.0]
    boost = detector.compute_reaction_boost(8.0, 15.0, reactions)
    assert 0.0 < boost <= 10.0
    assert boost == 9.0  # 0.9 * 10.0

    # Candidate window outside reaction [0.0 - 5.0]
    no_boost = detector.compute_reaction_boost(0.0, 5.0, reactions)
    assert no_boost == 0.0

    # Verify semantic quality dominance in ThoughtDetector
    td = ThoughtDetector()
    s = SentenceWindow(start=10.0, end=20.0, text="A thoughtful sentence here.", words=[Word("A", 10.0, 10.5)])
    tw = ThoughtWindow(start=10.0, end=20.0, text=s.text, words=s.words, sentences=[s])

    score_without = td.score_thought_window(tw, audio_reactions=[])
    score_with = td.score_thought_window(tw, audio_reactions=reactions)

    # Reaction score increases score by at most 10 points without overwhelming semantic base
    assert score_with >= score_without
    assert (score_with - score_without) <= 10.0
