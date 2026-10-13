import math
import os
import re
import subprocess
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from core.config.settings import Settings
from core.models.transcript import TranscriptSegment, Word


HOOK_PATTERN_REGEX = re.compile(
    r"\b(ternyata|tapi|namun|akhirnya|hasilnya|serius|gila|kenapa|bagaimana|tidak menyangka|"
    r"omg|wow|listen|look|wait|secret|trick|best|never|always|truth|story|remember|watch)\b",
    re.IGNORECASE,
)


@dataclass
class WindowSignal:
    timestamp: float
    start: float
    end: float
    speech_density: float = 0.0
    audio_energy: float = 0.0
    audio_peak: float = 0.0
    motion_score: float = 0.0
    scene_change_score: float = 0.0
    face_activity: float = 0.0
    sentence_completeness: float = 0.0
    silence_boundary: float = 0.0
    hook_pattern: float = 0.0
    object_activity: float = 0.0
    moment_score: float = 0.0


class MultiSignalAnalyzer:
    """Analyze full video across multiple independent audio, visual, and transcript signals.
    
    Signals:
    1. Audio Energy (RMS, energy delta, volume peaks)
    2. Speech Density (words/sec in window from faster-whisper)
    3. Silence Boundaries (pre/post silence intervals)
    4. Motion Score (sampled frame differences)
    5. Scene Changes (TransNetV2 / PySceneDetect / OpenCV histogram)
    6. Face Activity (MediaPipe / OpenCV YuNet count, position, movement)
    7. Object/Person Activity (YOLO / object presence)
    8. Transcript Features (sentence boundaries, punctuation, hook keywords)
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()

    def get_media_duration(self, media_path: str) -> float:
        """Extract media duration via ffprobe."""
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
        return 30.0

    def compute_audio_profile(self, media_path: str) -> Tuple[np.ndarray, np.ndarray, List[Tuple[float, float]]]:
        """Extract audio track, compute short-term RMS energy in 0.5s windows, and identify silence troughs."""
        work_dir = Path("data/work")
        work_dir.mkdir(parents=True, exist_ok=True)
        temp_wav = work_dir / f"audio_prof_{Path(media_path).stem}.wav"

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
            return np.array([0.5]), np.array([0.5]), []

        try:
            with wave.open(str(temp_wav), "rb") as wf:
                rate = wf.getframerate()
                n_frames = wf.getnframes()
                raw_bytes = wf.readframes(n_frames)
            temp_wav.unlink(missing_ok=True)

            audio = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32)
            if len(audio) == 0:
                return np.array([0.5]), np.array([0.5]), []

            # 0.5s windows (8000 samples)
            win_size = int(rate * 0.5)
            num_windows = max(1, len(audio) // win_size)
            energies = []
            peaks = []
            silences = []

            silence_thresh = 0.08 * (np.max(np.abs(audio)) + 1e-5)

            for i in range(num_windows):
                chunk = audio[i * win_size : (i + 1) * win_size]
                rms = float(np.sqrt(np.mean(chunk**2) + 1e-6))
                peak_val = float(np.max(np.abs(chunk))) if len(chunk) > 0 else 0.0
                energies.append(rms)
                peaks.append(peak_val)

                if rms < silence_thresh:
                    t_start = i * 0.5
                    t_end = (i + 1) * 0.5
                    silences.append((t_start, t_end))

            energy_arr = np.array(energies, dtype=np.float32)
            peak_arr = np.array(peaks, dtype=np.float32)

            # Normalize to 0.0-1.0
            max_e = float(np.max(energy_arr)) + 1e-5
            max_p = float(np.max(peak_arr)) + 1e-5
            norm_e = np.clip(energy_arr / max_e, 0.0, 1.0)
            norm_p = np.clip(peak_arr / max_p, 0.0, 1.0)

            return norm_e, norm_p, silences
        except Exception:
            if temp_wav.exists():
                temp_wav.unlink(missing_ok=True)
            return np.array([0.5]), np.array([0.5]), []

    def compute_motion_profile(self, media_path: str, sample_fps: float = 4.0) -> List[Tuple[float, float]]:
        """Compute optical/frame difference motion score across sampled frames."""
        cap = cv2.VideoCapture(str(media_path))
        if not cap.isOpened():
            return []

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        sample_step = max(1, int(round(fps / sample_fps)))
        prev_gray = None
        motion_profile: List[Tuple[float, float]] = []
        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % sample_step == 0:
                t_sec = frame_idx / fps
                small = cv2.resize(frame, (256, 144))
                gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
                if prev_gray is not None:
                    diff = cv2.absdiff(gray, prev_gray)
                    # Normalize mean difference (typically 0-40) to 0.0-1.0
                    m_score = min(1.0, float(np.mean(diff)) / 25.0)
                    motion_profile.append((t_sec, m_score))
                else:
                    motion_profile.append((t_sec, 0.2))
                prev_gray = gray
            frame_idx += 1

        cap.release()
        return motion_profile

    def compute_face_profile(self, media_path: str, sample_fps: float = 2.5) -> List[Tuple[float, float, int]]:
        """Compute face presence, size, and activity across sampled frames."""
        model_path = Path(__file__).resolve().parent.parent / "reframing" / "models" / "face_detection_yunet_2023mar.onnx"
        detector = None
        if model_path.exists():
            try:
                detector = cv2.FaceDetectorYN.create(str(model_path), "", (320, 180), score_threshold=0.55)
            except Exception:
                pass

        cap = cv2.VideoCapture(str(media_path))
        if not cap.isOpened():
            return []

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        sample_step = max(1, int(round(fps / sample_fps)))
        face_profile: List[Tuple[float, float, int]] = []
        frame_idx = 0
        last_cx, last_cy = 160.0, 90.0

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % sample_step == 0:
                t_sec = frame_idx / fps
                small = cv2.resize(frame, (320, 180))
                face_score = 0.0
                face_count = 0

                if detector is not None:
                    try:
                        detector.setInputSize((320, 180))
                        _, faces = detector.detect(small)
                        if faces is not None and len(faces) > 0:
                            face_count = len(faces)
                            primary = faces[0]
                            fw, fh = float(primary[2]), float(primary[3])
                            cx = float(primary[0]) + fw / 2.0
                            cy = float(primary[1]) + fh / 2.0
                            area_ratio = min(1.0, (fw * fh) / (320 * 180 * 0.25))
                            movement = min(1.0, math.hypot(cx - last_cx, cy - last_cy) / 80.0)
                            last_cx, last_cy = cx, cy
                            face_score = min(1.0, (area_ratio * 0.7) + (movement * 0.3) + 0.2)
                    except Exception:
                        pass
                else:
                    face_score = 0.5

                face_profile.append((t_sec, face_score, face_count))
            frame_idx += 1

        cap.release()
        return face_profile

    def compute_scene_cuts(self, media_path: str) -> List[Dict[str, float]]:
        """Identify visual scene cuts using PySceneDetect ContentDetector, falling back to OpenCV histogram."""
        try:
            from scenedetect import ContentDetector, detect  # type: ignore

            scene_list = detect(str(media_path), ContentDetector(threshold=27.0))
            if scene_list:
                result = []
                for sc in scene_list:
                    s_t = sc[0].seconds if hasattr(sc[0], "seconds") else float(sc[0].get_seconds())
                    e_t = sc[1].seconds if hasattr(sc[1], "seconds") else float(sc[1].get_seconds())
                    result.append({"start": round(s_t, 2), "end": round(e_t, 2), "duration": round(e_t - s_t, 2)})
                return result
        except Exception:
            pass

        # OpenCV HSV histogram fallback
        from services.detection.scene import SceneDetector
        return SceneDetector().detect_scenes(media_path)
