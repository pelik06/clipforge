import pytest
from services.render.models import RenderJobState
from services.render.progress import RenderProgressTracker


def test_progress_monotonic():
    tracker = RenderProgressTracker()
    assert tracker.progress == 0.0

    p1 = tracker.update(RenderJobState.PREPARING, 0.5)
    assert p1 > 0.0

    p2 = tracker.update(RenderJobState.RENDERING, 0.5)
    assert p2 > p1

    # Attempting to feed a lower fraction should not regress progress
    p_stale = tracker.update(RenderJobState.RENDERING, 0.1)
    assert p_stale == p2

    p_final = tracker.complete()
    assert p_final == 100.0


def test_stage_transition():
    tracker = RenderProgressTracker()
    prep = tracker.update(RenderJobState.PREPARING, 1.0)
    assert prep <= 5.0

    rend = tracker.update(RenderJobState.RENDERING, 0.5)
    assert 5.0 <= rend <= 90.0

    val = tracker.update(RenderJobState.VALIDATING, 0.5)
    assert 90.0 <= val <= 99.0
