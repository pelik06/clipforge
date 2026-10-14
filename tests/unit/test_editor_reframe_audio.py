import pytest
from services.editor.models import AudioConfig, CropConfig, EditorState
from services.editor.operations import EditorOperations


def test_auto_reframe_mode():
    state = EditorState(
        clip_id="c_ref_auto",
        source_id="v.mp4",
        source_duration=50.0,
        source_start=0.0,
        source_end=20.0,
    )
    assert state.crop.mode == "auto"


def test_manual_reframe_mode():
    state = EditorState(
        clip_id="c_ref_man",
        source_id="v.mp4",
        source_duration=50.0,
        source_start=0.0,
        source_end=20.0,
    )
    # Override crop manually: X=0.25, Y=0.10, Scale=1.25
    overridden = EditorOperations.set_crop(state, x=0.25, y=0.10, width=0.8, height=0.9, scale=1.25, mode="manual")
    assert overridden.crop.mode == "manual"
    assert overridden.crop.x == 0.25
    assert overridden.crop.y == 0.10
    assert overridden.crop.scale == 1.25
    assert "crop" in overridden.user_overrides


def test_crop_validation():
    state = EditorState(
        clip_id="c_crop_err",
        source_id="v.mp4",
        source_duration=50.0,
        source_start=0.0,
        source_end=20.0,
    )
    # Negative scale should raise ValueError
    with pytest.raises(ValueError, match="strictly positive"):
        EditorOperations.set_crop(state, x=0.0, y=0.0, width=1.0, height=1.0, scale=-0.5)

    # Invalid mode
    with pytest.raises(ValueError, match="Invalid crop mode"):
        EditorOperations.set_crop(state, x=0.0, y=0.0, width=1.0, height=1.0, mode="random_mode")


def test_layout_override():
    state = EditorState(
        clip_id="c_lay",
        source_id="v.mp4",
        source_duration=50.0,
        source_start=0.0,
        source_end=20.0,
    )
    assert state.layout == "AUTO"

    s_track = EditorOperations.set_layout(state, "TRACK")
    assert s_track.layout == "TRACK"

    s_split = EditorOperations.set_layout(state, "SPLIT")
    assert s_split.layout == "SPLIT"

    with pytest.raises(ValueError, match="Invalid layout mode"):
        EditorOperations.set_layout(state, "INVALID_LAYOUT")


def test_audio_volume_and_mute():
    state = EditorState(
        clip_id="c_aud",
        source_id="v.mp4",
        source_duration=50.0,
        source_start=0.0,
        source_end=20.0,
    )
    assert state.audio.volume == 1.0
    assert state.audio.mute is False

    # Set volume 1.5 (150%)
    s_vol = EditorOperations.set_audio(state, volume=1.5)
    assert s_vol.audio.volume == 1.5

    # Set mute
    s_mute = EditorOperations.set_audio(state, mute=True)
    assert s_mute.audio.mute is True


def test_audio_validation():
    state = EditorState(
        clip_id="c_aud_err",
        source_id="v.mp4",
        source_duration=50.0,
        source_start=0.0,
        source_end=20.0,
    )
    # Volume > 2.0 should raise ValueError
    with pytest.raises(ValueError, match="out of range"):
        EditorOperations.set_audio(state, volume=3.5)

    # Volume < 0.0 should raise ValueError
    with pytest.raises(ValueError, match="out of range"):
        EditorOperations.set_audio(state, volume=-0.1)
