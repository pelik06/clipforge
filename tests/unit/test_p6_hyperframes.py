"""P6 HyperFrames Motion Editing System Unit Tests.

Covers layer model, composition serialization, hook generation, person layers,
title editing, caption editing, caption timing, animations, templates,
timeline and z-index ordering, persistence, undo/redo, validation, and multi-clip automation.
"""

import json
from pathlib import Path
import pytest
import uuid

from core.models.transcript import Word, TranscriptSegment
from services.render.hyperframes_models import (
    AnimationType,
    CompositionLayer,
    HyperframesComposition,
    LayerType,
    TemplateType,
)
from services.render.hyperframes_templates import generate_initial_composition
from services.render.hyperframes_validator import HyperframesValidator
from services.render.hyperframes_composition import HyperframesCompositionBuilder, HyperframesConfig
from services.render.models import RenderJob, RenderJobState, RenderPreset
from services.render.presets import get_preset_config
from services.editor.models import EditorState, RenderSnapshot


# ==============================================================================
# 1. Layer Model & Serialization Tests (1-6)
# ==============================================================================

def test_layer_creation():
    layer = CompositionLayer(
        id="layer_01",
        type=LayerType.TEXT,
        start=0.0,
        end=5.0,
        x=540.0,
        y=960.0,
        scale=1.2,
        opacity=0.9,
    )
    assert layer.id == "layer_01"
    assert layer.type == LayerType.TEXT
    assert layer.duration == 5.0
    assert layer.scale == 1.2


def test_layer_to_and_from_dict():
    layer = CompositionLayer(
        id="layer_hook",
        type=LayerType.HOOK,
        start=1.0,
        end=8.0,
        x=500.0,
        y=200.0,
        scale=1.0,
        z_index=5,
        data={"title": "VIRAL TITLE", "badge": "★ NEW"},
    )
    d = layer.to_dict()
    assert d["type"] == "hook"
    assert d["duration"] == 7.0
    assert d["data"]["title"] == "VIRAL TITLE"

    rebuilt = CompositionLayer.from_dict(d)
    assert rebuilt.id == "layer_hook"
    assert rebuilt.type == LayerType.HOOK
    assert rebuilt.data["badge"] == "★ NEW"


def test_layer_duration_property():
    l1 = CompositionLayer(id="l1", type=LayerType.VIDEO, start=5.25, end=15.75)
    assert l1.duration == 10.5


def test_composition_to_and_from_dict():
    comp = HyperframesComposition(
        composition_id="comp_123",
        clip_id="clip_001",
        template=TemplateType.FINANCE.value,
        duration=68.0,
        layers=[
            CompositionLayer(id="v1", type=LayerType.VIDEO, start=0.0, end=68.0),
            CompositionLayer(id="h1", type=LayerType.HOOK, start=0.0, end=10.0),
        ],
        captions=[{"text": "Alpha", "start": 1.0, "end": 1.5}],
    )
    d = comp.to_dict()
    assert d["composition_id"] == "comp_123"
    assert len(d["layers"]) == 2
    assert d["template"] == "FINANCE"

    rebuilt = HyperframesComposition.from_dict(d)
    assert rebuilt.duration == 68.0
    assert len(rebuilt.layers) == 2
    assert rebuilt.layers[0].type == LayerType.VIDEO


def test_composition_json_roundtrip():
    comp = HyperframesComposition(
        composition_id="comp_json",
        clip_id="clip_json",
        duration=45.0,
    )
    comp.add_layer(CompositionLayer(id="pb", type=LayerType.PROGRESS_BAR, start=0.0, end=45.0))
    json_str = comp.to_json()
    assert "comp_json" in json_str

    rebuilt = HyperframesComposition.from_json(json_str)
    assert rebuilt.composition_id == "comp_json"
    assert len(rebuilt.layers) == 1


def test_layer_type_enumeration():
    assert LayerType.VIDEO.value == "video"
    assert LayerType.PERSON.value == "person"
    assert LayerType.HOOK.value == "hook"
    assert LayerType.CAPTION.value == "caption"
    assert LayerType.PROGRESS_BAR.value == "progress_bar"


# ==============================================================================
# 2. Composition Layer Management & Z-Index (7-11)
# ==============================================================================

def test_add_layer_maintains_z_index_order():
    comp = HyperframesComposition(composition_id="c1", clip_id="clip_1", duration=30.0)
    l_hook = CompositionLayer(id="hook", type=LayerType.HOOK, start=0, end=10, z_index=5)
    l_video = CompositionLayer(id="video", type=LayerType.VIDEO, start=0, end=30, z_index=0)
    l_caption = CompositionLayer(id="caption", type=LayerType.CAPTION, start=0, end=30, z_index=8)

    comp.add_layer(l_hook)
    comp.add_layer(l_caption)
    comp.add_layer(l_video)

    assert comp.layers[0].id == "video"
    assert comp.layers[1].id == "hook"
    assert comp.layers[2].id == "caption"


def test_get_layer_by_id():
    comp = HyperframesComposition(composition_id="c1", clip_id="clip_1", duration=30.0)
    comp.add_layer(CompositionLayer(id="layer_alpha", type=LayerType.TEXT, start=0, end=5))
    layer = comp.get_layer("layer_alpha")
    assert layer is not None
    assert layer.type == LayerType.TEXT
    assert comp.get_layer("non_existent") is None


def test_remove_layer():
    comp = HyperframesComposition(composition_id="c1", clip_id="clip_1", duration=30.0)
    comp.add_layer(CompositionLayer(id="l1", type=LayerType.TEXT, start=0, end=5))
    comp.add_layer(CompositionLayer(id="l2", type=LayerType.SHAPE, start=0, end=5))
    assert len(comp.layers) == 2

    ok = comp.remove_layer("l1")
    assert ok is True
    assert len(comp.layers) == 1
    assert comp.layers[0].id == "l2"

    ok_again = comp.remove_layer("l1")
    assert ok_again is False


def test_layer_visibility_toggle():
    layer = CompositionLayer(id="l_vis", type=LayerType.OVERLAY, start=0, end=10, visible=True)
    assert layer.visible is True
    layer.visible = False
    assert layer.visible is False
    d = layer.to_dict()
    assert d["visible"] is False


def test_layer_position_and_scale_mutation():
    layer = CompositionLayer(id="p1", type=LayerType.PERSON, start=0, end=20, x=300, y=500, scale=1.0)
    layer.x = 420.0
    layer.y = 650.0
    layer.scale = 1.35
    layer.rotation = 15.0
    assert layer.x == 420.0
    assert layer.y == 650.0
    assert layer.scale == 1.35
    assert layer.rotation == 15.0


# ==============================================================================
# 3. Template Generation & AI Auto-Composition (12-18)
# ==============================================================================

def test_template_viral_podcast_defaults():
    clip = {
        "id": "clip_test_vp",
        "title": "Highlight #1: Rahasia Viral Podcast [10.0s-70.0s]",
        "duration": "60.0s",
        "start_time": 10.0,
        "end_time": 70.0,
        "layout_mode": "TRACK",
    }
    comp = generate_initial_composition(clip, template=TemplateType.VIRAL_PODCAST.value)
    assert comp.template == TemplateType.VIRAL_PODCAST.value
    assert comp.duration == 60.0

    layer_types = [l.type for l in comp.layers]
    assert LayerType.VIDEO in layer_types
    assert LayerType.HOOK in layer_types
    assert LayerType.PERSON in layer_types
    assert LayerType.PROGRESS_BAR in layer_types
    assert LayerType.CAPTION in layer_types


def test_template_two_speaker_layout():
    clip = {
        "id": "clip_test_dual",
        "title": "Debat Seru Dua Pembicara",
        "duration": "75.0s",
        "start_time": 0.0,
        "end_time": 75.0,
        "layout_mode": "SPLIT",
    }
    comp = generate_initial_composition(clip)
    assert comp.template == TemplateType.TWO_SPEAKER.value

    person_layers = [l for l in comp.layers if l.type == LayerType.PERSON]
    assert len(person_layers) == 2
    assert person_layers[0].id == "layer_person_a"
    assert person_layers[1].id == "layer_person_b"
    assert person_layers[0].x != person_layers[1].x  # Left and right positioning


def test_template_finance_styling():
    clip = {
        "id": "clip_test_fin",
        "title": "Cara Dapat Cuan Puluhan Miliar Dari Crypto",
        "duration": "50.0s",
        "start_time": 5.0,
        "end_time": 55.0,
    }
    comp = generate_initial_composition(clip)
    assert comp.template == TemplateType.FINANCE.value

    hook_layer = comp.get_layer("layer_hook_title")
    assert hook_layer is not None
    assert "WEALTH" in hook_layer.data["badge"]
    assert hook_layer.data["text_color"] == "#FFDE00"


def test_template_minimal_clean():
    clip = {
        "id": "clip_test_min",
        "title": "Catatan Hening",
        "duration": "40.0s",
        "start_time": 0.0,
        "end_time": 40.0,
    }
    comp = generate_initial_composition(clip, template=TemplateType.MINIMAL.value)
    assert comp.template == TemplateType.MINIMAL.value
    assert comp.get_layer("layer_hook_title") is not None


def test_interview_template():
    clip = {
        "id": "clip_test_int",
        "title": "Exclusive Interview with Founder",
        "duration": "45.0s",
        "start_time": 0.0,
        "end_time": 45.0,
    }
    comp = generate_initial_composition(clip, template=TemplateType.INTERVIEW.value)
    assert comp.template == TemplateType.INTERVIEW.value
    hook = comp.get_layer("layer_hook_title")
    assert "INTERVIEW" in hook.data["subtitle"]


def test_title_cleaning_from_raw_highlight():
    clip = {
        "id": "clip_title_clean",
        "title": "Highlight #3: Samuel Christ: Belajar Bisnis [12.0s-45.0s]",
        "duration": "33.0s",
    }
    comp = generate_initial_composition(clip)
    hook = comp.get_layer("layer_hook_title")
    assert "[" not in hook.data["title"]
    assert "Belajar Bisnis" in hook.data["title"]


def test_caption_word_rebasing():
    clip = {
        "id": "clip_c_rebase",
        "title": "Test Rebase",
        "duration": "20.0s",
        "start_time": 50.0,
        "end_time": 70.0,
    }
    segs = [
        TranscriptSegment(
            text="Kata pertama kata kedua",
            start=52.0,
            end=56.0,
            words=[
                Word(text="Kata", start=52.0, end=53.0),
                Word(text="pertama", start=53.0, end=54.0),
                Word(text="kata", start=54.0, end=55.0),
                Word(text="kedua", start=55.0, end=56.0),
            ],
        )
    ]
    comp = generate_initial_composition(clip, transcript_segments=segs)
    assert len(comp.captions) == 4
    # Rebased relative to clip start (50.0) -> 2.0s to 6.0s
    assert comp.captions[0]["start"] == 2.0
    assert comp.captions[3]["end"] == 6.0


# ==============================================================================
# 4. Composition Validation & Error Handling (19-24)
# ==============================================================================

def test_validator_passes_valid_composition():
    comp = HyperframesComposition(composition_id="val_1", clip_id="clip_1", duration=30.0)
    comp.add_layer(CompositionLayer(id="v1", type=LayerType.VIDEO, start=0, end=30, data={"src": "video.mp4"}))
    comp.add_layer(CompositionLayer(id="h1", type=LayerType.HOOK, start=0, end=8))
    validator = HyperframesValidator()
    res = validator.validate(comp)
    assert res.valid is True
    assert len(res.issues) == 0


def test_validator_rejects_missing_video():
    comp = HyperframesComposition(composition_id="val_2", clip_id="clip_2", duration=30.0)
    comp.add_layer(CompositionLayer(id="h1", type=LayerType.HOOK, start=0, end=8))
    validator = HyperframesValidator()
    res = validator.validate(comp)
    assert res.valid is False
    assert any("VIDEO" in issue for issue in res.issues)


def test_validator_rejects_negative_duration():
    comp = HyperframesComposition(composition_id="val_3", clip_id="clip_3", duration=-5.0)
    comp.add_layer(CompositionLayer(id="v1", type=LayerType.VIDEO, start=0, end=30, data={"src": "video.mp4"}))
    validator = HyperframesValidator()
    res = validator.validate(comp)
    assert res.valid is False
    assert any("duration" in issue.lower() for issue in res.issues)


def test_validator_rejects_negative_layer_start():
    comp = HyperframesComposition(composition_id="val_4", clip_id="clip_4", duration=20.0)
    comp.add_layer(CompositionLayer(id="v1", type=LayerType.VIDEO, start=0, end=20, data={"src": "video.mp4"}))
    comp.add_layer(CompositionLayer(id="err_layer", type=LayerType.TEXT, start=-2.0, end=5.0))
    validator = HyperframesValidator()
    res = validator.validate(comp)
    assert res.valid is False
    assert any("negative start" in issue.lower() for issue in res.issues)


def test_validator_warns_on_nonstandard_canvas():
    comp = HyperframesComposition(composition_id="val_5", clip_id="clip_5", width=720, height=1280, duration=20.0)
    comp.add_layer(CompositionLayer(id="v1", type=LayerType.VIDEO, start=0, end=20, data={"src": "video.mp4"}))
    comp.add_layer(CompositionLayer(id="h1", type=LayerType.HOOK, start=0, end=5))
    validator = HyperframesValidator()
    res = validator.validate(comp)
    assert any("canvas dimensions" in w.lower() for w in res.warnings)


def test_validator_rejects_invalid_caption_timing():
    comp = HyperframesComposition(composition_id="val_6", clip_id="clip_6", duration=20.0)
    comp.add_layer(CompositionLayer(id="v1", type=LayerType.VIDEO, start=0, end=20, data={"src": "video.mp4"}))
    comp.captions = [{"text": "Broken", "start": 5.0, "end": 4.0}]
    validator = HyperframesValidator()
    res = validator.validate(comp)
    assert res.valid is False
    assert any("start" in issue and "end" in issue for issue in res.issues)


# ==============================================================================
# 5. HTML & GSAP Compilation Engine (25-30)
# ==============================================================================

def test_compiler_generates_seekable_gsap_timeline(tmp_path):
    builder = HyperframesCompositionBuilder()
    dummy_video = tmp_path / "src_video.mp4"
    dummy_video.write_bytes(b"\x00" * 2048)

    comp = HyperframesComposition(composition_id="comp_gsap", clip_id="c_gsap", duration=15.0)
    comp.add_layer(CompositionLayer(id="video", type=LayerType.VIDEO, start=0, end=15, data={"src": "src_video.mp4"}))
    comp.add_layer(CompositionLayer(id="hook_title", type=LayerType.HOOK, start=0, end=6, data={"title": "HEADLINE"}))
    comp.add_layer(CompositionLayer(id="progress", type=LayerType.PROGRESS_BAR, start=0, end=15, data={"color": "#00FF66"}))

    out_dir = tmp_path / "hf_project"
    builder.build_from_composition(out_dir, dummy_video, comp)

    html = (out_dir / "index.html").read_text(encoding="utf-8")
    assert 'gsap.timeline({ paused: true })' in html
    assert 'window.__timelines["main"] = tl;' in html
    assert 'tl.seek(0);' in html
    assert 'tl.to("#progress"' in html


def test_compiler_inlines_google_fonts(tmp_path):
    builder = HyperframesCompositionBuilder()
    dummy_video = tmp_path / "v.mp4"
    dummy_video.write_bytes(b"\x00" * 1024)

    comp = HyperframesComposition(composition_id="c_font", clip_id="c_f", duration=10.0)
    comp.add_layer(CompositionLayer(id="v", type=LayerType.VIDEO, start=0, end=10, data={"src": "v.mp4"}))

    out_dir = tmp_path / "hf_font_proj"
    builder.build_from_composition(out_dir, dummy_video, comp)

    html = (out_dir / "index.html").read_text(encoding="utf-8")
    assert "fonts.googleapis.com" in html
    assert "family=Anton" in html


def test_compiler_escapes_special_characters(tmp_path):
    builder = HyperframesCompositionBuilder()
    dummy_video = tmp_path / "v2.mp4"
    dummy_video.write_bytes(b"\x00" * 1024)

    comp = HyperframesComposition(composition_id="c_esc", clip_id="c_e", duration=10.0)
    comp.add_layer(CompositionLayer(id="v", type=LayerType.VIDEO, start=0, end=10, data={"src": "v2.mp4"}))
    comp.add_layer(CompositionLayer(id="h", type=LayerType.HOOK, start=0, end=5, data={"title": "Tips & Trik: Cuan > 100M!"}))

    out_dir = tmp_path / "hf_esc_proj"
    builder.build_from_composition(out_dir, dummy_video, comp)

    html = (out_dir / "index.html").read_text(encoding="utf-8")
    assert "Tips & Trik: Cuan > 100M!" in html


def test_compiler_creates_hyperframes_manifests(tmp_path):
    builder = HyperframesCompositionBuilder()
    dummy_video = tmp_path / "v3.mp4"
    dummy_video.write_bytes(b"\x00" * 1024)

    comp = HyperframesComposition(composition_id="c_man", clip_id="c_m", duration=8.0)
    comp.add_layer(CompositionLayer(id="v", type=LayerType.VIDEO, start=0, end=8, data={"src": "v3.mp4"}))

    out_dir = tmp_path / "hf_man_proj"
    builder.build_from_composition(out_dir, dummy_video, comp)

    assert (out_dir / "hyperframes.json").exists()
    assert (out_dir / "meta.json").exists()

    meta = json.loads((out_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["id"] == "c_man"


def test_compiler_kinetic_word_highlights(tmp_path):
    builder = HyperframesCompositionBuilder()
    dummy_video = tmp_path / "v4.mp4"
    dummy_video.write_bytes(b"\x00" * 1024)

    comp = HyperframesComposition(
        composition_id="c_kin",
        clip_id="c_k",
        duration=10.0,
        captions=[
            {"text": "Halo", "start": 1.0, "end": 1.5},
            {"text": "Dunia", "start": 1.5, "end": 2.0},
        ],
    )
    comp.add_layer(CompositionLayer(id="v", type=LayerType.VIDEO, start=0, end=10, data={"src": "v4.mp4"}))
    comp.add_layer(CompositionLayer(id="cap", type=LayerType.CAPTION, start=0, end=10))

    out_dir = tmp_path / "hf_kin_proj"
    builder.build_from_composition(out_dir, dummy_video, comp)

    html = (out_dir / "index.html").read_text(encoding="utf-8")
    assert "Halo" in html
    assert "Dunia" in html
    assert "tl.fromTo" in html
    assert "underline" in html


def test_compiler_multiple_persons_placement(tmp_path):
    builder = HyperframesCompositionBuilder()
    dummy_video = tmp_path / "v5.mp4"
    dummy_video.write_bytes(b"\x00" * 1024)

    comp = HyperframesComposition(composition_id="c_persons", clip_id="c_p", duration=12.0)
    comp.add_layer(CompositionLayer(id="v", type=LayerType.VIDEO, start=0, end=12, data={"src": "v5.mp4"}))
    comp.add_layer(CompositionLayer(id="p1", type=LayerType.PERSON, start=0, end=12, x=250, y=600, data={"person_label": "Guest A"}))
    comp.add_layer(CompositionLayer(id="p2", type=LayerType.PERSON, start=0, end=12, x=800, y=600, data={"person_label": "Guest B"}))

    out_dir = tmp_path / "hf_persons_proj"
    builder.build_from_composition(out_dir, dummy_video, comp)

    html = (out_dir / "index.html").read_text(encoding="utf-8")
    assert "Guest A" in html
    assert "Guest B" in html
    assert "left: 250.0px" in html
    assert "left: 800.0px" in html


# ==============================================================================
# 6. Presets, RenderSnapshots & Studio Integration (31-36)
# ==============================================================================

def test_hyperframes_preset_registered():
    cfg = get_preset_config("hyperframes")
    assert cfg.name == "hyperframes"
    assert cfg.width == 1080
    assert cfg.height == 1920
    assert cfg.fps == 30
    assert cfg.audio_normalize is True


def test_rendersnapshot_stores_hyperframes_composition():
    comp = HyperframesComposition(composition_id="c_snap", clip_id="clip_snap", duration=25.0)
    comp.add_layer(CompositionLayer(id="v", type=LayerType.VIDEO, start=0, end=25, data={"src": "video.mp4"}))
    comp.add_layer(CompositionLayer(id="h", type=LayerType.HOOK, start=0, end=8, data={"title": "SNAPSHOT TITLE"}))

    snap = RenderSnapshot(
        snapshot_id="snap_001",
        clip_id="clip_snap",
        editor_version=2,
        editor_state={
            "user_overrides": {
                "composition": comp.to_dict(),
            }
        },
        preset="hyperframes",
    )

    d = snap.to_dict()
    assert d["preset"] == "hyperframes"
    saved_comp = d["editor_state"]["user_overrides"]["composition"]
    assert saved_comp["composition_id"] == "c_snap"
    assert saved_comp["layers"][1]["data"]["title"] == "SNAPSHOT TITLE"


def test_editor_state_clone_preserves_composition():
    comp = HyperframesComposition(composition_id="c_clone", clip_id="clip_clone", duration=35.0)
    state = EditorState(
        clip_id="clip_clone",
        source_id="src.mp4",
        source_duration=35.0,
        source_start=0.0,
        source_end=35.0,
        user_overrides={"composition": comp.to_dict()},
    )
    cloned = state.clone()
    assert cloned.user_overrides["composition"]["composition_id"] == "c_clone"

    # Deep copy verification: mutating clone does not mutate original
    cloned.user_overrides["composition"]["duration"] = 99.0
    assert state.user_overrides["composition"]["duration"] == 35.0


def test_multi_clip_pipeline_composition_generation():
    """Verify that multiple clips each independently receive unique HyperFrames compositions."""
    clips = [
        {"id": "clip_01", "title": "Clip One [0s-60s]", "duration": "60.0s", "start_time": 0.0, "end_time": 60.0},
        {"id": "clip_02", "title": "Clip Two [60s-120s]", "duration": "60.0s", "start_time": 60.0, "end_time": 120.0},
        {"id": "clip_03", "title": "Clip Three [120s-180s]", "duration": "60.0s", "start_time": 120.0, "end_time": 180.0},
    ]

    compositions = []
    validator = HyperframesValidator()

    for c in clips:
        comp = generate_initial_composition(c)
        val_res = validator.validate(comp)
        assert val_res.valid is True
        compositions.append(comp)

    assert len(compositions) == 3
    # Distinct composition IDs
    comp_ids = set(c.composition_id for c in compositions)
    assert len(comp_ids) == 3


def test_animation_type_enum():
    assert AnimationType.NONE.value == "none"
    assert AnimationType.SPRING.value == "spring"
    assert AnimationType.WORD_POP.value == "word_pop"
    assert AnimationType.SLIDE_DOWN.value == "slide_down"


def test_template_type_enum():
    assert TemplateType.VIRAL_PODCAST.value == "VIRAL_PODCAST"
    assert TemplateType.TWO_SPEAKER.value == "TWO_SPEAKER"
    assert TemplateType.INTERVIEW.value == "INTERVIEW"
    assert TemplateType.FINANCE.value == "FINANCE"
    assert TemplateType.MINIMAL.value == "MINIMAL"
