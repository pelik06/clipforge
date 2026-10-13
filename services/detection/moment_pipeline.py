import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from core.models.candidate import CandidateMoment
from core.models.transcript import TranscriptSegment, Word
from services.detection.analyzer import MultiSignalAnalyzer, WindowSignal, HOOK_PATTERN_REGEX


@dataclass
class ScorerWeights:
    speech_density: float = 0.20
    audio_energy: float = 0.15
    audio_peak: float = 0.10
    motion_score: float = 0.10
    scene_change_score: float = 0.10
    face_activity: float = 0.10
    sentence_completeness: float = 0.10
    silence_boundary: float = 0.05
    hook_pattern: float = 0.05
    object_activity: float = 0.05


class NonLLMMomentDetector:
    """Non-LLM Multi-Signal Moment Detection and Clipping Pipeline.
    
    Phases:
    1. Multi-signal continuous extraction (audio, speech, silence, motion, scenes, face, transcript)
    2. Sliding window scoring (5s window, 1s step) with normalized feature weights
    3. Local peak detection across full video timeline
    4. Candidate expansion (hook/context -> development -> payoff/sentence end)
    5. Word boundary snapping (nearest word start and word end from Whisper)
    6. Scene cut alignment
    7. Temporal deduplication (NMS with max overlap 0.35)
    8. Dynamic clip count matching true detected moments (0 to N)
    """

    def __init__(
        self,
        weights: Optional[ScorerWeights] = None,
        moment_threshold: float = 0.65,
        window_size: float = 5.0,
        window_step: float = 1.0,
        max_overlap_ratio: float = 0.35,
    ):
        self.weights = weights or ScorerWeights()
        self.moment_threshold = moment_threshold
        self.window_size = window_size
        self.window_step = window_step
        self.max_overlap_ratio = max_overlap_ratio
        self.analyzer = MultiSignalAnalyzer()

    def detect_moments(
        self,
        media_path: str,
        transcript_segments: Optional[List[TranscriptSegment]] = None,
        min_clip_duration: float = 15.0,
        max_clip_duration: float = 60.0,
        max_clips: int = 15,
        moment_threshold: Optional[float] = None,
    ) -> List[CandidateMoment]:
        """Detect all valid, non-overlapping highlight moments across the entire video timeline."""
        thresh = moment_threshold if moment_threshold is not None else self.moment_threshold
        total_duration = self.analyzer.get_media_duration(media_path)
        if total_duration < 3.0:
            return []

        # 1. Multi-signal extraction across full timeline
        energy_arr, peak_arr, silences = self.analyzer.compute_audio_profile(media_path)
        motion_profile = self.analyzer.compute_motion_profile(media_path, sample_fps=4.0)
        face_profile = self.analyzer.compute_face_profile(media_path, sample_fps=2.5)
        scenes = self.analyzer.compute_scene_cuts(media_path)

        # Build lookup helpers for continuous signals
        def get_avg_motion(t0: float, t1: float) -> float:
            pts = [m for (t, m) in motion_profile if t0 <= t <= t1]
            return float(np.mean(pts)) if pts else 0.2

        def get_avg_face(t0: float, t1: float) -> float:
            pts = [f for (t, f, _) in face_profile if t0 <= t <= t1]
            return float(np.mean(pts)) if pts else 0.3

        def get_audio_window(t0: float, t1: float) -> Tuple[float, float]:
            i0 = max(0, int(t0 / 0.5))
            i1 = min(len(energy_arr), int(t1 / 0.5) + 1)
            if i0 >= i1 or i0 >= len(energy_arr):
                return 0.3, 0.3
            e_sub = energy_arr[i0:i1]
            p_sub = peak_arr[i0:i1]
            return float(np.mean(e_sub)), float(np.max(p_sub))

        def has_nearby_scene_cut(t0: float, t1: float) -> float:
            for sc in scenes:
                if (abs(t0 - sc["start"]) <= 1.5) or (abs(t1 - sc["end"]) <= 1.5):
                    return 1.0
            return 0.0

        def has_silence_boundary(t0: float, t1: float) -> float:
            for s_start, s_end in silences:
                if abs(t0 - s_end) <= 1.0 or abs(t1 - s_start) <= 1.0:
                    return 1.0
            return 0.2

        # Flatten transcript words
        all_words: List[Word] = []
        if transcript_segments:
            for s in transcript_segments:
                if s.words:
                    all_words.extend(s.words)
                else:
                    tokens = s.text.split()
                    if tokens:
                        dt = max(0.1, (s.end - s.start) / len(tokens))
                        for k, tok in enumerate(tokens):
                            all_words.append(Word(tok, round(s.start + k * dt, 2), round(s.start + (k + 1) * dt, 2)))

        # 2. Sliding Window Scoring
        windows: List[WindowSignal] = []
        w_size = self.window_size
        step = self.window_step
        curr_t = 0.0

        while curr_t + w_size <= total_duration + 0.5:
            w_start = curr_t
            w_end = min(total_duration, curr_t + w_size)
            mid_t = (w_start + w_end) / 2.0

            # Speech density in window
            words_in_w = [w for w in all_words if w.start >= w_start and w.end <= w_end]
            w_text = " ".join([w.text for w in words_in_w])
            speech_rate = len(words_in_w) / max(0.5, (w_end - w_start))
            norm_speech_density = min(1.0, speech_rate / 4.0)

            # Audio
            mean_e, max_p = get_audio_window(w_start, w_end)
            motion_val = get_avg_motion(w_start, w_end)
            scene_val = has_nearby_scene_cut(w_start, w_end)
            face_val = get_avg_face(w_start, w_end)
            silence_val = has_silence_boundary(w_start, w_end)

            # Sentence completeness
            has_ending = bool(re.search(r"[.!?]", w_text))
            sentence_completeness = 1.0 if has_ending else 0.4

            # Hook pattern regex
            hook_val = 1.0 if HOOK_PATTERN_REGEX.search(w_text) else 0.2
            object_val = 0.5

            raw_signal = WindowSignal(
                timestamp=round(mid_t, 2),
                start=round(w_start, 2),
                end=round(w_end, 2),
                speech_density=round(norm_speech_density, 3),
                audio_energy=round(mean_e, 3),
                audio_peak=round(max_p, 3),
                motion_score=round(motion_val, 3),
                scene_change_score=round(scene_val, 3),
                face_activity=round(face_val, 3),
                sentence_completeness=round(sentence_completeness, 3),
                silence_boundary=round(silence_val, 3),
                hook_pattern=round(hook_val, 3),
                object_activity=round(object_val, 3),
                moment_score=0.0,
            )
            windows.append(raw_signal)
            curr_t += step

        if not windows:
            return []

        # Min-Max Normalization across all windows to span full 0.0-1.0 range
        def norm_series(vals: List[float]) -> np.ndarray:
            arr = np.array(vals, dtype=np.float32)
            rng = float(np.max(arr) - np.min(arr))
            if rng > 1e-4:
                return (arr - float(np.min(arr))) / rng
            return np.full_like(arr, 0.5)

        n_speech = norm_series([w.speech_density for w in windows])
        n_energy = norm_series([w.audio_energy for w in windows])
        n_peak = norm_series([w.audio_peak for w in windows])
        n_motion = norm_series([w.motion_score for w in windows])
        n_face = norm_series([w.face_activity for w in windows])

        for i, w in enumerate(windows):
            w_score = (
                self.weights.speech_density * float(n_speech[i])
                + self.weights.audio_energy * float(n_energy[i])
                + self.weights.audio_peak * float(n_peak[i])
                + self.weights.motion_score * float(n_motion[i])
                + self.weights.scene_change_score * w.scene_change_score
                + self.weights.face_activity * float(n_face[i])
                + self.weights.sentence_completeness * w.sentence_completeness
                + self.weights.silence_boundary * w.silence_boundary
                + self.weights.hook_pattern * w.hook_pattern
                + self.weights.object_activity * w.object_activity
            )
            w.moment_score = round(float(w_score), 3)
        if not windows:
            return []

        # 3. Local Peak Detection across entire timeline
        peaks: List[WindowSignal] = []
        n_win = len(windows)
        for i in range(n_win):
            w = windows[i]
            if w.moment_score < thresh:
                continue
            is_local_max = True
            if i > 0 and windows[i - 1].moment_score > w.moment_score:
                is_local_max = False
            if i < n_win - 1 and windows[i + 1].moment_score > w.moment_score:
                is_local_max = False
            if is_local_max:
                peaks.append(w)

        # If strict local maxima found none, check top scoring windows meeting threshold
        if not peaks:
            sorted_by_score = sorted(windows, key=lambda x: x.moment_score, reverse=True)
            for w in sorted_by_score:
                if w.moment_score >= thresh:
                    peaks.append(w)
                    break

        if not peaks:
            # Zero moments met the threshold -> strictly return empty list per Critical Rule!
            return []

        # 4. Candidate Expansion around each peak
        expanded_candidates: List[CandidateMoment] = []

        for p in peaks:
            peak_t = p.timestamp

            # Target duration around peak
            target_dur = min(max_clip_duration, max(min_clip_duration, 20.0))
            half_dur = target_dur / 2.0
            cand_start = max(0.0, peak_t - half_dur)
            cand_end = min(total_duration, peak_t + half_dur)

            # Snap to transcript sentence boundaries if transcript available
            if transcript_segments:
                best_start = cand_start
                best_end = cand_end
                for s in transcript_segments:
                    # Find sentence start near cand_start
                    if abs(s.start - cand_start) <= 4.0:
                        best_start = s.start
                        break
                for s in transcript_segments:
                    # Find sentence end near cand_end
                    if abs(s.end - cand_end) <= 5.0 and s.end > best_start:
                        best_end = s.end

                cand_start = max(0.0, best_start - 0.25)
                cand_end = min(total_duration, best_end + 0.35)

            # 5. Snap to Word Boundaries from faster-whisper
            if all_words:
                nearby_start_words = [w for w in all_words if abs(w.start - cand_start) <= 2.0]
                if nearby_start_words:
                    cand_start = min(nearby_start_words, key=lambda w: abs(w.start - cand_start)).start

                nearby_end_words = [w for w in all_words if abs(w.end - cand_end) <= 2.0]
                if nearby_end_words:
                    cand_end = max(nearby_end_words, key=lambda w: abs(w.end - cand_end)).end

            # Ensure duration bounds
            actual_dur = cand_end - cand_start
            if actual_dur < min_clip_duration:
                # Expand symmetrically if needed
                deficit = min_clip_duration - actual_dur
                cand_start = max(0.0, cand_start - deficit / 2.0)
                cand_end = min(total_duration, cand_end + deficit / 2.0)
            elif actual_dur > max_clip_duration:
                cand_end = cand_start + max_clip_duration

            final_dur = cand_end - cand_start

            # Calculate feature breakdown for candidate
            reasons = []
            if p.speech_density > 0.6:
                reasons.append("High speech density & engagement")
            if p.audio_energy > 0.6:
                reasons.append("Strong acoustic volume energy")
            if p.motion_score > 0.5:
                reasons.append("Visual action & motion activity")
            if p.face_activity > 0.5:
                reasons.append("Active speaker close-up framing")
            if p.hook_pattern > 0.5:
                reasons.append("Viral hook keyword pattern")
            if not reasons:
                reasons.append(f"Highlight moment ({final_dur:.1f}s)")

            features = {
                "audio": p.audio_energy,
                "audio_peak": p.audio_peak,
                "speech_density": p.speech_density,
                "motion": p.motion_score,
                "face_activity": p.face_activity,
                "sentence_completeness": p.sentence_completeness,
            }

            expanded_candidates.append(
                CandidateMoment(
                    start=round(cand_start, 2),
                    end=round(cand_end, 2),
                    score=round(min(98.0, p.moment_score * 100.0), 1),
                    reasons=reasons,
                    signals=features,
                )
            )

        # 6. Temporal Deduplication (Non-Maximum Suppression)
        expanded_candidates.sort(key=lambda c: c.score, reverse=True)
        unique_moments: List[CandidateMoment] = []

        for cand in expanded_candidates:
            is_dup = False
            for prev in unique_moments:
                overlap_start = max(cand.start, prev.start)
                overlap_end = min(cand.end, prev.end)
                if overlap_end > overlap_start:
                    overlap_dur = overlap_end - overlap_start
                    min_d = min(cand.duration, prev.duration)
                    if (overlap_dur / min_d) > self.max_overlap_ratio:
                        is_dup = True
                        break
            if not is_dup:
                unique_moments.append(cand)
                if len(unique_moments) >= max_clips:
                    break

        return unique_moments
