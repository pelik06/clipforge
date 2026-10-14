import pytest
from services.reframing.service import Detection
from services.speaker_detection.models import (
    MouthActivity,
    SpeakerDetectorConfig,
    SpeakerTimeline,
    SpeechSegment,
)
from services.speaker_detection.detector import ActiveSpeakerDetector


def test_active_speaker_selection():
    """Verify active speaker tracks speech when two speakers alternate speaking turns."""
    detector = ActiveSpeakerDetector()

    # Track 1 visible 0.0 - 10.0
    # Track 2 visible 0.0 - 10.0
    detections = []
    for i in range(40):  # 4 fps, 10 seconds
        t = round(i * 0.25, 2)
        detections.append(Detection(frame_index=i, timestamp=t, bbox=(100, 100, 120, 150), center_x=160, center_y=175, width=120, height=150, confidence=0.9, track_id=1))
        detections.append(Detection(frame_index=i, timestamp=t, bbox=(500, 100, 120, 150), center_x=560, center_y=175, width=120, height=150, confidence=0.9, track_id=2))

    # Track 1 speaks from 0.0 to 4.5
    # Track 2 speaks from 5.0 to 9.5
    speech_segments = [
        SpeechSegment(start=0.0, end=4.5, confidence=1.0),
        SpeechSegment(start=5.0, end=9.5, confidence=1.0),
    ]
    mouth_activities = {
        1: [MouthActivity(track_id=1, start=0.0, end=4.5, score=0.85), MouthActivity(track_id=1, start=4.5, end=10.0, score=0.1)],
        2: [MouthActivity(track_id=2, start=0.0, end=4.5, score=0.1), MouthActivity(track_id=2, start=5.0, end=10.0, score=0.85)],
    }

    timeline = detector.analyze_speakers(
        detections=detections,
        speech_segments=speech_segments,
        mouth_activities=mouth_activities,
        total_duration=10.0,
    )
    assert timeline.speaker_mode == "active_speaker"
    assert len(timeline.segments) >= 2

    # First segment belongs to Track 1
    assert timeline.segments[0].track_id == 1
    # Subsequent segment switches to Track 2
    track_ids = [s.track_id for s in timeline.segments]
    assert 1 in track_ids
    assert 2 in track_ids


def test_speaker_switch_hysteresis():
    """Verify that a single-frame noise spike does NOT switch speaker without confirmation."""
    cfg = SpeakerDetectorConfig(switch_margin=0.12, switch_confirmation_frames=5, min_active_speaker_duration=0.5)
    detector = ActiveSpeakerDetector(config=cfg)

    detections = []
    # 20 frames = 5 seconds
    for i in range(20):
        t = round(i * 0.25, 2)
        # Track 1 has solid confidence 0.9
        detections.append(Detection(frame_index=i, timestamp=t, bbox=(100, 100, 120, 150), center_x=160, center_y=175, width=120, height=150, confidence=0.9, track_id=1))
        # Track 2 has confidence 0.8
        detections.append(Detection(frame_index=i, timestamp=t, bbox=(500, 100, 120, 150), center_x=560, center_y=175, width=120, height=150, confidence=0.8, track_id=2))

    # Both are in speech, but Track 1 was active first
    speech_segments = [SpeechSegment(start=0.0, end=5.0, confidence=0.9)]

    timeline = detector.analyze_speakers(
        detections=detections,
        speech_segments=speech_segments,
        total_duration=5.0,
    )

    # Because Track 2 never sustained 5 confirmation frames with switch_margin advantage, Track 1 remains active
    assert timeline.speaker_mode == "active_speaker"
    assert timeline.segments[0].track_id == 1


def test_speaker_fallback():
    """Verify that absent or zero-confidence situations fallback to fallback_tracking."""
    detector = ActiveSpeakerDetector()

    # Empty detections
    timeline_empty = detector.analyze_speakers(
        detections=[],
        speech_segments=[],
        total_duration=5.0,
    )
    assert timeline_empty.speaker_mode == "fallback_tracking"
    assert "No face detections available" in timeline_empty.fallback_reason

    # Extremely low confidence with no speech
    low_dets = [
        Detection(frame_index=0, timestamp=0.0, bbox=(10, 10, 20, 20), center_x=20, center_y=20, width=20, height=20, confidence=0.1, track_id=1),
        Detection(frame_index=1, timestamp=0.25, bbox=(10, 10, 20, 20), center_x=20, center_y=20, width=20, height=20, confidence=0.1, track_id=1),
    ]
    timeline_low = detector.analyze_speakers(
        detections=low_dets,
        speech_segments=[],
        total_duration=1.0,
    )
    assert timeline_low.speaker_mode == "fallback_tracking"
