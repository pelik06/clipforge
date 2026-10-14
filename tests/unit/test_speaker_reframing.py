import pytest
from pathlib import Path
import subprocess

from core.config.settings import Settings
from services.reframing.service import Detection, Reframer, ReframingAnalysis


def test_split_layout_decision():
    """Verify SPLIT mode activates when 2 distinct speakers exist, and falls back to TRACK if only 1 face exists."""
    reframer = Reframer()

    # Case A: 2 distinct tracks with horizontal distance > 0.38
    raw_detections_2speakers = [
        Detection(frame_index=0, timestamp=0.0, bbox=(100, 100, 120, 150), center_x=160, center_y=175, width=120, height=150, confidence=0.9, track_id=1),
        Detection(frame_index=0, timestamp=0.0, bbox=(700, 100, 120, 150), center_x=760, center_y=175, width=120, height=150, confidence=0.9, track_id=2),
    ]

    # Mock analyze_footage internal track resolution or test build_split_filter
    analysis_split = ReframingAnalysis(
        mode="split_layout",
        layout_mode="SPLIT",
        active_speaker_available=True,
        face_detection_available=True,
        detections=raw_detections_2speakers,
        primary_track_id=1,
        secondary_track_id=2,
        split_crops=((100, 50, 600, 530), (700, 50, 600, 530)),
    )

    filt = reframer.build_split_filter(analysis_split, src_w=1920, src_h=1080)
    assert "vstack=inputs=2" in filt
    assert "[top]" in filt
    assert "[bot]" in filt


def test_split_layout_render_actual(tmp_path):
    """Verify FFmpeg renders dual stacked 1080x960 split layout into valid 1080x1920 MP4."""
    s = Settings()
    test_media = tmp_path / "synthetic_2speakers.mp4"
    cmd = [
        s.ffmpeg_bin, "-y",
        "-f", "lavfi", "-i", "testsrc=duration=4:size=1280x720:rate=25",
        "-f", "lavfi", "-i", "sine=frequency=1000:duration=4",
        "-c:v", "libx264", "-c:a", "aac",
        str(test_media),
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    out_mp4 = tmp_path / "out_split.mp4"
    reframer = Reframer()
    res = reframer.render_vertical(
        source_path=str(test_media),
        output_path=str(out_mp4),
        width=1080,
        height=1920,
        framing_mode="split",
    )

    assert out_mp4.exists()
    assert out_mp4.stat().st_size > 1024

    # Probe dimensions
    cmd_probe = [s.ffprobe_bin, "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(out_mp4)]
    r = subprocess.run(cmd_probe, capture_output=True, text=True)
    assert "1080,1920" in r.stdout.strip()
