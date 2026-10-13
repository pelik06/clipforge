import math
import subprocess
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from core.config.settings import Settings
from core.models.candidate import CandidateMoment
from core.models.transcript import TranscriptSegment


class SignalDetector:
    """Analyze entire source video timeline to locate candidate highlight moments.
    
    Inspired by OpenShorts acoustic and transcript boundary analysis.
    Uses real acoustic energy envelope, silence boundaries, and sentence boundaries.
    """

    def __init__(self):
        self.settings = Settings()

    def get_media_duration(self, media_path: str) -> float:
        """Probe exact media duration using ffprobe."""
        cmd = [
            self.settings.ffprobe_bin,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "csv=p=0",
            str(media_path),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and res.stdout.strip():
            try:
                return float(res.stdout.strip())
            except ValueError:
                pass
        return 15.0

    def compute_audio_energy_profile(self, media_path: str) -> Tuple[np.ndarray, float]:
        """Extract fast 16kHz mono audio and compute RMS energy over 0.5s windows across entire video."""
        work_dir = Path("data/work")
        work_dir.mkdir(parents=True, exist_ok=True)
        temp_wav = work_dir / f"energy_{Path(media_path).stem}.wav"

        cmd = [
            self.settings.ffmpeg_bin,
            "-y",
            "-i", str(media_path),
            "-vn",
            "-ac", "1",
            "-ar", "16000",
            "-f", "wav",
            str(temp_wav),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        if proc.returncode != 0 or not temp_wav.exists() or temp_wav.stat().st_size < 100:
            return np.array([1.0]), 1.0

        try:
            with wave.open(str(temp_wav), "rb") as wf:
                rate = wf.getframerate()
                n_frames = wf.getnframes()
                raw_bytes = wf.readframes(n_frames)
            temp_wav.unlink(missing_ok=True)

            audio = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32)
            if len(audio) == 0:
                return np.array([1.0]), 1.0

            # 0.5-second windows (8000 samples at 16kHz)
            win_size = int(rate * 0.5)
            num_windows = max(1, len(audio) // win_size)
            energies = []
            for i in range(num_windows):
                chunk = audio[i * win_size : (i + 1) * win_size]
                rms = float(np.sqrt(np.mean(chunk**2) + 1e-6))
                energies.append(rms)

            energy_arr = np.array(energies, dtype=np.float32)
            mean_e = float(np.mean(energy_arr)) + 1e-5
            # Normalize relative to mean energy
            norm_energies = energy_arr / mean_e
            return norm_energies, mean_e
        except Exception:
            if temp_wav.exists():
                temp_wav.unlink(missing_ok=True)
            return np.array([1.0]), 1.0

    def detect(
        self,
        media_path: str,
        transcript_segments: Optional[List[TranscriptSegment]] = None,
        min_clip_seconds: float = 5.0,
        max_clip_seconds: float = 25.0,
    ) -> List[CandidateMoment]:
        """Detect candidate moments across the entire video timeline with variable durations."""
        duration = self.get_media_duration(media_path)
        energy_profile, _ = self.compute_audio_energy_profile(media_path)
        win_duration = 0.5  # each energy index is 0.5s

        # Helper to get energy metrics for a time range
        def get_range_energy(start_t: float, end_t: float) -> Tuple[float, float]:
            idx_start = max(0, int(start_t / win_duration))
            idx_end = min(len(energy_profile), int(end_t / win_duration) + 1)
            if idx_start >= idx_end or idx_start >= len(energy_profile):
                return 0.5, 0.5
            slice_e = energy_profile[idx_start:idx_end]
            mean_val = float(np.mean(slice_e))
            max_val = float(np.max(slice_e))
            return mean_val, max_val

        candidates: List[CandidateMoment] = []

        # Strategy 1: Sentence-aware candidate generation when transcript is available
        if transcript_segments and len(transcript_segments) > 0:
            num_segs = len(transcript_segments)
            for i in range(num_segs):
                cum_words = 0
                for j in range(i, min(num_segs, i + 5)):
                    t_start = max(0.0, transcript_segments[i].start - 0.3)
                    t_end = min(duration, transcript_segments[j].end + 0.4)
                    cand_dur = t_end - t_start

                    if cand_dur < min_clip_seconds:
                        continue
                    if cand_dur > max_clip_seconds:
                        break

                    # Count total words in candidate
                    words_in_window = sum(
                        len(seg.words) if seg.words else len(seg.text.split())
                        for seg in transcript_segments[i : j + 1]
                    )

                    mean_e, max_e = get_range_energy(t_start, t_end)
                    speech_density = min(1.0, (words_in_window / cand_dur) / 3.5)
                    energy_norm = min(1.0, mean_e / 2.0)
                    reaction_norm = min(1.0, max_e / 3.0)

                    # Ideal viral duration sweet spot: 8s - 16s
                    duration_score = max(0.0, 1.0 - abs(cand_dur - 12.0) / 16.0)

                    signals = {
                        "audio_energy": energy_norm,
                        "reaction_signal": reaction_norm,
                        "speech_density": speech_density,
                        "sentence_completeness": 1.0,
                        "duration_score": duration_score,
                    }

                    candidates.append(
                        CandidateMoment(
                            start=round(t_start, 2),
                            end=round(t_end, 2),
                            signals=signals,
                        )
                    )

        # Strategy 2: Acoustic Peak & Activity Analysis (if no transcript or to augment)
        if len(candidates) < 3:
            # Find acoustic peaks across timeline
            num_wins = len(energy_profile)
            step_wins = max(1, int(3.0 / win_duration))  # test every ~3 seconds
            target_durations = [7.5, 11.0, 15.0, 18.5]

            for w_idx in range(0, num_wins, step_wins):
                t_center = w_idx * win_duration
                if t_center >= duration:
                    break

                for dur in target_durations:
                    c_start = max(0.0, t_center - (dur * 0.35))
                    c_end = min(duration, c_start + dur)
                    actual_dur = c_end - c_start
                    if actual_dur < min_clip_seconds:
                        continue

                    mean_e, max_e = get_range_energy(c_start, c_end)
                    energy_norm = min(1.0, mean_e / 2.0)
                    reaction_norm = min(1.0, max_e / 3.0)
                    duration_score = max(0.0, 1.0 - abs(actual_dur - 12.0) / 16.0)

                    signals = {
                        "audio_energy": energy_norm,
                        "reaction_signal": reaction_norm,
                        "speech_density": 0.5,
                        "sentence_completeness": 0.5,
                        "duration_score": duration_score,
                    }

                    candidates.append(
                        CandidateMoment(
                            start=round(c_start, 2),
                            end=round(c_end, 2),
                            signals=signals,
                        )
                    )

        # Fallback if video is very short
        if not candidates:
            cand_dur = min(duration, 12.0)
            candidates.append(
                CandidateMoment(
                    start=0.0,
                    end=round(cand_dur, 2),
                    signals={
                        "audio_energy": 0.7,
                        "reaction_signal": 0.7,
                        "speech_density": 0.6,
                        "sentence_completeness": 0.7,
                        "duration_score": 0.8,
                    },
                )
            )

        return candidates
