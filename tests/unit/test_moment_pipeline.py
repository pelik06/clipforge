import uuid
import subprocess
from pathlib import Path

import pytest

from core.config.settings import Settings
from core.models.candidate import CandidateMoment
from core.storage import get_job, list_clips, save_job
from services.detection.moment_pipeline import NonLLMMomentDetector
from apps.worker.pipeline_runner import execute_job_pipeline_sync


def test_test1_five_valid_moments_generates_five_clips(tmp_path):
    """Test 1: 5 valid moments must generate exactly 5 clips (not just 1)."""
    test_media = tmp_path / "synthetic_5moments.mp4"
    s = Settings()
    cmd = [
        s.ffmpeg_bin, "-y",
        "-f", "lavfi", "-i", "testsrc=duration=30:size=640x360:rate=25",
        "-f", "lavfi", "-i", "sine=frequency=1000:duration=30",
        "-c:v", "libx264", "-c:a", "aac",
        str(test_media),
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    moments_data = [
        {"start": 1.0, "end": 4.5, "duration": 3.5, "score": 92.0, "reasons": ["Peak #1"]},
        {"start": 6.0, "end": 9.5, "duration": 3.5, "score": 88.0, "reasons": ["Peak #2"]},
        {"start": 11.0, "end": 14.5, "duration": 3.5, "score": 85.0, "reasons": ["Peak #3"]},
        {"start": 16.0, "end": 19.5, "duration": 3.5, "score": 82.0, "reasons": ["Peak #4"]},
        {"start": 21.0, "end": 24.5, "duration": 3.5, "score": 79.0, "reasons": ["Peak #5"]},
    ]

    job_id = f"job_test_5moments_{uuid.uuid4().hex[:6]}"
    cfg = {
        "caption_preset": "no_captions",
        "max_clips": 5,
        "min_clip_duration": 3.0,
        "max_clip_duration": 10.0,
    }

    save_job({
        "id": job_id,
        "vod_url": str(test_media.resolve()),
        "kind": "local",
        "status": "created",
        "metadata": {"candidates": moments_data},
        **cfg,
    })

    final_job = execute_job_pipeline_sync(job_id, str(test_media.resolve()), "local", config=cfg)
    assert final_job["status"] == "waiting_approval"

    clips = list_clips(job_id=job_id)
    assert len(clips) == 5, f"Expected 5 clips, got {len(clips)}"
    for c in clips:
        assert c["status"] == "WAITING_APPROVAL"
        assert c["media_url"] is not None
        assert (Path("data/output") / Path(c["media_url"]).name).exists()


def test_test2_two_valid_moments_generates_two_clips(tmp_path):
    """Test 2: 2 valid moments must generate exactly 2 clips (not 1)."""
    test_media = tmp_path / "synthetic_2moments.mp4"
    s = Settings()
    cmd = [
        s.ffmpeg_bin, "-y",
        "-f", "lavfi", "-i", "testsrc=duration=15:size=640x360:rate=25",
        "-f", "lavfi", "-i", "sine=frequency=800:duration=15",
        "-c:v", "libx264", "-c:a", "aac",
        str(test_media),
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    moments_data = [
        {"start": 1.0, "end": 5.0, "duration": 4.0, "score": 90.0, "reasons": ["Moment A"]},
        {"start": 8.0, "end": 12.0, "duration": 4.0, "score": 85.0, "reasons": ["Moment B"]},
    ]

    job_id = f"job_test_2moments_{uuid.uuid4().hex[:6]}"
    cfg = {
        "caption_preset": "no_captions",
        "max_clips": 5,
        "min_clip_duration": 3.0,
        "max_clip_duration": 10.0,
    }

    save_job({
        "id": job_id,
        "vod_url": str(test_media.resolve()),
        "kind": "local",
        "status": "created",
        "metadata": {"candidates": moments_data},
        **cfg,
    })

    final_job = execute_job_pipeline_sync(job_id, str(test_media.resolve()), "local", config=cfg)
    assert final_job["status"] == "waiting_approval"

    clips = list_clips(job_id=job_id)
    assert len(clips) == 2, f"Expected 2 clips, got {len(clips)}"


def test_test3_one_valid_moment_generates_one_clip(tmp_path):
    """Test 3: 1 valid moment must generate exactly 1 clip."""
    test_media = tmp_path / "synthetic_1moment.mp4"
    s = Settings()
    cmd = [
        s.ffmpeg_bin, "-y",
        "-f", "lavfi", "-i", "testsrc=duration=8:size=640x360:rate=25",
        "-f", "lavfi", "-i", "sine=frequency=600:duration=8",
        "-c:v", "libx264", "-c:a", "aac",
        str(test_media),
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    moments_data = [
        {"start": 1.0, "end": 5.5, "duration": 4.5, "score": 88.0, "reasons": ["Solo Highlight"]},
    ]

    job_id = f"job_test_1moment_{uuid.uuid4().hex[:6]}"
    cfg = {
        "caption_preset": "no_captions",
        "max_clips": 5,
        "min_clip_duration": 3.0,
        "max_clip_duration": 10.0,
    }

    save_job({
        "id": job_id,
        "vod_url": str(test_media.resolve()),
        "kind": "local",
        "status": "created",
        "metadata": {"candidates": moments_data},
        **cfg,
    })

    final_job = execute_job_pipeline_sync(job_id, str(test_media.resolve()), "local", config=cfg)
    assert final_job["status"] == "waiting_approval"

    clips = list_clips(job_id=job_id)
    assert len(clips) == 1, f"Expected 1 clip, got {len(clips)}"


def test_test4_ten_peaks_six_duplicates_yields_four_unique_clips():
    """Test 4: 10 candidate peaks with 6 duplicates (overlap > 0.35) yields 4 unique clips."""
    candidates = [
        CandidateMoment(start=10.0, end=20.0, score=95.0, reasons=["Cluster 1 Peak"]),
        CandidateMoment(start=11.0, end=19.5, score=80.0, reasons=["Cluster 1 Dup A"]),
        CandidateMoment(start=12.0, end=21.0, score=75.0, reasons=["Cluster 1 Dup B"]),
        CandidateMoment(start=30.0, end=40.0, score=90.0, reasons=["Cluster 2 Peak"]),
        CandidateMoment(start=32.0, end=39.0, score=78.0, reasons=["Cluster 2 Dup A"]),
        CandidateMoment(start=60.0, end=70.0, score=88.0, reasons=["Cluster 3 Peak"]),
        CandidateMoment(start=61.0, end=69.0, score=74.0, reasons=["Cluster 3 Dup A"]),
        CandidateMoment(start=62.0, end=71.0, score=70.0, reasons=["Cluster 3 Dup B"]),
        CandidateMoment(start=90.0, end=100.0, score=85.0, reasons=["Cluster 4 Peak"]),
        CandidateMoment(start=91.0, end=99.0, score=72.0, reasons=["Cluster 4 Dup A"]),
    ]
    assert len(candidates) == 10

    candidates.sort(key=lambda c: c.score, reverse=True)
    unique = []
    max_overlap = 0.35

    for cand in candidates:
        is_dup = False
        for prev in unique:
            overlap_start = max(cand.start, prev.start)
            overlap_end = min(cand.end, prev.end)
            if overlap_end > overlap_start:
                overlap_dur = overlap_end - overlap_start
                min_d = min(cand.duration, prev.duration)
                if (overlap_dur / min_d) > max_overlap:
                    is_dup = True
                    break
        if not is_dup:
            unique.append(cand)

    assert len(unique) == 4
    starts = sorted([c.start for c in unique])
    assert starts == [10.0, 30.0, 60.0, 90.0]


def test_test5_no_valid_moments_generates_zero_clips_with_status(tmp_path):
    """Test 5: Video without valid moments yields 0 clips and status NO_VALID_MOMENTS."""
    test_media = tmp_path / "synthetic_nomoments.mp4"
    s = Settings()
    cmd = [
        s.ffmpeg_bin, "-y",
        "-f", "lavfi", "-i", "testsrc=duration=5:size=640x360:rate=25",
        "-f", "lavfi", "-i", "sine=frequency=400:duration=5",
        "-c:v", "libx264", "-c:a", "aac",
        str(test_media),
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    job_id = f"job_test_nomoments_{uuid.uuid4().hex[:6]}"
    cfg = {
        "caption_preset": "no_captions",
        "min_clip_duration": 4.0,
        "max_clip_duration": 10.0,
    }

    save_job({
        "id": job_id,
        "vod_url": str(test_media.resolve()),
        "kind": "local",
        "status": "created",
        "metadata": {"candidates": []},
        **cfg,
    })

    final_job = execute_job_pipeline_sync(job_id, str(test_media.resolve()), "local", config=cfg)
    assert "NO_VALID_MOMENTS" in final_job["stage"]
    assert final_job["status"] == "completed"

    clips = list_clips(job_id=job_id)
    assert len(clips) == 0, f"Expected 0 clips, got {len(clips)}"
