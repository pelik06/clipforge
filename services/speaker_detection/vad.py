from typing import List, Optional, Union
import numpy as np

from services.speaker_detection.models import SpeechSegment


class VoiceActivityDetector:
    """Local Voice Activity Detection (VAD) analyzing audio energy and speech cadence."""

    def __init__(self, sample_rate: int = 16000, frame_duration_ms: int = 50, energy_threshold_ratio: float = 1.35):
        self.sample_rate = sample_rate
        self.frame_len = int(sample_rate * (frame_duration_ms / 1000.0))
        self.hop_len = self.frame_len // 2
        self.energy_threshold_ratio = energy_threshold_ratio

    def detect_from_pcm(self, pcm_data: np.ndarray) -> List[SpeechSegment]:
        """Detect speech segments from 1D float32 numpy audio PCM buffer."""
        if len(pcm_data) < self.frame_len:
            return []

        # Compute RMS per frame
        n_frames = (len(pcm_data) - self.frame_len) // self.hop_len + 1
        rms_values = np.zeros(n_frames, dtype=np.float32)

        for i in range(n_frames):
            start_sample = i * self.hop_len
            frame = pcm_data[start_sample : start_sample + self.frame_len]
            rms_values[i] = np.sqrt(np.mean(frame**2) + 1e-9)

        # Dynamic threshold based on median/noise floor
        noise_floor = float(np.percentile(rms_values, 25))
        threshold = max(0.005, noise_floor * self.energy_threshold_ratio)

        # Flag frames as speech
        is_speech = rms_values > threshold

        # Group consecutive speech frames with 250ms hang-over smoothing
        hangover_frames = int(0.25 / (self.hop_len / float(self.sample_rate)))
        smooth_speech = np.copy(is_speech)
        silence_count = 0
        in_speech = False

        for i in range(len(is_speech)):
            if is_speech[i]:
                in_speech = True
                silence_count = 0
                smooth_speech[i] = True
            elif in_speech:
                silence_count += 1
                if silence_count <= hangover_frames:
                    smooth_speech[i] = True
                else:
                    in_speech = False

        # Convert to SpeechSegment intervals
        segments: List[SpeechSegment] = []
        seg_start = None

        dt = self.hop_len / float(self.sample_rate)
        for i in range(len(smooth_speech)):
            t = i * dt
            if smooth_speech[i] and seg_start is None:
                seg_start = t
            elif not smooth_speech[i] and seg_start is not None:
                if (t - seg_start) >= 0.2:  # Min speech segment duration 200ms
                    # Calculate mean energy confidence
                    i0 = int(seg_start / dt)
                    conf = min(1.0, float(np.mean(rms_values[i0 : i + 1])) / max(0.01, threshold * 2.0))
                    segments.append(SpeechSegment(start=round(seg_start, 2), end=round(t, 2), confidence=round(max(0.5, conf), 2)))
                seg_start = None

        if seg_start is not None and ((len(smooth_speech) * dt) - seg_start) >= 0.2:
            t_end = len(smooth_speech) * dt
            segments.append(SpeechSegment(start=round(seg_start, 2), end=round(t_end, 2), confidence=0.85))

        return segments

    def detect_from_transcript(self, transcript_segments: list) -> List[SpeechSegment]:
        """Convert verified speech segments into VAD SpeechSegment signals."""
        vad_segments: List[SpeechSegment] = []
        for s in transcript_segments:
            vad_segments.append(
                SpeechSegment(
                    start=round(float(s.start), 2),
                    end=round(float(s.end), 2),
                    confidence=0.95,
                )
            )
        return vad_segments
