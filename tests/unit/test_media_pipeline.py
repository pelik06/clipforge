import pytest
from pathlib import Path
import subprocess

from core.config.settings import Settings
from services.clipping.service import ClipRenderer
from services.reframing.service import Reframer
from services.qc.service import QualityController
from apps.worker.pipeline import run_media_pipeline


@pytest.fixture(scope="module")
def synthetic_video(tmp_path_factory):
    """Create a real synthetic 4-second MP4 video fixture using FFmpeg."""
    tmp_dir = tmp_path_factory.mktemp("media")
    video_path = tmp_dir / "test_synthetic.mp4"

    s = Settings()
    cmd = [
        s.ffmpeg_bin,
        "-y",
        "-f", "lavfi", "-i", "testsrc=duration=4:size=640x360:rate=25",
        "-f", "lavfi", "-i", "sine=frequency=1000:duration=4",
        "-c:v", "libx264",
        "-c:a", "aac",
        str(video_path),
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.returncode == 0
    assert video_path.exists()
    return video_path


def test_clip_renderer_success(synthetic_video, tmp_path):
    cr = ClipRenderer()
    out = tmp_path / "clip.mp4"
    result = cr.render(str(synthetic_video), 1.0, 3.0, str(out))
    assert Path(result).exists()
    assert Path(result).stat().st_size > 1024


def test_clip_renderer_invalid_timestamps(synthetic_video, tmp_path):
    cr = ClipRenderer()
    out = tmp_path / "clip.mp4"
    with pytest.raises(ValueError):
        cr.render(str(synthetic_video), -1.0, 3.0, str(out))
    with pytest.raises(ValueError):
        cr.render(str(synthetic_video), 3.0, 1.0, str(out))


def test_clip_renderer_missing_source(tmp_path):
    cr = ClipRenderer()
    out = tmp_path / "clip.mp4"
    with pytest.raises(FileNotFoundError):
        cr.render("nonexistent_video.mp4", 0.0, 2.0, str(out))


def test_reframer_vertical(synthetic_video, tmp_path):
    rf = Reframer()
    out = tmp_path / "vertical.mp4"
    result = rf.render_vertical(str(synthetic_video), str(out), width=720, height=1280)
    assert Path(result).exists()
    assert Path(result).stat().st_size > 1024


def test_quality_controller(synthetic_video, tmp_path):
    qc = QualityController()
    res = qc.check(str(synthetic_video))
    assert res.passed is True
    assert res.checks["file_exists"] is True
    assert res.checks["valid_container"] is True
    assert res.checks["video_stream"] is True
    assert res.checks["valid_duration"] is True

    # Missing file
    res_missing = qc.check(str(tmp_path / "missing.mp4"))
    assert res_missing.passed is False

    # Empty file
    empty_file = tmp_path / "empty.mp4"
    empty_file.write_bytes(b"")
    res_empty = qc.check(str(empty_file))
    assert res_empty.passed is False


def test_run_media_pipeline(synthetic_video, tmp_path):
    out_dir = tmp_path / "output"
    res = run_media_pipeline(str(synthetic_video), start=0.5, end=2.5, output_dir=str(out_dir), vertical=True)
    assert res.status == "completed"
    assert len(res.outputs) == 1
    final_clip = Path(res.outputs[0])
    assert final_clip.exists()
    assert final_clip.stat().st_size > 1024
