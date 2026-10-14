import pytest
from services.render.models import RenderJob, RenderJobState
from services.render.queue import RenderQueue


def test_queue_order():
    q = RenderQueue()
    j1 = RenderJob(id="j1", clip_id="c1", source_id="s.mp4", created_at="2026-10-14T10:00:00", priority=10)
    j2 = RenderJob(id="j2", clip_id="c2", source_id="s.mp4", created_at="2026-10-14T10:01:00", priority=10)

    q.enqueue(j1)
    q.enqueue(j2)

    # FIFO when same priority
    pop1 = q.dequeue()
    pop2 = q.dequeue()
    assert pop1.id == "j1"
    assert pop2.id == "j2"


def test_concurrency_limit():
    q = RenderQueue()
    for i in range(5):
        q.enqueue(RenderJob(id=f"job_{i}", clip_id=f"c_{i}", source_id="s.mp4"))

    assert q.size() == 5
    # Process only 2 jobs (simulating concurrency limit = 2)
    active = [q.dequeue() for _ in range(2)]
    assert len(active) == 2
    assert q.size() == 3


def test_priority():
    q = RenderQueue()
    j_low = RenderJob(id="low", clip_id="c_low", source_id="s.mp4", priority=5)
    j_high = RenderJob(id="high", clip_id="c_high", source_id="s.mp4", priority=20)

    q.enqueue(j_low)
    q.enqueue(j_high)

    # High priority job must dequeue first
    first = q.dequeue()
    assert first.id == "high"
    second = q.dequeue()
    assert second.id == "low"
