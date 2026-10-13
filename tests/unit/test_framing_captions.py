import json
import sqlite3
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from core.config.settings import Settings
from core.models.configuration import (
    CaptionLanguage,
    CaptionPosition,
    CaptionPreset,
    CaptionSize,
    FramingMode,
    JobConfig,
    validate_hex_color,
)
from core.models.candidate import CandidateMoment
from core.models.transcript import TranscriptSegment, Word
from core.storage import _format_job_row, get_job, init_db, save_job
from services.captions.service import (
    CaptionRenderer,
    adjust_segments_for_clip,
    escape_ass_text,
    format_ass_time,
    hex_to_ass_color,
    verify_caption_in_frame,
    validate_ass_file,
)
from services.detection.service import SignalDetector
from services.scoring.service import MomentScorer
from services.detection.scene import SceneDetector
from services.scoring.selector import MomentSelector
from services.qc.service import QualityController
from services.reframing.service import Reframer, ReframingAnalysis, TrajectoryPoint


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def sample_video(tmp_path_factory):
    """Create a real 3-second 1280x720 video fixture using FFmpeg."""
    tmp_dir = tmp_path_factory.mktemp("media_test")
    video_path = tmp_dir / "sample_input.mp4"
    s = Settings()
    cmd = [
        s.ffmpeg_bin,
        "-y",
        "-f", "lavfi", "-i", "testsrc=duration=3:size=1280x720:rate=25",
        "-f", "lavfi", "-i", "sine=frequency=800:duration=3",
        "-c:v", "libx264",
        "-c:a", "aac",
        str(video_path),
    ]
    proc = subprocess.run(cmd, capture_output=True)
    assert proc.returncode == 0
    return video_path


# ==============================================================================
# Task 8.1: Configuration Schema & Validation Tests
# ==============================================================================


def test_job_config_defaults():
    cfg = JobConfig()
    cfg.validate()
    assert cfg.framing_mode == "center_crop"
    assert cfg.caption_preset == "clean"
    assert cfg.caption_language == "auto"
    assert cfg.caption_size == "medium"
    assert cfg.caption_position == "bottom_safe"
    assert cfg.caption_text_color == "#FFFFFF"
    assert cfg.caption_highlight_color == "#FFFF00"
    assert cfg.caption_word_highlight is False


def test_job_config_all_allowed_enums():
    for f in FramingMode:
        for p in CaptionPreset:
            for l in CaptionLanguage:
                for s in CaptionSize:
                    for pos in CaptionPosition:
                        cfg = JobConfig(
                            framing_mode=f.value,
                            caption_preset=p.value,
                            caption_language=l.value,
                            caption_size=s.value,
                            caption_position=pos.value,
                        )
                        cfg.validate()
                        if p == CaptionPreset.KARAOKE:
                            assert cfg.caption_word_highlight is True


def test_job_config_invalid_enums_rejected():
    with pytest.raises(ValueError, match="Invalid framing_mode"):
        JobConfig(framing_mode="drone_follow").validate()

    with pytest.raises(ValueError, match="Invalid caption_preset"):
        JobConfig(caption_preset="3d_neon").validate()

    with pytest.raises(ValueError, match="Invalid caption_language"):
        JobConfig(caption_language="fr").validate()

    with pytest.raises(ValueError, match="Invalid caption_size"):
        JobConfig(caption_size="extra_huge").validate()

    with pytest.raises(ValueError, match="Invalid caption_position"):
        JobConfig(caption_position="sidebar").validate()


def test_color_validation():
    assert validate_hex_color("#ffffff") == "#FFFFFF"
    assert validate_hex_color("#38bdf8") == "#38BDF8"
    assert validate_hex_color("#F00") == "#F00"

    with pytest.raises(ValueError):
        validate_hex_color("blue")
    with pytest.raises(ValueError):
        validate_hex_color("#12345")
    with pytest.raises(ValueError):
        validate_hex_color("#GGGGGG")


# ==============================================================================
# Task 8.2: SQLite Persistence & Backward Compatibility
# ==============================================================================


def test_sqlite_persistence_and_reload(tmp_path):
    db_file = tmp_path / "test_store.db"
    init_db(db_file)

    test_job = {
        "id": "job_cfg_001",
        "vod_url": "https://youtu.be/dQw4w9WgXcQ",
        "kind": "youtube",
        "status": "created",
        "stage": "Queued",
        "progress": 5,
        "framing_mode": "auto_follow_speaker",
        "caption_preset": "creator_bold",
        "caption_language": "id",
        "caption_size": "large",
        "caption_position": "top_safe",
        "caption_text_color": "#00FF00",
        "caption_highlight_color": "#FF00FF",
        "caption_word_highlight": True,
    }

    save_job(test_job, db_path=db_file)
    loaded = get_job("job_cfg_001", db_path=db_file)
    assert loaded is not None
    assert loaded["framing_mode"] == "auto_follow_speaker"
    assert loaded["caption_preset"] == "creator_bold"
    assert loaded["caption_language"] == "id"
    assert loaded["caption_size"] == "large"
    assert loaded["caption_position"] == "top_safe"
    assert loaded["caption_text_color"] == "#00FF00"
    assert loaded["caption_highlight_color"] == "#FF00FF"
    assert loaded["caption_word_highlight"] is True


def test_sqlite_backward_compatibility_legacy_rows():
    # Simulate a legacy SQLite row where configuration columns are NULL or missing
    class MockRow(dict):
        def keys(self):
            return super().keys()

    legacy_row = MockRow({
        "id": "job_legacy_999",
        "vod_url": "https://youtu.be/legacy",
        "kind": "youtube",
        "status": "completed",
        "current_stage": "Finished",
        "progress": 100,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "error": None,
        "metadata_json": "{}",
        "stages_json": "[]",
        "framing_mode": None,
        "caption_preset": None,
        "caption_language": None,
        "caption_size": None,
        "caption_position": None,
        "caption_text_color": None,
        "caption_highlight_color": None,
        "caption_word_highlight": None,
    })

    formatted = _format_job_row(legacy_row)
    assert formatted["framing_mode"] == "center_crop"
    assert formatted["caption_preset"] == "clean"
    assert formatted["caption_language"] == "auto"
    assert formatted["caption_size"] == "medium"
    assert formatted["caption_position"] == "bottom_safe"
    assert formatted["caption_text_color"] == "#FFFFFF"
    assert formatted["caption_highlight_color"] == "#FFFF00"
    assert formatted["caption_word_highlight"] is False


# ==============================================================================
# Task 8.3 & 8.4: Reframing, Speaker Transparency & Fallback Tests
# ==============================================================================


def test_reframer_analysis_and_fallback(sample_video):
    rf = Reframer()
    analysis = rf.analyze_footage(str(sample_video))

    # Synthetic testsrc video has no faces -> must fall back safely to center
    assert analysis.active_speaker_available is False  # Never claim speaker detection!
    assert analysis.fallback_applied is True
    assert "center crop fallback" in analysis.fallback_reason.lower()


def test_reframer_filter_construction():
    rf = Reframer()
    # 1. Fallback / empty trajectory generates standard center crop
    fallback_analysis = ReframingAnalysis(mode="auto_follow_speaker", fallback_applied=True)
    f_str = rf.build_crop_filter(fallback_analysis, 1280, 720, 1080, 1920)
    assert "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920" in f_str

    # 2. Dynamic trajectory creates smooth piecewise expression
    pts = [
        TrajectoryPoint(timestamp=0.0, target_x=640, target_y=360, crop_x=200, crop_y=0),
        TrajectoryPoint(timestamp=1.0, target_x=700, target_y=360, crop_x=260, crop_y=0),
        TrajectoryPoint(timestamp=2.0, target_x=800, target_y=360, crop_x=340, crop_y=0),
    ]
    active_analysis = ReframingAnalysis(
        mode="auto_follow_speaker",
        fallback_applied=False,
        trajectory=pts,
    )
    dyn_filter = rf.build_crop_filter(active_analysis, 1280, 720, 1080, 1920)
    assert "crop=1080:1920:x=" in dyn_filter
    assert "if(lt(t,1.00)" in dyn_filter


def test_reframer_render_actual_video(sample_video, tmp_path):
    rf = Reframer()
    out = tmp_path / "vertical_actual.mp4"
    res = rf.render_vertical(
        str(sample_video),
        str(out),
        width=1080,
        height=1920,
        framing_mode="auto_follow_speaker",
    )
    assert Path(res).exists()
    assert Path(res).stat().st_size > 1024

    qc = QualityController()
    qc_res = qc.check(str(out))
    assert qc_res.passed is True
    assert qc_res.checks["valid_container"] is True


# ==============================================================================
# Task 8.5: Caption Renderer, Presets, Formatting & Escaping Tests
# ==============================================================================


def test_hex_to_ass_color():
    assert hex_to_ass_color("#FFFFFF") == "&H00FFFFFF&"
    assert hex_to_ass_color("#FFFF00") == "&H0000FFFF&"  # Yellow in BGR: B=00, G=FF, R=FF
    assert hex_to_ass_color("#FF0000") == "&H000000FF&"  # Red in BGR: B=00, G=00, R=FF
    assert hex_to_ass_color("#0000FF") == "&H00FF0000&"  # Blue in BGR: B=FF, G=00, R=00


def test_ass_time_format():
    assert format_ass_time(0.0) == "0:00:00.00"
    assert format_ass_time(5.25) == "0:00:05.25"
    assert format_ass_time(65.5) == "0:01:05.50"


def test_ass_text_escaping():
    raw = "Halo {Dunia} & \\Keren!\nBaris baru."
    escaped = escape_ass_text(raw)
    assert "{" not in escaped
    assert "}" not in escaped
    assert "\n" not in escaped
    assert "(Dunia)" in escaped


def test_caption_presets_visual_differences():
    cr = CaptionRenderer()
    words = [Word(text="Halo", start=0.5, end=1.0), Word(text="Semua", start=1.0, end=1.5)]
    seg = [TranscriptSegment(text="Halo Semua", start=0.5, end=1.5, words=words)]

    clean_ass = cr.generate_ass_script(seg, JobConfig(caption_preset="clean"))
    bold_ass = cr.generate_ass_script(seg, JobConfig(caption_preset="creator_bold"))
    karaoke_ass = cr.generate_ass_script(seg, JobConfig(caption_preset="karaoke"))
    minimal_ass = cr.generate_ass_script(seg, JobConfig(caption_preset="minimal"))

    assert "Impact" in bold_ass
    assert "Arial Black" in karaoke_ass
    assert "Arial" in clean_ass
    assert "Segoe UI" in minimal_ass
    # Karaoke has word-level color tags
    assert "\\c" in karaoke_ass


def test_karaoke_missing_word_timestamps_fails():
    cr = CaptionRenderer()
    seg_no_words = [TranscriptSegment(text="Tidak ada kata", start=0.5, end=2.0, words=[])]
    with pytest.raises(ValueError, match="verified word-level timestamps"):
        cr.generate_ass_script(seg_no_words, JobConfig(caption_preset="karaoke"))


def test_no_captions_preset_skips(sample_video, tmp_path):
    cr = CaptionRenderer()
    out = tmp_path / "no_cap.mp4"
    res = cr.render(
        transcript_segments=[],
        video_path=str(sample_video),
        output_path=str(out),
        config=JobConfig(caption_preset="no_captions"),
    )
    assert res["status"] == "skipped"
    assert res["reason"] == "captions disabled by user"
    assert Path(out).exists()


def test_burn_captions_ffmpeg_actual(sample_video, tmp_path):
    cr = CaptionRenderer()
    out = tmp_path / "captioned_actual.mp4"
    words = [
        Word(text="Streamer", start=0.2, end=1.0),
        Word(text="Keren", start=1.0, end=2.0),
    ]
    segs = [TranscriptSegment(text="Streamer Keren", start=0.2, end=2.0, words=words)]

    cfg = JobConfig(caption_preset="creator_bold", caption_word_highlight=True, caption_highlight_color="#FFFF00")
    res = cr.render(segs, str(sample_video), str(out), config=cfg)
    assert res["status"] == "completed"
    assert Path(out).exists()
    assert Path(out).stat().st_size > 1024

    qc = QualityController()
    assert qc.check(str(out)).passed is True
def test_subtitle_timing_offset_adjustment():
    raw_segments = [
        TranscriptSegment(text="Before clip", start=5.0, end=9.5, words=[Word("Before", 5.0, 9.5)]),
        TranscriptSegment(
            text="Inside clip moment",
            start=22.0,
            end=27.0,
            words=[Word("Inside", 22.0, 23.5), Word("clip", 23.5, 25.0), Word("moment", 25.0, 27.0)],
        ),
        TranscriptSegment(text="After clip", start=45.0, end=50.0, words=[Word("After", 45.0, 50.0)]),
    ]

    # Slice clip from 20.0s to 30.0s
    adjusted = adjust_segments_for_clip(raw_segments, clip_start=20.0, clip_end=30.0)
    assert len(adjusted) == 1
    target = adjusted[0]
    assert target.text == "Inside clip moment"
    # Shifted: 22.0 - 20.0 = 2.0s; 27.0 - 20.0 = 7.0s
    assert target.start == 2.0
    assert target.end == 7.0
    assert len(target.words) == 3
    assert target.words[0].start == 2.0
    assert target.words[0].end == 3.5
    assert target.words[1].start == 3.5
    assert target.words[2].start == 5.0


def test_visual_caption_burn_in_pixels(sample_video, tmp_path):
    cr = CaptionRenderer()
    out_captioned = tmp_path / "burned_visual_check.mp4"
    words = [Word("HELLO", 0.1, 1.2), Word("WORLD", 1.2, 2.5)]
    segs = [TranscriptSegment("HELLO WORLD", 0.1, 2.5, words=words)]

    cfg = JobConfig(caption_preset="creator_bold", caption_size="large", caption_position="bottom_safe")
    res = cr.render(segs, str(sample_video), str(out_captioned), config=cfg, clip_start=0.0)
    assert res["status"] == "completed"

    # Visual frame check: compare against raw video without subtitles
    has_visible_captions = verify_caption_in_frame(
        str(out_captioned),
        timestamp=1.0,
        raw_reference_video=str(sample_video),
    )
    assert has_visible_captions is True


def test_signal_detector_full_video_analysis(sample_video):
    detector = SignalDetector()
    duration = detector.get_media_duration(str(sample_video))
    assert duration >= 2.5

    # Simulate transcript segments across a timeline
    segs = [
        TranscriptSegment("Opening hook intro", start=0.5, end=4.5, words=[Word("Opening", 0.5, 2.0), Word("hook", 2.0, 4.5)]),
        TranscriptSegment("Climax reaction here", start=12.0, end=19.5, words=[Word("Climax", 12.0, 15.0), Word("reaction", 15.0, 19.5)]),
    ]

    candidates = detector.detect(str(sample_video), transcript_segments=segs, min_clip_seconds=3.0)
    assert len(candidates) >= 1
    # Check that candidate generation supports variable duration
    durations = [c.duration for c in candidates]
    assert any(d != 6.0 for d in durations)


def test_moment_scorer_reasons_and_nms():
    scorer = MomentScorer()
    c1 = CandidateMoment(start=10.0, end=18.0, signals={"audio_energy": 0.9, "reaction_signal": 0.85, "speech_density": 0.8, "sentence_completeness": 1.0, "duration_score": 0.9})
    # Overlapping duplicate candidate (11.0 to 17.5 overlaps > 35%)
    c2 = CandidateMoment(start=11.0, end=17.5, signals={"audio_energy": 0.7, "reaction_signal": 0.6, "speech_density": 0.5, "sentence_completeness": 0.8, "duration_score": 0.7})
    # Distinct second candidate at 35.0 to 45.0
    c3 = CandidateMoment(start=35.0, end=45.0, signals={"audio_energy": 0.8, "reaction_signal": 0.7, "speech_density": 0.6, "sentence_completeness": 1.0, "duration_score": 0.8})

    scored = scorer.score([c1, c2, c3], top_n=2, max_overlap_ratio=0.35)
    assert len(scored) == 2
    # c1 is top ranked
    assert scored[0].start == 10.0
    assert scored[0].score > 80.0
    assert len(scored[0].reasons) >= 1
    # c2 was suppressed due to overlap with c1; c3 is second
    assert scored[1].start == 35.0
def test_validate_ass_file(tmp_path):
    valid_ass = tmp_path / "valid.ass"
    valid_ass.write_text(
        "[Script Info]\nTitle: Test\n[V4+ Styles]\nStyle: Default\n[Events]\nDialogue: 0,0:00:01.00,0:00:03.00,Default,,0,0,0,,Halo\n",
        encoding="utf-8",
    )
    res = validate_ass_file(str(valid_ass))
    assert res["valid"] is True
    assert res["dialogue_count"] == 1

    empty_ass = tmp_path / "empty.ass"
    empty_ass.write_text("", encoding="utf-8")
    with pytest.raises(ValueError):
        validate_ass_file(str(empty_ass))

    no_dialogue = tmp_path / "no_dialogue.ass"
    no_dialogue.write_text("[Script Info]\n[V4+ Styles]\n[Events]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="zero Dialogue events"):
        validate_ass_file(str(no_dialogue))


def test_scene_detector(sample_video):
    sd = SceneDetector()
    scenes = sd.detect_scenes(str(sample_video), min_scene_duration=1.0)
    assert len(scenes) >= 1
    assert "start" in scenes[0]
    assert "end" in scenes[0]
    assert scenes[0]["duration"] > 0


def test_moment_selector_heuristic_and_ai_fallback():
    selector = MomentSelector(mode="ai", provider="gemini")
    segs = [
        TranscriptSegment("Intro sentence statement.", start=0.5, end=6.0, words=[Word("Intro", 0.5, 2.0)]),
        TranscriptSegment("Second sentence with full thought.", start=10.0, end=17.0, words=[Word("Second", 10.0, 13.0)]),
    ]
    scenes = [{"start": 0.0, "end": 8.0, "duration": 8.0}, {"start": 8.0, "end": 20.0, "duration": 12.0}]

    res = selector.select_moments(
        video_duration=25.0,
        transcript_segments=segs,
        words_json=[{"w": "Intro", "s": 0.5, "e": 2.0}],
        scenes=scenes,
        min_duration=4.0,
        max_duration=15.0,
        max_clips=3,
    )
    assert len(res.candidates) >= 1
    assert res.mode in ("ai_semantic", "heuristic_fallback")

# ==============================================================================
# Task 8.6 & 8.7: API Validation & Human Approval Gate Regression Tests
# ==============================================================================


def test_api_create_job_with_config(client):
    res = client.post(
        "/api/v4/jobs",
        json={
            "vod_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "framing_mode": "auto_follow_speaker",
            "caption_preset": "creator_bold",
            "caption_language": "id",
            "caption_size": "large",
            "caption_position": "center",
            "caption_text_color": "#FFFFFF",
            "caption_highlight_color": "#38BDF8",
            "caption_word_highlight": True,
        },
    )
    assert res.status_code == 200
    job = res.json()["job"]
    assert job["framing_mode"] == "auto_follow_speaker"
    assert job["caption_preset"] == "creator_bold"
    assert job["caption_highlight_color"] == "#38BDF8"

def test_api_moment_detection_validation(client):
    # Invalid max_clips (> 15)
    r = client.post(
        "/api/v4/jobs",
        json={"vod_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "max_clips": 50},
    )
    assert r.status_code == 400
    assert "max_clips must be between 1 and 15" in r.json()["detail"]

    # Valid moment detection options
    r2 = client.post(
        "/api/v4/jobs",
        json={
            "vod_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "moment_detection_mode": "ai",
            "max_clips": 4,
            "min_clip_duration": 10.0,
            "max_clip_duration": 45.0,
        },
    )
    assert r2.status_code == 200
    assert r2.json()["job"]["max_clips"] == 4
    assert r2.json()["job"]["moment_detection_mode"] == "ai"

def test_api_create_job_invalid_config_rejected(client):
    # Invalid framing
    r1 = client.post(
        "/api/v4/jobs",
        json={"vod_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "framing_mode": "invalid_mode"},
    )
    assert r1.status_code == 400
    assert "Configuration error" in r1.json()["detail"]

    # Invalid color
    r2 = client.post(
        "/api/v4/jobs",
        json={"vod_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "caption_text_color": "not_hex"},
    )
    assert r2.status_code == 400
    assert "Invalid caption_text_color" in r2.json()["detail"]


def test_human_approval_gate_preserved(client):
    # Operator must approve clip before publishing
    approve_res = client.post(
        "/api/v4/jobs/fixture_001/decision",
        json={"decision": "approve"},
    )
    assert approve_res.status_code == 200
    data = approve_res.json()
    assert data["decision"] == "APPROVED"
    assert data["clip"]["status"] == "APPROVED"

    reject_res = client.post(
        "/api/v4/jobs/fixture_002/decision",
        json={"decision": "reject"},
    )
    assert reject_res.status_code == 200
    data_rej = reject_res.json()
    assert data_rej["decision"] == "REJECTED"
    assert data_rej["clip"]["status"] == "REJECTED"
