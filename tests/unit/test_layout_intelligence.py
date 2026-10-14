import pytest
from services.layout.layout_decision import AdvancedLayoutEngine, LayoutMode


def test_track_decision():
    engine = AdvancedLayoutEngine()

    # Single face -> TRACK
    faces = [{"track_id": 1, "center_x": 0.5, "center_y": 0.4}]
    dec = engine.evaluate_layout(timestamp=0.5, visible_faces=faces)
    assert dec.mode == LayoutMode.TRACK.value
    assert dec.primary_track_id == 1


def test_split_decision():
    engine = AdvancedLayoutEngine(split_distance_threshold=0.35)

    # 2 widely separated faces (0.2 and 0.8 -> distance 0.6 > 0.35)
    faces = [
        {"track_id": 1, "center_x": 0.2, "center_y": 0.4},
        {"track_id": 2, "center_x": 0.8, "center_y": 0.4},
    ]
    dec = engine.evaluate_layout(timestamp=0.5, visible_faces=faces)
    assert dec.mode == LayoutMode.SPLIT.value
    assert dec.primary_track_id == 1
    assert dec.secondary_track_id == 2


def test_layout_hysteresis():
    engine = AdvancedLayoutEngine(min_layout_duration=1.0)

    # Start in TRACK
    f_single = [{"track_id": 1, "center_x": 0.5, "center_y": 0.4}]
    dec1 = engine.evaluate_layout(timestamp=0.0, visible_faces=f_single)
    assert dec1.mode == LayoutMode.TRACK.value

    # Immediately after 0.2s, 2 faces appear -> switch should be suppressed by hysteresis (< 1.0s)
    f_double = [
        {"track_id": 1, "center_x": 0.1, "center_y": 0.4},
        {"track_id": 2, "center_x": 0.9, "center_y": 0.4},
    ]
    dec2 = engine.evaluate_layout(timestamp=0.2, visible_faces=f_double)
    assert dec2.mode == LayoutMode.TRACK.value
    assert "suppressed" in dec2.reason.lower()

    # At 1.5s (> 1.0s min duration), switch should be allowed
    dec3 = engine.evaluate_layout(timestamp=1.5, visible_faces=f_double)
    assert dec3.mode == LayoutMode.SPLIT.value
    assert dec3.switched is True


def test_scene_cut_reset():
    engine = AdvancedLayoutEngine(min_layout_duration=2.0)

    f_single = [{"track_id": 1, "center_x": 0.5, "center_y": 0.4}]
    engine.evaluate_layout(timestamp=0.0, visible_faces=f_single)

    # Within 0.3s (< 2.0s), but marked with is_scene_cut=True -> instant switch allowed!
    f_double = [
        {"track_id": 1, "center_x": 0.1, "center_y": 0.4},
        {"track_id": 2, "center_x": 0.9, "center_y": 0.4},
    ]
    dec_cut = engine.evaluate_layout(timestamp=0.3, visible_faces=f_double, is_scene_cut=True)
    assert dec_cut.mode == LayoutMode.SPLIT.value
    assert dec_cut.switched is True
