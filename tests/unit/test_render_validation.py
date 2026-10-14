from pathlib import Path
import subprocess
import pytest
from core.config.settings import Settings
from services.render.validator import RenderValidator


def test_valid_mp4(tmp_path):
    s = Settings()
    test_media = tmp_path / "valid_render.mp4"
    cmd = [
        s.ffmpeg_bin, "-y",
        "-f", "lavfi", "-i", "testsrc=duration=3:size=1080x1920:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=1000:duration=3",
        "-c:v", "libx264", "-c:a", "aac",
        str(test_media),
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    validator = RenderValidator(duration_tolerance_sec=0.15)
    res = validator.validate(str(test_media), expected_duration=3.0, expected_width=1080, expected_height=1920)
    assert res.is_valid is True
    assert res.sha256 is not None
    assert len(res.errors) == 0


def test_wrong_resolution(tmp_path):
    s = Settings()
    test_media = tmp_path / "wrong_res.mp4"
    cmd = [
        s.ffmpeg_bin, "-y",
        "-f", "lavfi", "-i", "testsrc=duration=2:size=720x1280:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=1000:duration=2",
        "-c:v", "libx264", "-c:a", "aac",
        str(test_media),
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    validator = RenderValidator()
    # Expect 1080x1920, but file is 720x1280
    res = validator.validate(str(test_media), expected_width=1080, expected_height=1920)
    assert res.is_valid is False
    assert any("Width mismatch" in e for e in res.errors)


def test_duration_tolerance(tmp_path):
    s = Settings()
    test_media = tmp_path / "dur_test.mp4"
    cmd = [
        s.ffmpeg_bin, "-y",
        "-f", "lavfi", "-i", "testsrc=duration=5:size=1080x1920:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=1000:duration=5",
        "-c:v", "libx264", "-c:a", "aac",
        str(test_media),
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    validator = RenderValidator(duration_tolerance_sec=0.15)
    # Expected 5.0s -> actual ~5.0s -> within tolerance -> PASS
    res_pass = validator.validate(str(test_media), expected_duration=5.0)
    assert res_pass.is_valid is True

    # Expected 4.0s -> actual ~5.0s -> error 1.0s > 0.15s -> FAIL
    res_fail = validator.validate(str(test_media), expected_duration=4.0)
    assert res_fail.is_valid is False
    assert any("Duration error" in e for e in res_fail.errors)
