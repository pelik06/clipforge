import pytest
from services.clip_quality import ClipQualityAnalyzer
from services.clip_quality.audio_score import AudioReactionScorer
from services.clip_quality.semantic_score import SemanticScorer


def test_hook_score():
    scorer = SemanticScorer()

    # Question hook + numbers -> high hook score
    score1, reasons1 = scorer.evaluate_hook_strength("Kenapa 90% orang gagal di tahun pertama?")
    assert score1 >= 10.0
    assert any("question" in r.lower() for r in reasons1)

    # Curiosity keyword
    score2, reasons2 = scorer.evaluate_hook_strength("Inilah rahasia terbesar yang tidak pernah diceritakan.")
    assert score2 >= 9.0

    # Weak filler opening
    score3, reasons3 = scorer.evaluate_hook_strength("Terus ya kita kan cuma...")
    assert score3 < score1


def test_payoff_score():
    scorer = SemanticScorer()

    # Clear conclusion payoff marker
    text_with_payoff = "Kita coba cari tahu penyebabnya. Dan akhirnya solusinya adalah konsistensi setiap hari."
    score1, reasons1, penalties1 = scorer.evaluate_payoff(text_with_payoff, ["Kita coba cari tahu penyebabnya.", "Dan akhirnya solusinya adalah konsistensi setiap hari."])
    assert score1 >= 8.0
    assert any("payoff" in r.lower() or "conclusion" in r.lower() for r in reasons1)

    # Incomplete text without payoff
    text_no_payoff = "Jadi pas gue buka pintu, tiba-tiba ada orang"
    score2, reasons2, penalties2 = scorer.evaluate_payoff(text_no_payoff, ["Jadi pas gue buka pintu, tiba-tiba ada orang"])
    assert score2 <= 5.0
    assert len(penalties2) > 0


def test_semantic_score():
    scorer = SemanticScorer()

    # Clean sentence with terminal punctuation
    good_text = "Strategi terbaik adalah membangun kebiasaan membaca setiap pagi."
    score1, reasons1, penalties1 = scorer.evaluate_semantic_quality(good_text, duration=15.0)
    assert score1 >= 25.0
    assert len(penalties1) == 0

    # Cut off with trailing conjunction
    bad_text = "Semua orang sudah setuju bahwa"
    score2, reasons2, penalties2 = scorer.evaluate_semantic_quality(bad_text, duration=5.0)
    assert score2 < score1
    assert any("dangling" in p.lower() for p in penalties2)


def test_audio_score_limit():
    scorer = AudioReactionScorer()

    class MockReaction:
        start = 2.0
        end = 4.0
        confidence = 0.99
        label = "high_energy_reaction"

    # Loud reaction should contribute, but strictly <= 10.0
    score, reasons = scorer.evaluate_audio_emotion([MockReaction()], clip_start=0.0, clip_end=10.0)
    assert score <= 10.0
    assert score >= 7.0

    # Empty reaction baseline
    score_empty, _ = scorer.evaluate_audio_emotion([], clip_start=0.0, clip_end=10.0)
    assert score_empty == 4.0


def test_composite_score():
    analyzer = ClipQualityAnalyzer()

    # Well-crafted complete thought
    text = "Kenapa 90% kreator menyerah di 3 bulan pertama? Masalah terbesarnya adalah ekspektasi yang keliru. Dan solusinya adalah fokus pada proses."
    sents = [
        "Kenapa 90% kreator menyerah di 3 bulan pertama?",
        "Masalah terbesarnya adalah ekspektasi yang keliru.",
        "Dan solusinya adalah fokus pada proses.",
    ]
    feat = analyzer.analyze_clip(
        clip_id="c_test",
        text=text,
        duration=28.0,
        sentences=sents,
        active_speaker_confidence=0.92,
        layout_mode="TRACK",
    )

    assert feat.breakdown.total >= 75.0
    assert feat.breakdown.semantic <= 35.0
    assert feat.breakdown.hook <= 15.0
    assert feat.breakdown.payoff <= 10.0
    assert feat.breakdown.emotion <= 10.0
    assert feat.breakdown.speaker_framing <= 10.0
    assert feat.breakdown.caption <= 5.0
    assert feat.breakdown.duration_continuity <= 5.0
    assert len(feat.reasons) > 0
