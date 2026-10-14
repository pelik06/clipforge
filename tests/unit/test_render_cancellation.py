from pathlib import Path
import pytest
from services.render.cancellation import RenderCancellationManager
from services.render.models import RenderJob, RenderJobState
from services.render.queue import RenderQueue


def test_cancel_queued():
    q = RenderQueue()
    job = RenderJob(id="job_q", clip_id="c1", source_id="s.mp4")
    q.enqueue(job)
    assert q.size() == 1

    ok = q.cancel("job_q")
    assert ok is True
    assert q.size() == 0
    assert job.status == RenderJobState.CANCELLED


def test_partial_cleanup(tmp_path):
    mgr = RenderCancellationManager()
    partial_file = tmp_path / "partial_test.mp4"
    partial_file.write_bytes(b"corrupt partial bytes")
    assert partial_file.exists()

    mgr.cancel_job("running_job_1", partial_output_path=str(partial_file))
    assert not partial_file.exists()
    assert mgr.is_cancelled("running_job_1") is True
