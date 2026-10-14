import math
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

from core.config.settings import Settings


class SceneDetector:
    """Analyze full video to identify natural visual scene boundaries.
    
    Inspired by OpenShorts PySceneDetect / ContentDetector approach.
    Uses HSV color histogram correlation across sampled frames.
    """

    def __init__(self, correlation_threshold: float = 0.58, sample_fps: float = 2.5):
        self.settings = Settings()
        self.correlation_threshold = correlation_threshold
        self.sample_fps = sample_fps

    def detect_scenes(
        self,
        media_path: str,
        min_scene_duration: float = 2.0,
    ) -> List[Dict[str, float]]:
        """Return list of detected scenes with start, end, and duration timestamps."""
        cap = cv2.VideoCapture(str(media_path))
        if not cap.isOpened():
            return [{"start": 0.0, "end": 30.0, "duration": 30.0}]

        video_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        total_duration = total_frames / video_fps if total_frames > 0 else 30.0

        sample_step = max(1, int(round(video_fps / self.sample_fps)))
        scene_boundaries: List[float] = [0.0]
        prev_hist = None
        frame_idx = 0

        while True:
            if frame_idx % sample_step == 0:
                ret, frame = cap.read()
                if not ret:
                    break
                t_sec = round(frame_idx / video_fps, 2)
                thumb = cv2.resize(frame, (160, 90))
                hsv = cv2.cvtColor(thumb, cv2.COLOR_BGR2HSV)
                hist = cv2.calcHist([hsv], [0, 1], None, [16, 16], [0, 180, 0, 256])
                cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)

                if prev_hist is not None:
                    score = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)
                    if score < self.correlation_threshold:
                        if (t_sec - scene_boundaries[-1]) >= min_scene_duration:
                            scene_boundaries.append(t_sec)

                prev_hist = hist
            else:
                if not cap.grab():
                    break

            frame_idx += 1

        cap.release()

        if total_duration - scene_boundaries[-1] > 1.0:
            scene_boundaries.append(round(total_duration, 2))
        elif len(scene_boundaries) == 1:
            scene_boundaries.append(round(total_duration, 2))

        scenes: List[Dict[str, float]] = []
        for i in range(len(scene_boundaries) - 1):
            s_start = scene_boundaries[i]
            s_end = scene_boundaries[i + 1]
            scenes.append({
                "start": s_start,
                "end": s_end,
                "duration": round(s_end - s_start, 2),
            })

        return scenes
