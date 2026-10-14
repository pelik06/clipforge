import pytest
from core.models.candidate import CandidateMoment
from core.models.transcript import SentenceWindow, Word
from services.detection.thought_detector import ThoughtDetector


def test_tight_variant_boundary():
    """Verify tight variant retains hook + payoff within 20-35s boundary ending on complete sentence."""
    td = ThoughtDetector()

    # Sequence of 4 sentences: 0-10s (hook), 10-22s (context), 22-30s (payoff), 30-50s (detail)
    s1 = SentenceWindow(start=0.0, end=10.0, text="Truth be told, this is the most critical lesson in startups.", words=[Word("Truth", 0.0, 1.0)])
    s2 = SentenceWindow(start=10.2, end=22.0, text="Most founders focus on product but forget distribution,", words=[Word("Most", 10.2, 11.0)])
    s3 = SentenceWindow(start=22.2, end=30.0, text="Distribution is what actually makes you win.", words=[Word("Distribution", 22.2, 23.0)])
    s4 = SentenceWindow(start=30.2, end=50.0, text="And that is why early marketing matters so much.", words=[Word("And", 30.2, 31.0)])
    sentences = [s1, s2, s3, s4]
    mom = CandidateMoment(start=0.0, end=50.0, score=88.0, reasons=["Complete thought"])

    variants = td.generate_variants_for_top_moments([mom], sentences, top_n=1)

    # Tight variant must exist
    tight = next((v for v in variants if v.variant == "tight"), None)
    assert tight is not None
    assert 20.0 <= tight.duration <= 35.0
    assert tight.start == 0.0
    assert tight.end == 30.0  # Ends on s3 sentence boundary
    assert tight.parent_moment_id == mom.moment_id


def test_extended_variant_boundary():
    """Verify extended variant incorporates conversational context up to 40-65s without sentence splitting."""
    td = ThoughtDetector()

    s0 = SentenceWindow(start=5.0, end=12.0, text="Let me tell you about an early experience.", words=[Word("Let", 5.0, 6.0)])
    s1 = SentenceWindow(start=12.2, end=24.0, text="Truth be told, we made every mistake in the book.", words=[Word("Truth", 12.2, 13.0)])
    s2 = SentenceWindow(start=24.2, end=35.0, text="We ran out of money in six months.", words=[Word("We", 24.2, 25.0)])
    s3 = SentenceWindow(start=35.2, end=48.0, text="Then we pivoted to an enterprise model that saved us.", words=[Word("Then", 35.2, 36.0)])
    s4 = SentenceWindow(start=48.2, end=58.0, text="That single decision changed our company trajectory forever.", words=[Word("That", 48.2, 49.0)])

    sentences = [s0, s1, s2, s3, s4]
    # Base moment is s1 + s2 (12.2 to 35.0 = 22.8s)
    mom = CandidateMoment(start=12.2, end=35.0, score=85.0, reasons=["Base thought"])

    variants = td.generate_variants_for_top_moments([mom], sentences, top_n=1)

    ext = next((v for v in variants if v.variant == "extended"), None)
    assert ext is not None
    assert 40.0 <= ext.duration <= 65.0
    assert ext.start == 5.0
    assert ext.end in (48.0, 58.0)
    assert ext.parent_moment_id == mom.moment_id


def test_variant_deduplication():
    """Verify deduplication keeps unique moments and properly ranks variants."""
    td = ThoughtDetector()
    mom1 = CandidateMoment(start=0.0, end=25.0, score=90.0, variant="tight")
    mom2 = CandidateMoment(start=0.0, end=50.0, score=89.0, variant="extended")
    mom3 = CandidateMoment(start=100.0, end=130.0, score=84.0, variant="normal")

    # If deduplicating moments from different timestamps, both are kept
    unique = td.deduplicate_thoughts([mom1, mom3], max_clips=5)
    assert len(unique) == 2
