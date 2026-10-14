import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from core.models.candidate import CandidateMoment
from core.models.transcript import SentenceWindow, ThoughtWindow, TranscriptSegment, Word
from services.detection.analyzer import MultiSignalAnalyzer, WindowSignal, HOOK_PATTERN_REGEX
from services.detection.thought_detector import ThoughtDetector, extract_sentences


@dataclass
class ScorerWeights:
    speech_density: float = 0.15
    audio_energy: float = 0.10
    audio_peak: float = 0.10
    sentence_completeness: float = 0.15
    thought_completeness: float = 0.20
    hook_strength: float = 0.10
    payoff_strength: float = 0.10
    boundary_quality: float = 0.05
    scene_quality: float = 0.05


class NonLLMMomentDetector:
    """Transcript-Driven and Multi-Signal Moment Detection Pipeline.

    Architecture:
    1. Sentence & Thought Window segmentation from Whisper transcript.
    2. Hook -> Development -> Payoff conversational thought alignment.
    3. Strict duration enforcement (MIN_CLIP_DURATION 15s to MAX_CLIP_DURATION 60s).
    4. Full-window quality scoring across speech, acoustic, and narrative dimensions.
    5. Incomplete speech penalties (dangling start/end conjunctions, zero-start bumper penalty).
    6. Strict deduplication (IoU <= 0.35 AND containment <= 0.50).
    7. Dynamic output count matching true valid moments (0 to N).
    """

    def __init__(
        self,
        weights: Optional[ScorerWeights] = None,
        moment_threshold: float = 0.45,
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
        max_clips: int = 10,
        moment_threshold: Optional[float] = None,
    ) -> List[CandidateMoment]:
        """Detect all valid, non-overlapping highlight moments across the entire video timeline."""
        raw_thresh = moment_threshold if moment_threshold is not None else self.moment_threshold
        thresh_100 = raw_thresh * 100.0 if raw_thresh <= 1.0 else raw_thresh

        total_duration = self.analyzer.get_media_duration(media_path)
        if total_duration < min_clip_duration:
            # Source video shorter than minimum required clip duration -> NO_VALID_MOMENTS
            return []

        # 1. Multi-signal continuous extraction
        energy_arr, peak_arr, silences = self.analyzer.compute_audio_profile(media_path)
        motion_profile = self.analyzer.compute_motion_profile(media_path, sample_fps=4.0)
        face_profile = self.analyzer.compute_face_profile(media_path, sample_fps=2.5)
        scenes = self.analyzer.compute_scene_cuts(media_path)

        td = ThoughtDetector(
            min_clip_duration=min_clip_duration,
            max_clip_duration=max_clip_duration,
            max_overlap_ratio=self.max_overlap_ratio,
            max_containment_ratio=0.50,
        )

        # 2. Primary Path: Transcript-Driven Thought Windowing
        if transcript_segments and len(transcript_segments) > 0:
            sentences = extract_sentences(transcript_segments)
            thought_windows = td.identify_thought_windows(
                sentences,
                total_duration=total_duration,
                silences=silences,
                scenes=scenes,
            )

            raw_candidates: List[CandidateMoment] = []
            for tw in thought_windows:
                dur = tw.duration
                # STRICT check: enforce 15s to 60s
                if dur < min_clip_duration or dur > max_clip_duration:
                    continue

                score = td.score_thought_window(
                    tw,
                    energy_arr=energy_arr,
                    peak_arr=peak_arr,
                    motion_profile=motion_profile,
                    face_profile=face_profile,
                    scenes=scenes,
                    silences=silences,
                    total_duration=total_duration,
                )

                if score < thresh_100:
                    continue

                reasons = []
                if tw.has_hook:
                    reasons.append("Strong opening conversational hook")
                if tw.has_payoff:
                    reasons.append("Complete resolution & payoff")
                reasons.append(f"Complete conversational thought ({dur:.1f}s)")

                # Extract signals across the full thought window
                i0 = max(0, int(tw.start / 0.5))
                i1 = min(len(energy_arr), int(tw.end / 0.5) + 1)
                sub_e = float(np.mean(energy_arr[i0:i1])) if i0 < i1 and len(energy_arr) > 0 else 0.5
                sub_p = float(np.max(peak_arr[i0:i1])) if i0 < i1 and len(peak_arr) > 0 else 0.5

                spoken_dur = sum([w.end - w.start for w in tw.words]) if tw.words else dur * 0.7
                speech_dens = min(1.0, max(0.0, spoken_dur / dur))

                signals = {
                    "speech_density": round(speech_dens, 3),
                    "audio_energy": round(sub_e, 3),
                    "audio_peak": round(sub_p, 3),
                    "sentence_completeness": 1.0,
                    "thought_completeness": 1.0 if tw.has_hook and tw.has_payoff else 0.75,
                    "hook_strength": 1.0 if tw.has_hook else 0.4,
                    "payoff_strength": 1.0 if tw.has_payoff else 0.4,
                }

                raw_candidates.append(
                    CandidateMoment(
                        start=round(tw.start, 2),
                        end=round(tw.end, 2),
                        score=round(score, 1),
                        reasons=reasons,
                        signals=signals,
                    )
                )

            # Strict distinct-thought deduplication
            valid_moments = td.deduplicate_thoughts(raw_candidates, max_clips=max_clips)
            return valid_moments

        # 3. Fallback Path: Acoustic + Visual Scene Boundaries (when transcript is unavailable)
        candidates: List[CandidateMoment] = []
        if scenes:
            for sc in scenes:
                dur = sc["duration"]
                if dur >= min_clip_duration and dur <= max_clip_duration:
                    score = 72.0
                    if sc.get("start", 0) < 1.0:
                        score -= 30.0
                    if score < thresh_100:
                        continue
                    candidates.append(
                        CandidateMoment(
                            start=round(sc["start"], 2),
                            end=round(sc["end"], 2),
                            score=score,
                            reasons=["Visual scene cut boundary window"],
                            signals={"duration": dur},
                        )
                    )

        return td.deduplicate_thoughts(candidates, max_clips=max_clips)
