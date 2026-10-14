from typing import Any, Dict, List, Optional, Set, Tuple
from pathlib import Path
import numpy as np

from services.speaker_detection.models import (
    MouthActivity,
    SpeakerDetectorConfig,
    SpeakerSegment,
    SpeakerTimeline,
    SpeechSegment,
)
from services.speaker_detection.vad import VoiceActivityDetector
from services.speaker_detection.mouth_activity import MouthActivityDetector


class ActiveSpeakerDetector:
    """Multi-modal active speaker detection combining VAD, mouth motion, face visibility, and temporal continuity."""

    def __init__(self, config: Optional[SpeakerDetectorConfig] = None):
        self.config = config or SpeakerDetectorConfig()
        self.vad = VoiceActivityDetector()
        self.mouth_detector = MouthActivityDetector()

    def is_in_speech(self, timestamp: float, speech_segments: List[SpeechSegment]) -> Tuple[bool, float]:
        """Check if timestamp falls within an active speech segment and return confidence."""
        if not speech_segments:
            return False, 0.0
        for seg in speech_segments:
            if seg.start <= timestamp <= seg.end:
                return True, seg.confidence
        return False, 0.0

    def get_mouth_score(
        self,
        track_id: int,
        timestamp: float,
        mouth_activities: Dict[int, List[MouthActivity]],
    ) -> float:
        """Lookup mouth activity score for track at timestamp."""
        acts = mouth_activities.get(track_id, [])
        if not acts:
            return 0.5  # Neutral default when mouth movement is unmeasured
        for a in acts:
            if a.start <= timestamp <= a.end:
                return a.score
        return 0.2

    def analyze_speakers(
        self,
        detections: List[Any],  # List of Detection objects with frame_index, timestamp, bbox, track_id, confidence
        speech_segments: List[SpeechSegment],
        scenes: Optional[List[Dict[str, float]]] = None,
        video_path: Optional[str] = None,
        total_duration: float = 0.0,
        mouth_activities: Optional[Dict[int, List[MouthActivity]]] = None,
    ) -> SpeakerTimeline:
        """Evaluate active speaker across timeline with hysteresis and scene-cut priority."""
        if not detections:
            return SpeakerTimeline(
                segments=[],
                active_tracks=[],
                speaker_mode="fallback_tracking",
                fallback_reason="No face detections available for speaker tracking.",
            )

        # Index detections by timestamp and track
        timestamps = sorted(list({round(d.timestamp, 3) for d in detections}))
        if not timestamps:
            return SpeakerTimeline(
                segments=[],
                active_tracks=[],
                speaker_mode="fallback_tracking",
                fallback_reason="No timestamps found in detections.",
            )

        track_dets_by_t: Dict[float, Dict[int, Any]] = {t: {} for t in timestamps}
        all_tracks: Set[int] = set()

        for d in detections:
            t = round(d.timestamp, 3)
            track_dets_by_t[t][d.track_id] = d
            all_tracks.add(d.track_id)

        # Check for multiple visible speakers
        active_track_ids = sorted(list(all_tracks))

        # Compute mouth motion if video file exists and not supplied
        if mouth_activities is None:
            mouth_activities = {}
            if video_path and Path(video_path).exists() and len(active_track_ids) > 1:
                try:
                    tracks_for_mouth: Dict[int, List[Dict[str, Any]]] = {tid: [] for tid in active_track_ids}
                    for d in detections:
                        tracks_for_mouth[d.track_id].append({
                            "frame_index": d.frame_index,
                            "timestamp": d.timestamp,
                            "bbox": d.bbox,
                        })
                    mouth_activities = self.mouth_detector.compute_track_mouth_activity(video_path, tracks_for_mouth)
                except Exception:
                    mouth_activities = {}

        # Scene cut timestamps
        scene_cut_times = {round(s["start"], 3) for s in (scenes or []) if s.get("start", 0) > 0.3}

        # Track state over time
        current_speaker_tid: Optional[int] = None
        current_speaker_start: float = 0.0
        pending_candidate_tid: Optional[int] = None
        candidate_confirm_frames: int = 0

        frame_speaker_assignments: List[Tuple[float, int, float]] = []  # (t, track_id, score)

        cfg = self.config

        for t in timestamps:
            t_dets = track_dets_by_t[t]
            if not t_dets:
                continue

            is_scene_cut = any(abs(t - sc_t) < 0.25 for sc_t in scene_cut_times)
            in_speech, speech_conf = self.is_in_speech(t, speech_segments)
            speech_factor = speech_conf if in_speech else 0.10

            # Score each visible track
            track_scores: Dict[int, float] = {}
            for tid, d in t_dets.items():
                mouth_score = self.get_mouth_score(tid, t, mouth_activities)
                face_vis = min(1.0, max(0.0, float(d.confidence)))
                temporal_cont = 1.0 if (current_speaker_tid is not None and tid == current_speaker_tid) else 0.0

                score = (
                    cfg.speech_weight * speech_factor
                    + cfg.mouth_weight * mouth_score
                    + cfg.face_weight * face_vis
                    + cfg.temporal_weight * temporal_cont
                )
                track_scores[tid] = float(np.clip(score, 0.0, 1.0))

            # Pick highest scoring track for current timestamp
            best_tid, best_score = max(track_scores.items(), key=lambda item: item[1])

            # Initial assignment
            if current_speaker_tid is None:
                current_speaker_tid = best_tid
                current_speaker_start = t
                pending_candidate_tid = None
                candidate_confirm_frames = 0
            else:
                curr_score = track_scores.get(current_speaker_tid, 0.0)

                # PRIORITY 1: Scene cut -> switch instantly to the best visible face in the new scene
                if is_scene_cut:
                    current_speaker_tid = best_tid
                    current_speaker_start = t
                    pending_candidate_tid = None
                    candidate_confirm_frames = 0

                # PRIORITY 2: Active Speaker Switch with Hysteresis
                elif best_tid != current_speaker_tid:
                    dur_active = t - current_speaker_start
                    # Must exceed switch margin and minimum active duration
                    if (best_score - curr_score) > cfg.switch_margin and dur_active >= cfg.min_active_speaker_duration:
                        if pending_candidate_tid == best_tid:
                            candidate_confirm_frames += 1
                        else:
                            pending_candidate_tid = best_tid
                            candidate_confirm_frames = 1

                        if candidate_confirm_frames >= cfg.switch_confirmation_frames:
                            current_speaker_tid = best_tid
                            current_speaker_start = t
                            pending_candidate_tid = None
                            candidate_confirm_frames = 0
                    else:
                        pending_candidate_tid = None
                        candidate_confirm_frames = 0
                else:
                    pending_candidate_tid = None
                    candidate_confirm_frames = 0

            frame_speaker_assignments.append((t, current_speaker_tid, track_scores.get(current_speaker_tid, best_score)))

        if not frame_speaker_assignments:
            return SpeakerTimeline(
                segments=[],
                active_tracks=active_track_ids,
                speaker_mode="fallback_tracking",
                fallback_reason="No speaker frames resolved.",
            )

        # Check if speaker confidence is high enough to avoid fake speaker identity
        mean_score = float(np.mean([item[2] for item in frame_speaker_assignments]))
        if mean_score < cfg.min_confidence_threshold and not speech_segments:
            return SpeakerTimeline(
                segments=[],
                active_tracks=active_track_ids,
                speaker_mode="fallback_tracking",
                fallback_reason=f"Active speaker confidence ({mean_score:.2f}) below threshold {cfg.min_confidence_threshold}.",
            )

        # Group sequential frames into contiguous speaker segments
        timeline_segments: List[SpeakerSegment] = []
        cur_tid = frame_speaker_assignments[0][1]
        seg_start = frame_speaker_assignments[0][0]
        seg_scores: List[float] = [frame_speaker_assignments[0][2]]

        for t, tid, score in frame_speaker_assignments[1:]:
            if tid == cur_tid:
                seg_scores.append(score)
            else:
                timeline_segments.append(
                    SpeakerSegment(
                        start=round(seg_start, 2),
                        end=round(t, 2),
                        track_id=cur_tid,
                        confidence=round(float(np.mean(seg_scores)), 3),
                    )
                )
                cur_tid = tid
                seg_start = t
                seg_scores = [score]

        last_t = frame_speaker_assignments[-1][0]
        end_t = total_duration if total_duration > last_t else (last_t + 0.25)
        timeline_segments.append(
            SpeakerSegment(
                start=round(seg_start, 2),
                end=round(end_t, 2),
                track_id=cur_tid,
                confidence=round(float(np.mean(seg_scores)), 3),
            )
        )

        return SpeakerTimeline(
            segments=timeline_segments,
            active_tracks=active_track_ids,
            speaker_mode="active_speaker",
            fallback_reason=None,
        )
