import pytest
from services.editor.models import CaptionSegment, EditorState
from services.editor.operations import EditorOperations
from services.editor.undo_redo import EditorHistoryManager


def test_single_operation_undo_redo():
    initial = EditorState(
        clip_id="c_undo_1",
        source_id="v.mp4",
        source_duration=50.0,
        source_start=0.0,
        source_end=30.0,
    )
    history = EditorHistoryManager(initial)
    assert history.can_undo is False
    assert history.can_redo is False

    # Op 1: trim to 5.0 - 25.0
    s1 = EditorOperations.trim(history.current_state, 5.0, 25.0)
    history.push(s1)
    assert history.can_undo is True
    assert history.current_state.source_start == 5.0

    # Undo
    undone = history.undo()
    assert undone is not None
    assert undone.source_start == 0.0
    assert history.can_undo is False
    assert history.can_redo is True

    # Redo
    redone = history.redo()
    assert redone is not None
    assert redone.source_start == 5.0
    assert history.can_undo is True
    assert history.can_redo is False


def test_multiple_operations_undo_redo():
    initial = EditorState(
        clip_id="c_undo_multi",
        source_id="v.mp4",
        source_duration=50.0,
        source_start=0.0,
        source_end=30.0,
        captions=[CaptionSegment(id="c1", start=1.0, end=4.0, text="A")],
    )
    history = EditorHistoryManager(initial)

    # Op 1: edit caption text to 'B'
    s1 = EditorOperations.edit_caption_text(history.current_state, "c1", "B")
    history.push(s1)

    # Op 2: change volume to 1.5
    s2 = EditorOperations.set_audio(history.current_state, volume=1.5)
    history.push(s2)

    # Op 3: set crop manual
    s3 = EditorOperations.set_crop(history.current_state, x=0.2, y=0.1, width=0.8, height=0.8, mode="manual")
    history.push(s3)

    assert history.current_state.crop.mode == "manual"
    assert history.current_state.audio.volume == 1.5

    # Undo Op 3 -> back to s2
    history.undo()
    assert history.current_state.crop.mode == "auto"
    assert history.current_state.audio.volume == 1.5

    # Undo Op 2 -> back to s1
    history.undo()
    assert history.current_state.audio.volume == 1.0
    assert history.current_state.captions[0].text == "B"

    # Undo Op 1 -> back to initial
    history.undo()
    assert history.current_state.captions[0].text == "A"


def test_branching_history_clears_redo():
    initial = EditorState(
        clip_id="c_branch",
        source_id="v.mp4",
        source_duration=50.0,
        source_start=0.0,
        source_end=30.0,
    )
    history = EditorHistoryManager(initial)

    s1 = EditorOperations.trim(history.current_state, 5.0, 25.0)
    history.push(s1)

    history.undo()
    assert history.can_redo is True

    # New branch operation while redo is available
    s_new = EditorOperations.set_layout(history.current_state, "SPLIT")
    history.push(s_new)

    # Redo stack must be wiped
    assert history.can_redo is False
    assert history.current_state.layout == "SPLIT"


def test_undo_redo_immutability():
    initial = EditorState(
        clip_id="c_immut",
        source_id="v.mp4",
        source_duration=50.0,
        source_start=0.0,
        source_end=30.0,
        captions=[CaptionSegment(id="c1", start=1.0, end=4.0, text="Constant")],
    )
    history = EditorHistoryManager(initial)

    s1 = EditorOperations.edit_caption_text(history.current_state, "c1", "Changed")
    history.push(s1)

    # Mutate s1 directly outside history manager
    s1.captions[0].text = "Hacked"

    # Undo should restore untainted original
    restored = history.undo()
    assert restored.captions[0].text == "Constant"
