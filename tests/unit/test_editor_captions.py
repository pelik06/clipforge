import pytest
from services.editor.models import CaptionSegment, EditorState
from services.editor.operations import EditorOperations


def test_caption_text_edit():
    state = EditorState(
        clip_id="c_cap",
        source_id="v.mp4",
        source_duration=60.0,
        source_start=0.0,
        source_end=20.0,
        captions=[
            CaptionSegment(id="c1", start=1.0, end=4.0, text="aku pikir ini penting")
        ],
    )
    edited = EditorOperations.edit_caption_text(state, "c1", "menurutku ini sangat penting")
    assert edited.captions[0].text == "menurutku ini sangat penting"
    assert edited.editor_version == state.editor_version + 1


def test_caption_split():
    state = EditorState(
        clip_id="c_split",
        source_id="v.mp4",
        source_duration=60.0,
        source_start=0.0,
        source_end=20.0,
        captions=[
            CaptionSegment(id="c1", start=1.0, end=5.0, text="Kalimat pembuka yang cukup panjang")
        ],
    )
    # Split at 3.0s
    split_state = EditorOperations.split_caption(state, "c1", split_time=3.0)
    assert len(split_state.captions) == 2
    assert split_state.captions[0].start == 1.0
    assert split_state.captions[0].end == 3.0
    assert split_state.captions[1].start == 3.0
    assert split_state.captions[1].end == 5.0


def test_caption_merge():
    state = EditorState(
        clip_id="c_merge",
        source_id="v.mp4",
        source_duration=60.0,
        source_start=0.0,
        source_end=20.0,
        captions=[
            CaptionSegment(id="c1", start=1.0, end=3.0, text="Halo"),
            CaptionSegment(id="c2", start=3.0, end=5.0, text="Dunia"),
        ],
    )
    merged_state = EditorOperations.merge_captions(state, "c1", "c2")
    assert len(merged_state.captions) == 1
    assert merged_state.captions[0].text == "Halo Dunia"
    assert merged_state.captions[0].start == 1.0
    assert merged_state.captions[0].end == 5.0


def test_caption_delete():
    state = EditorState(
        clip_id="c_del",
        source_id="v.mp4",
        source_duration=60.0,
        source_start=0.0,
        source_end=20.0,
        captions=[
            CaptionSegment(id="c1", start=1.0, end=3.0, text="Satu"),
            CaptionSegment(id="c2", start=3.5, end=6.0, text="Dua"),
        ],
    )
    deleted_state = EditorOperations.delete_caption(state, "c1")
    assert len(deleted_state.captions) == 1
    assert deleted_state.captions[0].id == "c2"


def test_caption_timing_validation():
    state = EditorState(
        clip_id="c_time_err",
        source_id="v.mp4",
        source_duration=60.0,
        source_start=0.0,
        source_end=10.0,
        captions=[
            CaptionSegment(id="c1", start=2.0, end=4.0, text="Teks"),
        ],
    )
    # End <= Start should raise ValueError
    with pytest.raises(ValueError, match="non-positive duration"):
        EditorOperations.edit_caption_timing(state, "c1", new_start=4.0, new_end=2.0)

    # End exceeding clip duration should raise ValueError
    with pytest.raises(ValueError, match="exceeds clip duration"):
        EditorOperations.edit_caption_timing(state, "c1", new_start=2.0, new_end=15.0)
