import pytest
from services.render.models import ExportPresetConfig, RenderPreset
from services.render.presets import get_preset_config


def test_tiktok_preset():
    cfg = get_preset_config("tiktok")
    assert cfg.width == 1080
    assert cfg.height == 1920
    assert cfg.fps == 30
    assert cfg.audio_normalize is True


def test_high_quality_preset():
    cfg = get_preset_config("high_quality")
    assert cfg.width == 1080
    assert cfg.height == 1920
    assert cfg.video_bitrate == "8000k"
    assert cfg.crf == 18


def test_draft_preset():
    cfg = get_preset_config("draft")
    assert cfg.width == 720
    assert cfg.height == 1280
    assert cfg.ffmpeg_preset == "veryfast"


def test_invalid_config():
    with pytest.raises(ValueError, match="Unknown export preset"):
        get_preset_config("ultra_vr_4d")

    # Invalid odd dimensions for H.264
    invalid_odd = ExportPresetConfig(name="odd", width=1081, height=1920)
    with pytest.raises(ValueError, match="Dimensions must be even"):
        invalid_odd.validate()
