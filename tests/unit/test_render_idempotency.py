from pathlib import Path
import subprocess
import pytest
from core.config.settings import Settings
from services.render.job_manager import RenderJobManager
from services.render.models import RenderJobState
from services.render.worker import RENDER_VERSION, RenderWorker


def test_existing_artifact_reuse(tmp_path):
    s = Settings()
    source_media = tmp_path / "src_test.mp4"
    cmd = [
        s.ffmpeg_bin, "-y",
        "-f", "lavfi", "-i", "testsrc=duration=3:size=1080x1920:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=1000:duration=3",
        "-c:v", "libx264", "-c:a", "aac",
        str(source_media),
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    manager = RenderJobManager(concurrency=1, renders_dir=str(tmp_path / "renders"))

    # First render
    j1 = manager.submit_job(
        clip_id="c_idem_1",
        source_id=str(source_media),
        preset="tiktok",
        config={"duration": 3.0, "start_time": 0.0},
    )
    res1 = manager.process_queue_sync(1)[0]
    assert res1.status == RenderJobState.COMPLETED
    assert Path(res1.output_path).exists()
    out1_sha = res1.output_sha256

    # Second render with identical parameters -> should reuse existing artifact!
    j2 = manager.submit_job(
        clip_id="c_idem_1",
        source_id=str(source_media),
        preset="tiktok",
        config={"duration": 3.0, "start_time": 0.0},
    )
    res2 = manager.process_queue_sync(1)[0]
    assert res2.status == RenderJobState.COMPLETED
    assert "Reused existing verified render artifact" in res2.stage
    assert res2.output_sha256 == out1_sha
