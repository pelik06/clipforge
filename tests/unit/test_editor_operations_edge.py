import pytest
from services.editor.models import (
    CaptionSegment,
    EditorState,
    EditorStatus,
    RenderSnapshot,
)
from services.editor.operations import EditorOperations
from services.editor.render_bridge import StudioRenderBridge
from services.editor.validation import EditorValidator


def test_caption_add_operation():
    state = EditorState(
        clip_id="c_add_test",
        source_id="v.mp4",
        source_duration=60.0,
        source_start=0.0,
        source_end=20.0,
        captions=[],
    )
    assert len(state.captions) == 0
    # Add caption at 2.0s -> 5.0s
    updated = EditorOperations.add_caption(state, start=2.0, end=5.0, text="New caption segment", emphasis=True)
    assert len(updated.captions) == 1
    assert updated.captions[0].text == "New caption segment"
    assert updated.captions[0].emphasis is True
    assert updated.editor_version == state.editor_version + 1


def test_audio_mute_filter_synthesis():
    state = EditorState(
        clip_id="c_mute_test",
        source_id="data/input/real_talk_35s.mp4",
        source_duration=35.0,
        source_start=0.0,
        source_end=15.0,
    )
    # Mute audio
    muted = EditorOperations.set_audio(state, mute=True)
    bridge = StudioRenderBridge()
    cfg, _ = bridge.prepare_render_config(muted)
    assert cfg["af_filter"] == "volume=0.0"


def test_crop_scale_and_position():
    state = EditorState(
        clip_id="c_crop_scale",
        source_id="v.mp4",
        source_duration=50.0,
        source_start=0.0,
        source_end=20.0,
    )
    overridden = EditorOperations.set_crop(state, x=0.35, y=0.15, width=0.6, height=0.7, scale=1.4, mode="manual")
    assert overridden.crop.mode == "manual"
    assert overridden.crop.x == 0.35
    assert overridden.crop.y == 0.15
    assert overridden.crop.scale == 1.4

    bridge = StudioRenderBridge()
    cfg, _ = bridge.prepare_render_config(overridden)
    assert "crop=" in cfg["vf_filter"]


def test_editor_state_approval_workflow():
    state = EditorState(
        clip_id="c_workflow",
        source_id="v.mp4",
        source_duration=50.0,
        source_start=0.0,
        source_end=20.0,
        status=EditorStatus.DRAFT,
    )
    assert state.status == EditorStatus.DRAFT

    state.status = EditorStatus.PREVIEWED
    assert state.status == EditorStatus.PREVIEWED

    state.status = EditorStatus.APPROVED
    assert state.status == EditorStatus.APPROVED

    state.status = EditorStatus.EXPORTED
    assert state.status == EditorStatus.EXPORTED


def test_editor_snapshot_serialization():
    snapshot = RenderSnapshot(
        snapshot_id="snap_123",
        clip_id="c_snap_test",
        editor_version=4,
        editor_state={"start": 0.0, "end": 15.0},
        preset="high_quality",
    )
    d = snapshot.to_dict()
    assert d["snapshot_id"] == "snap_123"
    assert d["clip_id"] == "c_snap_test"
    assert d["editor_version"] == 4
    assert d["preset"] == "high_quality"


def test_editor_validator_empty_caption_rejection():
    state = EditorState(
        clip_id="c_empty_cap",
        source_id="v.mp4",
        source_duration=50.0,
        source_start=0.0,
        source_end=20.0,
        captions=[CaptionSegment(id="1", start=1.0, end=4.0, text="   ")],
    )
    with pytest.raises(ValueError, match="text cannot be empty"):
        EditorValidator.validate_all(state)
