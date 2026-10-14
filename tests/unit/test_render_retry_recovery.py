from pathlib import Path
import pytest
from core.storage import get_render_job, save_render_job
from services.render.models import RenderJob, RenderJobState
from services.render.recovery import recover_stale_jobs
from services.render.retry import RenderRetryManager


def test_transient_retry():
    mgr = RenderRetryManager(max_retries=2)
    err = RuntimeError("Temporary pipe closed by worker")
    assert mgr.is_transient_error(err) is True
    assert mgr.should_retry(err, current_retry_count=0) is True
    assert mgr.should_retry(err, current_retry_count=1) is True
    assert mgr.should_retry(err, current_retry_count=2) is False


def test_permanent_error_no_retry():
    mgr = RenderRetryManager(max_retries=2)
    err = FileNotFoundError("Missing source file")
    assert mgr.is_transient_error(err) is False
    assert mgr.should_retry(err, current_retry_count=0) is False

    err2 = ValueError("Unknown export preset '8k_super'")
    assert mgr.should_retry(err2, current_retry_count=0) is False


def test_max_retry():
    mgr = RenderRetryManager(max_retries=2)
    backoff0 = mgr.compute_backoff_sec(0)
    backoff1 = mgr.compute_backoff_sec(1)
    assert backoff0 == 1.0
    assert backoff1 == 2.0


def test_stale_job_recovery(tmp_path):
    db_file = tmp_path / "test_recovery.db"
    # Seed a job stuck in RENDERING
    job = {
        "id": "stale_01",
        "clip_id": "c_stale",
        "source_id": "s.mp4",
        "status": RenderJobState.RENDERING.value,
        "stage": "Rendering via FFmpeg",
        "progress": 45.0,
        "preset": "tiktok",
        "render_type": "final",
        "retry_count": 0,
        "priority": 10,
        "config": {},
    }
    save_render_job(job, db_path=db_file)

    recovered = recover_stale_jobs(db_path=db_file, max_retries=2)
    assert len(recovered) == 1
    assert recovered[0]["status"] == RenderJobState.RETRYING.value
    assert recovered[0]["retry_count"] == 1

    # If retries exceeded, it transitions to FAILED
    recovered[0]["status"] = RenderJobState.RENDERING.value
    recovered[0]["retry_count"] = 2
    save_render_job(recovered[0], db_path=db_file)

    recovered_failed = recover_stale_jobs(db_path=db_file, max_retries=2)
    assert len(recovered_failed) == 1
    assert recovered_failed[0]["status"] == RenderJobState.FAILED.value
