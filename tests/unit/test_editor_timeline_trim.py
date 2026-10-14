import pytest
from services.editor.models import CaptionSegment, EditorState
from services.editor.operations import EditorOperations
from services.editor.timeline import TimelineHelper
from services.editor.validation import EditorValidator


def test_trim_operation():
    state = EditorState(
        clip_id="c_trim",
        source_id="v.mp4",
        source_duration=100.0,
        source_start=10.0,
        source_end=40.0,
    )
    # Trim to 15.0 - 35.0
    trimmed = EditorOperations.trim(state, 15.0, 35.0)
    assert trimmed.source_start == 15.0
    assert trimmed.source_end == 35.0
    assert trimmed.clip_duration == 20.0
    assert trimmed.editor_version == state.editor_version + 1
    assert "trim" in trimmed.user_overrides


def test_trim_minimum_duration():
    state = EditorState(
        clip_id="c_min",
        source_id="v.mp4",
        source_duration=100.0,
        source_start=10.0,
        source_end=40.0,
    )
    # Trimming to duration < 3.0s should be rejected
    with pytest.raises(ValueError, match="less than minimum allowed"):
        EditorOperations.trim(state, 10.0, 11.5)


def test_trim_maximum_duration():
    state = EditorState(
        clip_id="c_max",
        source_id="v.mp4",
        source_duration=50.0,
        source_start=0.0,
        source_end=30.0,
    )
    # Trimming beyond source duration should be rejected
    with pytest.raises(ValueError, match="exceeds source_duration"):
        EditorOperations.trim(state, 0.0, 65.0)


def test_caption_rebasing_after_trim():
    # Source duration: 100s. Original clip: 10s to 40s.
    # Captions relative to 10s:
    # cap1: 2.0 -> 5.0 (absolute 12.0 -> 15.0)
    # cap2: 10.0 -> 15.0 (absolute 20.0 -> 25.0)
    # cap3: 25.0 -> 28.0 (absolute 35.0 -> 38.0)
    captions = [
        CaptionSegment(id="cap1", start=2.0, end=5.0, text="Drop me"),
        CaptionSegment(id="cap2", start=10.0, end=15.0, text="Keep me"),
        CaptionSegment(id="cap3", start=25.0, end=28.0, text="Drop me too"),
    ]

    # Trim to 18.0s -> 30.0s
    # cap1 (abs 12-15) is completely outside [< 18] -> dropped!
    # cap2 (abs 20-25) is inside [18-30] -> rebased relative to 18: start=2.0, end=7.0!
    # cap3 (abs 35-38) is completely outside [> 30] -> dropped!
    rebased = TimelineHelper.rebase_captions_after_trim(
        captions=captions,
        old_source_start=10.0,
        new_source_start=18.0,
        new_source_end=30.0,
    )

    assert len(rebased) == 1
    assert rebased[0].id == "cap2"
    assert rebased[0].start == 2.0
    assert rebased[0].end == 7.0
    assert rebased[0].text == "Keep me"
