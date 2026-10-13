from apps.worker.pipeline import run_mvp
import pytest


def test_pipeline_validation_error(tmp_path):
    fake_source = tmp_path / "nonexistent.mp4"
    with pytest.raises(FileNotFoundError):
        run_mvp(str(fake_source))


def test_pipeline_success(tmp_path):
    source = tmp_path / "sample_vod.mp4"
    source.write_bytes(b"fake video data")
    
    out_dir = tmp_path / "output"
    result = run_mvp(str(source), output_dir=str(out_dir))
    
    assert result.status == "completed"
    assert len(result.outputs) == 1
    assert "sample_vod_clip.mp4" in result.outputs[0]
