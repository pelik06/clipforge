import os
import math
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from core.config.settings import Settings
from core.models.configuration import FramingMode


@dataclass
class Detection:
    frame_index: int
    timestamp: float
    bbox: Tuple[int, int, int, int]  # (x, y, w, h)
    center_x: float
    center_y: float
    width: float
    height: float
    confidence: float
    track_id: int


@dataclass
class TrajectoryPoint:
    timestamp: float
    target_x: float
    target_y: float
    crop_x: float
    crop_y: float


@dataclass
class ReframingAnalysis:
    mode: str
    active_speaker_available: bool = False  # Critical rule: Active speaker detection unavailable, report as fallback
    face_detection_available: bool = False
    fallback_applied: bool = False
    fallback_reason: Optional[str] = None
    detections: List[Detection] = field(default_factory=list)
    trajectory: List[TrajectoryPoint] = field(default_factory=list)
    primary_track_id: Optional[int] = None

class ReframingResult(str):
    analysis: ReframingAnalysis
    filter_applied: str

    def __new__(cls, output_path: str, analysis: ReframingAnalysis, filter_applied: str):
        instance = super().__new__(cls, output_path)
        instance.analysis = analysis
        instance.filter_applied = filter_applied
        return instance

class Reframer:
    """Speaker-aware auto-reframing into vertical 9:16 format with temporal smoothing."""

    def __init__(self, model_path: Optional[str] = None):
        self.settings = Settings()
        default_model = Path(__file__).parent / "models" / "face_detection_yunet_2023mar.onnx"
        self.model_path = Path(model_path) if model_path else default_model

    def _get_detector(self, width: int = 320, height: int = 320) -> Optional[Any]:
        if not self.model_path.exists() or self.model_path.stat().st_size < 1000:
            return None
        try:
            detector = cv2.FaceDetectorYN.create(str(self.model_path), "", (width, height), score_threshold=0.6)
            return detector
        except Exception:
            return None

    def analyze_footage(
        self,
        video_path: str,
        sample_fps: float = 4.0,
        out_width: int = 1080,
        out_height: int = 1920,
        scenes: Optional[List[Dict[str, float]]] = None,
    ) -> ReframingAnalysis:
        """Sample video frames, detect faces, track primary subject, and compute smoothed crop trajectory."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return ReframingAnalysis(
                mode="fallback_center",
                active_speaker_available=False,
                face_detection_available=False,
                fallback_applied=True,
                fallback_reason=f"Cannot open video file: {video_path}",
            )

        video_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        source_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1920)
        source_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 1080)
        duration = total_frames / video_fps if total_frames > 0 else 5.0

        detector = self._get_detector(source_w, source_h)
        if detector is None:
            cap.release()
            return ReframingAnalysis(
                mode="fallback_center",
                active_speaker_available=False,
                face_detection_available=False,
                fallback_applied=True,
                fallback_reason="Face detection model (YuNet ONNX) unavailable; using center crop fallback.",
            )

        detector.setInputSize((source_w, source_h))

        # Sample frames at sample_fps interval
        sample_interval = max(1, int(round(video_fps / sample_fps)))
        raw_detections: List[Detection] = []
        tracks: Dict[int, Dict[str, Any]] = {}
        next_track_id = 1
        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % sample_interval == 0:
                # Scene-aware tracking reset: do not carry tracking across scene transitions
                scene_cuts = [s["start"] for s in (scenes or []) if s.get("start", 0) > 0.3]
                if any(abs(t_sec - cut_t) < 0.35 for cut_t in scene_cuts):
                    tracks.clear()
                try:
                    _, faces = detector.detect(frame)
                except Exception:
                    faces = None

                current_frame_dets: List[Tuple[float, float, float, float, float]] = []
                if faces is not None and len(faces) > 0:
                    for f in faces:
                        fx, fy, fw, fh = float(f[0]), float(f[1]), float(f[2]), float(f[3])
                        conf = float(f[14])
                        if fw > 20 and fh > 20 and conf >= 0.55:
                            current_frame_dets.append((fx, fy, fw, fh, conf))

                # Frame-to-frame tracking
                for fx, fy, fw, fh, conf in current_frame_dets:
                    cx = fx + fw / 2.0
                    cy = fy + fh / 2.0

                    best_tid = None
                    best_dist = float("inf")
                    for tid, tinfo in tracks.items():
                        # Track matching threshold: within 35% of frame width
                        dist = math.hypot(cx - tinfo["last_cx"], cy - tinfo["last_cy"])
                        if dist < (source_w * 0.35) and dist < best_dist:
                            best_dist = dist
                            best_tid = tid

                    if best_tid is None:
                        best_tid = next_track_id
                        next_track_id += 1
                        tracks[best_tid] = {
                            "first_t": t_sec,
                            "count": 0,
                            "total_area": 0.0,
                            "last_cx": cx,
                            "last_cy": cy,
                        }

                    tracks[best_tid]["count"] += 1
                    tracks[best_tid]["total_area"] += (fw * fh)
                    tracks[best_tid]["last_cx"] = cx
                    tracks[best_tid]["last_cy"] = cy

                    det_obj = Detection(
                        frame_index=frame_idx,
                        timestamp=t_sec,
                        bbox=(int(fx), int(fy), int(fw), int(fh)),
                        center_x=cx,
                        center_y=cy,
                        width=fw,
                        height=fh,
                        confidence=conf,
                        track_id=best_tid,
                    )
                    raw_detections.append(det_obj)

            frame_idx += 1

        cap.release()

        # If no faces detected anywhere in video, fallback to center crop
        if not raw_detections or not tracks:
            return ReframingAnalysis(
                mode="fallback_center",
                active_speaker_available=False,
                face_detection_available=True,
                fallback_applied=True,
                fallback_reason="No faces detected in video; center crop fallback applied.",
            )

        # Select primary track: highest persistence and area (salient speaker)
        primary_tid = max(tracks.keys(), key=lambda tid: (tracks[tid]["count"], tracks[tid]["total_area"]))
        primary_dets = {d.timestamp: d for d in raw_detections if d.track_id == primary_tid}

        # Calculate crop coordinates in 1080x1920 vertical space
        # Aspect scaling: scale so video height is at least out_height (1920)
        scale_factor = out_height / float(source_h)
        scaled_w = source_w * scale_factor
        scaled_h = source_h * scale_factor  # = 1920
        max_crop_x = max(0.0, scaled_w - out_width)
        default_center_x = max_crop_x / 2.0

        # Construct raw trajectory at sampled timestamps
        sampled_timestamps = sorted(list(set(d.timestamp for d in raw_detections)))
        if not sampled_timestamps:
            sampled_timestamps = [0.0]

        raw_points: List[Tuple[float, float, float, float, float]] = []
        last_known_cx = source_w / 2.0
        last_known_cy = source_h * 0.35

        for ts in sampled_timestamps:
            if ts in primary_dets:
                d = primary_dets[ts]
                last_known_cx = d.center_x
                last_known_cy = d.center_y

            # Scale to vertical space
            target_scaled_x = last_known_cx * scale_factor
            target_scaled_y = last_known_cy * scale_factor

            # Desired crop window X centered on target face
            desired_crop_x = target_scaled_x - (out_width / 2.0)
            clamped_crop_x = max(0.0, min(max_crop_x, desired_crop_x))
            crop_y = 0.0

            raw_points.append((ts, last_known_cx, last_known_cy, clamped_crop_x, crop_y))

        # Temporal Smoothing with Safe Deadband & Jump Confirmation
        smoothed_trajectory: List[TrajectoryPoint] = []
        alpha = 0.25
        smoothed_x = default_center_x if not raw_points else raw_points[0][3]
        jump_confirm_count = 0

        for i, (ts, tcx, tcy, cx, cy) in enumerate(raw_points):
            scene_cuts = [s["start"] for s in (scenes or []) if s.get("start", 0) > 0.3]
            if any(abs(ts - cut_t) < 0.4 for cut_t in scene_cuts):
                smoothed_x = cx
                jump_confirm_count = 0
            else:
                # Safe Zone Deadband: ignore minor jitter < 25 pixels
                target_shift = smoothed_x if abs(cx - smoothed_x) < 25.0 else cx

                # Jump Confirmation (JUMP_CONFIRM_FRAMES = 3)
                if abs(target_shift - smoothed_x) > 180.0:
                    jump_confirm_count += 1
                    if jump_confirm_count < 3:
                        target_shift = smoothed_x
                else:
                    jump_confirm_count = 0

                smoothed_x = alpha * target_shift + (1.0 - alpha) * smoothed_x

            final_crop_x = max(0.0, min(max_crop_x, smoothed_x))
            smoothed_trajectory.append(
                TrajectoryPoint(
                    timestamp=ts,
                    target_x=round(tcx, 2),
                    target_y=round(tcy, 2),
                    crop_x=round(final_crop_x, 2),
                    crop_y=round(cy, 2),
                )
            )

        return ReframingAnalysis(
            mode="speaker_aware_tracking",
            active_speaker_available=False,  # Transparent fallback disclosure per Constitution & Task 2.6
            face_detection_available=True,
            fallback_applied=False,
            fallback_reason="Active speaker detection unavailable; using face/person tracking fallback.",
            detections=raw_detections,
            trajectory=smoothed_trajectory,
            primary_track_id=primary_tid,
        )

    def build_crop_filter(
        self,
        analysis: ReframingAnalysis,
        source_w: int,
        source_h: int,
        out_w: int = 1080,
        out_h: int = 1920,
    ) -> str:
        """Build FFmpeg video filter for static or trajectory-guided reframing."""
        # Scale to match height 1920
        scale_filter = f"scale={out_w}:{out_h}:force_original_aspect_ratio=increase"

        if (
            analysis.fallback_applied
            or not analysis.trajectory
            or len(analysis.trajectory) < 2
        ):
            # Center crop fallback
            return f"{scale_filter},crop={out_w}:{out_h}"
        # Downsample trajectory if too long to prevent FFmpeg expression stack overflow (max 24 points)
        pts = analysis.trajectory
        if len(pts) > 24:
            step = math.ceil(len(pts) / 24)
            sampled_pts = pts[::step]
            if sampled_pts[-1] != pts[-1]:
                sampled_pts.append(pts[-1])
            pts = sampled_pts

        expr = f"{pts[-1].crop_x:.1f}"
        for i in range(len(pts) - 2, -1, -1):
            p0 = pts[i]
            p1 = pts[i + 1]
            dt = max(0.001, p1.timestamp - p0.timestamp)
            dx = p1.crop_x - p0.crop_x
            seg = f"({p0.crop_x:.1f}+({dx:.2f})*(t-{p0.timestamp:.2f})/{dt:.3f})"
            expr = f"if(lt(t,{p1.timestamp:.2f}),{seg},{expr})"

        scale_str = f"scale=w='max({out_w},trunc(iw*{out_h}/ih/2)*2)':h={out_h}"
        return f"{scale_str},crop={out_w}:{out_h}:x='{expr}':y=0"

    def render_vertical(
        self,
        source_path: str,
        output_path: str,
        width: int = 1080,
        height: int = 1920,
        framing_mode: str = "center_crop",
        scenes: Optional[List[Dict[str, float]]] = None,
    ) -> Dict[str, Any]:
        """Render source footage into vertical 9:16 short format applying requested framing mode."""
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"Source video file not found: {source_path}")
        if not source.is_file():
            raise ValueError(f"Source path is not a file: {source_path}")

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        s = Settings()

        # Probe input video dimensions
        probe_cmd = [
            s.ffprobe_bin,
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0",
            str(source),
        ]
        probe_proc = subprocess.run(probe_cmd, capture_output=True, text=True)
        src_w, src_h = 1920, 1080
        if probe_proc.returncode == 0 and probe_proc.stdout.strip():
            try:
                parts = probe_proc.stdout.strip().split(",")
                src_w, src_h = int(parts[0]), int(parts[1])
            except Exception:
                pass

        analysis = ReframingAnalysis(
            mode=framing_mode,
            active_speaker_available=False,
            fallback_applied=False,
        )

        if framing_mode == FramingMode.AUTO_FOLLOW_SPEAKER.value:
            # Perform face/person detection & tracking analysis with scene-aware resets
            analysis = self.analyze_footage(str(source), out_width=width, out_height=height, scenes=scenes)
            filter_str = self.build_crop_filter(analysis, src_w, src_h, width, height)
        else:
            # Center crop default
            filter_str = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"

        cmd = [
            s.ffmpeg_bin,
            "-y",
            "-i", str(source),
            "-vf", filter_str,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "22",
            "-c:a", "copy",
            "-movflags", "+faststart",
            str(out),
        ]

        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=180,
        )

        if proc.returncode != 0:
            # Transcode audio fallback if container copy fails
            fallback_cmd = [
                s.ffmpeg_bin,
                "-y",
                "-i", str(source),
                "-vf", filter_str,
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "22",
                "-c:a", "aac",
                "-movflags", "+faststart",
                str(out),
            ]
            proc = subprocess.run(
                fallback_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=180,
            )
            if proc.returncode != 0:
                raise RuntimeError(f"FFmpeg vertical reframing failed (code {proc.returncode}): {proc.stderr[-400:]}")

        if not out.exists() or out.stat().st_size == 0:
            raise RuntimeError(f"Reframing completed but output file missing or empty: {output_path}")

        return ReframingResult(str(out), analysis=analysis, filter_applied=filter_str)
