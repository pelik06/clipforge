from pathlib import Path
import pytest
from core.storage import (
    delete_export_artifact,
    get_editor_state,
    list_export_artifacts,
    save_editor_state,
    save_export_artifact,
)
from services.editor.editor_state import EditorStateManager
from services.editor.models import (
    CaptionSegment,
    CropConfig,
    EditorState,
    EditorStatus,
    RenderSnapshot,
)
from services.editor.render_bridge import StudioRenderBridge


def test_editor_state_persistence_save_and_reload(tmp_path):
    db_file = tmp_path / "editor_test.db"
    manager = EditorStateManager(db_path=db_file)

    clip = {
        "id": "clip_persist_1",
        "vod": "https://youtu.be/sample",
        "start_time": 10.0,
        "end_time": 40.0,
        "duration": "30.0s",
        "layout_mode": "TRACK",
    }
    state = manager.load_or_initialize(clip)
    assert state.clip_id == "clip_persist_1"
    assert state.source_start == 10.0
    assert state.source_end == 40.0
    assert state.editor_version == 1

    # Update version and save
    state.editor_version = 2
    state.crop.mode = "manual"
    state.crop.scale = 1.3
    manager.save(state)

    # Reload from fresh manager instance (simulating server/browser restart)
    manager2 = EditorStateManager(db_path=db_file)
    reloaded = manager2.load_or_initialize(clip)
    assert reloaded.editor_version == 2
    assert reloaded.crop.mode == "manual"
    assert reloaded.crop.scale == 1.3


def test_render_snapshot_immutability():
    state = EditorState(
        clip_id="c_snap",
        source_id="v.mp4",
        source_duration=60.0,
        source_start=5.0,
        source_end=25.0,
        editor_version=3,
    )
    bridge = StudioRenderBridge()
    snapshot = bridge.create_snapshot(state, preset="tiktok")

    assert snapshot.clip_id == "c_snap"
    assert snapshot.editor_version == 3
    assert snapshot.preset == "tiktok"
    assert snapshot.editor_state["source_start"] == 5.0

    # Mutate state after snapshot
    state.source_start = 12.0
    state.editor_version = 4

    # Snapshot remains immutable
    assert snapshot.editor_state["source_start"] == 5.0
    assert snapshot.editor_version == 3


def test_preview_and_final_filter_synthesis():
    state = EditorState(
        clip_id="c_filters",
        source_id="data/input/real_talk_35s.mp4",
        source_duration=35.0,
        source_start=2.0,
        source_end=15.0,
        crop=CropConfig(x=0.1, y=0.1, width=0.8, height=0.8, mode="manual"),
        captions=[
            CaptionSegment(id="cap1", start=0.5, end=3.0, text="Edited text")
        ],
    )
    bridge = StudioRenderBridge()
    cfg, ass_file = bridge.prepare_render_config(state, preset="preview")

    assert cfg["start_time"] == 2.0
    assert cfg["duration"] == 13.0
    assert "crop=" in cfg["vf_filter"]
    assert "ass=" in cfg["vf_filter"]
    assert ass_file is not None
    assert Path(ass_file).exists()


def test_stale_export_detection(tmp_path):
    db_file = tmp_path / "stale_test.db"

    # Save editor state at version 2
    save_editor_state({
        "clip_id": "clip_stale_demo",
        "editor_version": 2,
        "status": "DRAFT",
        "state_json": {"clip_id": "clip_stale_demo", "source_start": 0.0, "source_end": 20.0},
    }, db_path=db_file)

    # Save export rendered from version 1
    save_export_artifact({
        "id": "exp_old_v1",
        "clip_id": "clip_stale_demo",
        "editor_version": 1,
        "preset": "tiktok",
        "render_type": "final",
        "output_path": "data/renders/final/old.mp4",
        "file_size": 2048,
        "duration": 20.0,
    }, db_path=db_file)

    # Save export rendered from current version 2
    save_export_artifact({
        "id": "exp_fresh_v2",
        "clip_id": "clip_stale_demo",
        "editor_version": 2,
        "preset": "draft",
        "render_type": "final",
        "output_path": "data/renders/final/fresh.mp4",
        "file_size": 1024,
        "duration": 20.0,
    }, db_path=db_file)

    exports = list_export_artifacts(clip_id="clip_stale_demo", db_path=db_file)
    assert len(exports) == 2

    old_exp = next(e for e in exports if e["id"] == "exp_old_v1")
    fresh_exp = next(e for e in exports if e["id"] == "exp_fresh_v2")

    assert old_exp["is_stale"] is True
    assert "Outdated export" in old_exp["stale_reason"]
    assert old_exp["status"] == "OUTDATED"

    assert fresh_exp["is_stale"] is False
    assert fresh_exp["stale_reason"] is None


def test_export_artifact_deletion(tmp_path):
    db_file = tmp_path / "del_test.db"
    save_export_artifact({
        "id": "exp_del_1",
        "clip_id": "clip_del",
        "editor_version": 1,
        "output_path": "v.mp4",
    }, db_path=db_file)

    assert len(list_export_artifacts(clip_id="clip_del", db_path=db_file)) == 1
    delete_export_artifact("exp_del_1", db_path=db_file)
    assert len(list_export_artifacts(clip_id="clip_del", db_path=db_file)) == 0
