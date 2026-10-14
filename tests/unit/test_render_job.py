import pytest
from services.render.models import RenderJob, RenderJobState


def test_job_creation():
    job = RenderJob(id="rj_01", clip_id="c_01", source_id="data/input/sample.mp4", preset="tiktok")
    assert job.id == "rj_01"
    assert job.status == RenderJobState.QUEUED
    assert job.progress == 0.0
    assert job.preset == "tiktok"
    assert job.render_type == "final"


def test_job_state_transition():
    job = RenderJob(id="rj_02", clip_id="c_02", source_id="data/input/sample.mp4")
    # Valid transition: QUEUED -> PREPARING
    job.transition_to(RenderJobState.PREPARING, "Preparing assets")
    assert job.status == RenderJobState.PREPARING
    assert job.stage == "Preparing assets"

    # PREPARING -> RENDERING
    job.transition_to(RenderJobState.RENDERING, "Encoding video")
    assert job.status == RenderJobState.RENDERING

    # RENDERING -> VALIDATING
    job.transition_to(RenderJobState.VALIDATING, "Validating output")
    assert job.status == RenderJobState.VALIDATING

    # VALIDATING -> COMPLETED
    job.transition_to(RenderJobState.COMPLETED, "Done")
    assert job.status == RenderJobState.COMPLETED


def test_invalid_transition():
    job = RenderJob(id="rj_03", clip_id="c_03", source_id="data/input/sample.mp4")
    job.status = RenderJobState.COMPLETED

    # COMPLETED is terminal -> cannot transition to RENDERING
    with pytest.raises(ValueError, match="Invalid state transition"):
        job.transition_to(RenderJobState.RENDERING)
