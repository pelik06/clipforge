from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np

from services.speaker_detection.models import MouthActivity


class MouthActivityDetector:
    """Detects mouth motion and lower-face dynamics across persistent face tracks."""

    def __init__(self, sample_fps: float = 4.0):
        self.sample_fps = sample_fps

    def extract_mouth_roi(self, frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> Optional[np.ndarray]:
        """Extract lower-face / mouth region of interest (ROI) from face bbox."""
        fx, fy, fw, fh = bbox
        h, w = frame.shape[:2]

        # Clamp face bbox to image boundaries
        x0 = max(0, int(fx))
        y0 = max(0, int(fy))
        x1 = min(w, int(fx + fw))
        y1 = min(h, int(fy + fh))

        if (x1 - x0) < 10 or (y1 - y0) < 10:
            return None

        # Mouth ROI: bottom 35% of face height, center 60% of face width
        mouth_y0 = min(h - 5, int(y0 + 0.60 * (y1 - y0)))
        mouth_y1 = min(h, int(y0 + 0.95 * (y1 - y0)))
        mouth_x0 = max(0, int(x0 + 0.20 * (x1 - x0)))
        mouth_x1 = min(w, int(x0 + 0.80 * (x1 - x0)))

        if (mouth_x1 - mouth_x0) < 6 or (mouth_y1 - mouth_y0) < 4:
            return None

        mouth_crop = frame[mouth_y0:mouth_y1, mouth_x0:mouth_x1]
        if mouth_crop.size == 0:
            return None

        # Convert to grayscale and resize to standard 48x32 patch
        gray = cv2.cvtColor(mouth_crop, cv2.COLOR_BGR2GRAY) if len(mouth_crop.shape) == 3 else mouth_crop
        resized = cv2.resize(gray, (48, 32), interpolation=cv2.INTER_AREA)
        return resized

    def compute_track_mouth_activity(
        self,
        video_path: str,
        tracks: Dict[int, List[Dict[str, Any]]],
    ) -> Dict[int, List[MouthActivity]]:
        """Sample video frames and compute mouth motion score for each track over time."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return {}

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        frame_interval = max(1, int(round(fps / self.sample_fps)))

        # Pre-index tracks by frame number
        frames_to_sample = set()
        track_dets_by_frame: Dict[int, Dict[int, Tuple[int, int, int, int]]] = {}

        for tid, dets in tracks.items():
            for d in dets:
                fidx = int(d.get("frame_index", 0))
                frames_to_sample.add(fidx)
                if fidx not in track_dets_by_frame:
                    track_dets_by_frame[fidx] = {}
                bbox = d.get("bbox") or (0, 0, 0, 0)
                track_dets_by_frame[fidx][tid] = bbox

        # Sample frames and store previous mouth ROIs per track
        prev_mouth_rois: Dict[int, Tuple[float, np.ndarray]] = {}
        activities: Dict[int, List[MouthActivity]] = {tid: [] for tid in tracks}

        current_frame = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if current_frame in track_dets_by_frame:
                t_sec = current_frame / float(fps)
                frame_tracks = track_dets_by_frame[current_frame]

                for tid, bbox in frame_tracks.items():
                    mouth_roi = self.extract_mouth_roi(frame, bbox)
                    if mouth_roi is None:
                        continue

                    if tid in prev_mouth_rois:
                        prev_t, prev_roi = prev_mouth_rois[tid]
                        # Compute normalized mean absolute difference between patches
                        diff = float(np.mean(np.abs(mouth_roi.astype(np.float32) - prev_roi.astype(np.float32)))) / 255.0
                        # Speech mouth opening/movement typically produces 0.03 - 0.15 diff
                        # Scale to 0.0 - 1.0 confidence
                        score = min(1.0, max(0.0, (diff - 0.015) / 0.08))

                        activities[tid].append(
                            MouthActivity(
                                track_id=tid,
                                start=round(prev_t, 2),
                                end=round(t_sec, 2),
                                score=round(score, 3),
                            )
                        )

                    prev_mouth_rois[tid] = (t_sec, mouth_roi)

            current_frame += 1

        cap.release()
        return activities
