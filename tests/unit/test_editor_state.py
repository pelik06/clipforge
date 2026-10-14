import pytest
from services.editor.models import (
    AudioConfig,
    CaptionSegment,
    CropConfig,
    EditorState,
    EditorStatus,
)
from services.editor.validation import EditorValidator


def test_create_state():
    state = EditorState(
        clip_id="c_001",
        source_id="data/input/real_talk_35s.mp4",
        source_duration=35.0,
        source_start=5.0,
        source_end=25.0,
    )
    assert state.clip_id == "c_001"
    assert state.clip_duration == 20.0
    assert state.editor_version == 1
    assert state.status == EditorStatus.DRAFT
    assert state.audio.volume == 1.0


def test_serialize_state():
    state = EditorState(
        clip_id="c_002",
        source_id="sample.mp4",
        source_duration=60.0,
        source_start=10.0,
        source_end=40.0,
        layout="TRACK",
    )
    d = state.to_dict()
    assert d["clip_id"] == "c_002"
    assert d["source_start"] == 10.0
    assert d["source_end"] == 40.0
    assert d["clip_duration"] == 30.0
    assert d["layout"] == "TRACK"
    assert "crop" in d
    assert "audio" in d


def test_deserialize_state():
    raw_dict = {
        "clip_id": "c_003",
        "source_id": "vod.mp4",
        "source_duration": 120.0,
        "source_start": 15.0,
        "source_end": 45.0,
        "layout": "SPLIT",
        "crop": {"x": 0.1, "y": 0.2, "width": 0.8, "height": 0.7, "scale": 1.2, "mode": "manual"},
        "audio": {"volume": 1.5, "mute": False},
        "captions": [
            {"id": "cap_1", "start": 0.0, "end": 2.5, "text": "Hello world"}
        ],
        "editor_version": 3,
        "status": "APPROVED",
    }
    state = EditorState.from_dict(raw_dict)
    assert state.clip_id == "c_003"
    assert state.layout == "SPLIT"
    assert state.crop.mode == "manual"
    assert state.crop.scale == 1.2
    assert state.audio.volume == 1.5
    assert len(state.captions) == 1
    assert state.captions[0].text == "Hello world"
    assert state.editor_version == 3
    assert state.status == EditorStatus.APPROVED


def test_state_validation():
    state = EditorState(
        clip_id="c_004",
        source_id="v.mp4",
        source_duration=100.0,
        source_start=10.0,
        source_end=25.0,
        captions=[CaptionSegment(id="1", start=0.0, end=5.0, text="Valid text")],
    )
    # Should pass without raising
    EditorValidator.validate_all(state)


def test_invalid_state_rejection():
    # start >= end
    invalid_timeline = EditorState(
        clip_id="c_005",
        source_id="v.mp4",
        source_duration=50.0,
        source_start=30.0,
        source_end=10.0,
    )
    with pytest.raises(ValueError, match="Invalid timeline range"):
        EditorValidator.validate_all(invalid_timeline)


def test_state_clone_deep_copy():
    state1 = EditorState(
        clip_id="c_orig",
        source_id="v.mp4",
        source_duration=100.0,
        source_start=0.0,
        source_end=20.0,
        captions=[CaptionSegment(id="1", start=0.0, end=5.0, text="Original")],
    )
    state2 = state1.clone()
    # Mutating clone should not mutate original
    state2.captions[0].text = "Mutated"
    state2.source_start = 5.0

    assert state1.captions[0].text == "Original"
    assert state1.source_start == 0.0
    assert state2.captions[0].text == "Mutated"
    assert state2.source_start == 5.0
