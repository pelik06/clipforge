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
    is_scene_cut: bool = False


@dataclass
class ReframingAnalysis:
    mode: str
    layout_mode: str = "TRACK"  # "TRACK", "SPLIT", "GENERAL"
    active_speaker_available: bool = False
    face_detection_available: bool = False
    fallback_applied: bool = False
    fallback_reason: Optional[str] = None
    detections: List[Detection] = field(default_factory=list)
    trajectory: List[TrajectoryPoint] = field(default_factory=list)
    primary_track_id: Optional[int] = None
    secondary_track_id: Optional[int] = None
    speaker_timeline: Optional[Any] = None
    split_crops: Optional[Tuple[Tuple[int, int, int, int], Tuple[int, int, int, int]]] = None

class ReframingResult(str):
    analysis: ReframingAnalysis
    filter_applied: str

    def __new__(cls, output_path: str, analysis: ReframingAnalysis, filter_applied: str):
        instance = super().__new__(cls, output_path)
        instance.analysis = analysis
        instance.filter_applied = filter_applied
        return instance


def compute_iou(boxA: Tuple[float, float, float, float], boxB: Tuple[float, float, float, float]) -> float:
    """Compute Intersection over Union between two bounding boxes (x, y, w, h)."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[0] + boxA[2], boxB[0] + boxB[2])
    yB = min(boxA[1] + boxA[3], boxB[1] + boxB[3])

    inter = max(0.0, xB - xA) * max(0.0, yB - yA)
    areaA = boxA[2] * boxA[3]
    areaB = boxB[2] * boxB[3]
    denom = areaA + areaB - inter
    if denom <= 0.0:
        return 0.0
    return inter / denom


def compute_center_similarity(
    centerA: Tuple[float, float],
    centerB: Tuple[float, float],
    frame_w: float,
    frame_h: float,
) -> float:
    """Compute normalized spatial center proximity similarity [0.0, 1.0]."""
    diag = math.hypot(frame_w, frame_h)
    dist = math.hypot(centerA[0] - centerB[0], centerA[1] - centerB[1])
    norm_dist = dist / max(1.0, diag)
    return max(0.0, 1.0 - (norm_dist / 0.35))


class Reframer:
    """Speaker-aware auto-reframing into vertical 9:16 format with persistent tracking and scene-cut snapping."""

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
        framing_mode: str = "track",
        speech_segments: Optional[Any] = None,
    ) -> ReframingAnalysis:
        """Sample video frames, track faces with persistent IDs, and compute smoothed trajectory with scene snaps."""
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

        # Mode check: if GENERAL / center crop requested, return center crop immediately
        if framing_mode in (FramingMode.CENTER_CROP.value, FramingMode.GENERAL.value):
            cap.release()
            return ReframingAnalysis(
                mode="center_crop",
                active_speaker_available=False,
                face_detection_available=True,
                fallback_applied=True,
                fallback_reason="General / center crop requested explicitly.",
            )

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

        sample_interval = max(1, int(round(video_fps / sample_fps)))
        raw_detections: List[Detection] = []
        tracks: Dict[int, Dict[str, Any]] = {}
        next_track_id = 1
        frame_idx = 0

        track_timeout = self.settings.track_timeout
        scene_cuts = [s["start"] for s in (scenes or []) if s.get("start", 0) > 0.3]

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % sample_interval == 0:
                t_sec = round(frame_idx / video_fps, 3)

                # Check if frame is crossing a scene cut
                is_near_scene_cut = any(abs(t_sec - cut_t) < 0.25 for cut_t in scene_cuts)

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

                # Persistent Multi-Object Tracking Matching (IoU + Center Distance)
                # Filter active tracks within timeout
                active_track_ids = [
                    tid for tid, tinfo in tracks.items()
                    if (t_sec - tinfo["last_seen_t"]) <= track_timeout
                ]

                # Compute match matrix: current_frame_dets x active_track_ids
                matched_detections = set()
                matched_tracks = set()
                candidate_pairs = []

                for det_idx, (fx, fy, fw, fh, conf) in enumerate(current_frame_dets):
                    cx = fx + fw / 2.0
                    cy = fy + fh / 2.0
                    det_box = (fx, fy, fw, fh)
                    det_center = (cx, cy)

                    for tid in active_track_ids:
                        tinfo = tracks[tid]
                        last_box = tinfo["last_bbox"]
                        last_center = (tinfo["last_cx"], tinfo["last_cy"])

                        iou = compute_iou(det_box, last_box)
                        center_sim = compute_center_similarity(det_center, last_center, source_w, source_h)
                        match_score = 0.5 * iou + 0.5 * center_sim

                        if match_score >= 0.20 or center_sim >= 0.40:
                            candidate_pairs.append((match_score, det_idx, tid))

                # Greedy bipartite matching (highest score first)
                candidate_pairs.sort(key=lambda x: x[0], reverse=True)
                for score, det_idx, tid in candidate_pairs:
                    if det_idx in matched_detections or tid in matched_tracks:
                        continue
                    matched_detections.add(det_idx)
                    matched_tracks.add(tid)

                    fx, fy, fw, fh, conf = current_frame_dets[det_idx]
                    cx = fx + fw / 2.0
                    cy = fy + fh / 2.0

                    tracks[tid]["count"] += 1
                    tracks[tid]["total_area"] += (fw * fh)
                    tracks[tid]["last_seen_t"] = t_sec
                    tracks[tid]["last_cx"] = cx
                    tracks[tid]["last_cy"] = cy
                    tracks[tid]["last_bbox"] = (fx, fy, fw, fh)

                    det_obj = Detection(
                        frame_index=frame_idx,
                        timestamp=t_sec,
                        bbox=(int(fx), int(fy), int(fw), int(fh)),
                        center_x=cx,
                        center_y=cy,
                        width=fw,
                        height=fh,
                        confidence=conf,
                        track_id=tid,
                    )
                    raw_detections.append(det_obj)

                # Initialize new tracks for unmatched detections
                for det_idx, (fx, fy, fw, fh, conf) in enumerate(current_frame_dets):
                    if det_idx not in matched_detections:
                        tid = next_track_id
                        next_track_id += 1
                        cx = fx + fw / 2.0
                        cy = fy + fh / 2.0
                        tracks[tid] = {
                            "first_t": t_sec,
                            "last_seen_t": t_sec,
                            "count": 1,
                            "total_area": fw * fh,
                            "last_cx": cx,
                            "last_cy": cy,
                            "last_bbox": (fx, fy, fw, fh),
                        }
                        det_obj = Detection(
                            frame_index=frame_idx,
                            timestamp=t_sec,
                            bbox=(int(fx), int(fy), int(fw), int(fh)),
                            center_x=cx,
                            center_y=cy,
                            width=fw,
                            height=fh,
                            confidence=conf,
                            track_id=tid,
                        )
                        raw_detections.append(det_obj)

            frame_idx += 1

        cap.release()

        # Center crop fallback if no faces found
        if not raw_detections or not tracks:
            return ReframingAnalysis(
                mode="fallback_center",
                active_speaker_available=False,
                face_detection_available=True,
                fallback_applied=True,
                fallback_reason="No faces detected in video; center crop fallback applied.",
            )

        # Determine layout mode
        req_mode = str(framing_mode).lower()
        is_split_requested = (req_mode == "split")

        # Evaluate Active Speaker Detection
        speaker_timeline = None
        active_spk_available = False
        spk_fallback_reason = "Active speaker detection unavailable; using face/person tracking fallback."

        try:
            from services.speaker_detection.detector import ActiveSpeakerDetector
            spk_detector = ActiveSpeakerDetector()
            speaker_timeline = spk_detector.analyze_speakers(
                detections=raw_detections,
                speech_segments=speech_segments or [],
                scenes=scenes,
                video_path=video_path,
                total_duration=duration,
            )
            if speaker_timeline and speaker_timeline.speaker_mode == "active_speaker" and speaker_timeline.segments:
                active_spk_available = True
                spk_fallback_reason = None
        except Exception as e:
            speaker_timeline = None
            active_spk_available = False

        # Multi-Speaker Split Layout Decision
        sorted_tracks = sorted(tracks.keys(), key=lambda tid: (tracks[tid]["count"], tracks[tid]["total_area"]), reverse=True)
        primary_tid = sorted_tracks[0]
        secondary_tid = sorted_tracks[1] if len(sorted_tracks) > 1 else None

        # Check split eligibility: at least 2 tracks with significant horizontal distance
        if is_split_requested and secondary_tid is not None:
            p1_cx = tracks[primary_tid]["last_cx"]
            p2_cx = tracks[secondary_tid]["last_cx"]
            p1_cy = tracks[primary_tid]["last_cy"]
            p2_cy = tracks[secondary_tid]["last_cy"]
            dist_x = abs(p1_cx - p2_cx) / float(source_w)

            # Split ratio for top & bottom: 1080x960 (9:8 aspect ratio)
            w_c = min(source_w, int(source_h * (out_width / (out_height / 2.0))))
            h_c = int(w_c * ((out_height / 2.0) / out_width))
            if h_c > source_h:
                h_c = source_h
                w_c = int(h_c * (out_width / (out_height / 2.0)))

            # Calculate top crop for speaker 1, bottom crop for speaker 2
            # Place left speaker on top or bottom according to position
            t1_x = max(0, min(source_w - w_c, int(p1_cx - w_c / 2.0)))
            t1_y = max(0, min(source_h - h_c, int(p1_cy - h_c / 2.0)))
            t2_x = max(0, min(source_w - w_c, int(p2_cx - w_c / 2.0)))
            t2_y = max(0, min(source_h - h_c, int(p2_cy - h_c / 2.0)))

            split_crops = ((t1_x, t1_y, w_c, h_c), (t2_x, t2_y, w_c, h_c))
            return ReframingAnalysis(
                mode="split_layout",
                layout_mode="SPLIT",
                active_speaker_available=active_spk_available,
                face_detection_available=True,
                fallback_applied=False,
                fallback_reason=None,
                detections=raw_detections,
                trajectory=[],
                primary_track_id=primary_tid,
                secondary_track_id=secondary_tid,
                speaker_timeline=speaker_timeline,
                split_crops=split_crops,
            )

        # Standard TRACK / Follow Speaker Mode
        # Pre-index active speaker by timestamp if timeline exists
        spk_by_timestamp: Dict[float, int] = {}
        if active_spk_available and speaker_timeline:
            for ts in [d.timestamp for d in raw_detections]:
                for seg in speaker_timeline.segments:
                    if seg.start <= ts <= seg.end:
                        spk_by_timestamp[ts] = seg.track_id
                        break

        # Group detections by track
        dets_by_track: Dict[int, Dict[float, Any]] = {}
        for d in raw_detections:
            if d.track_id not in dets_by_track:
                dets_by_track[d.track_id] = {}
            dets_by_track[d.track_id][d.timestamp] = d

        # Calculate crop coordinates in 1080x1920 vertical space
        scale_factor = out_height / float(source_h)
        scaled_w = source_w * scale_factor
        scaled_h = source_h * scale_factor  # 1920
        max_crop_x = max(0.0, scaled_w - out_width)
        default_center_x = max_crop_x / 2.0

        sampled_timestamps = sorted(list(set(d.timestamp for d in raw_detections)))
        if not sampled_timestamps:
            sampled_timestamps = [0.0]

        raw_points: List[Tuple[float, float, float, float, float, bool]] = []
        last_known_cx = source_w / 2.0
        last_known_cy = source_h * 0.35

        for ts in sampled_timestamps:
            is_cut = any(abs(ts - cut_t) < 0.30 for cut_t in scene_cuts)
            # Active speaker priority: lookup speaker track at this timestamp
            target_tid = spk_by_timestamp.get(ts, primary_tid)
            track_dets = dets_by_track.get(target_tid, {})

            if ts in track_dets:
                d = track_dets[ts]
                last_known_cx = d.center_x
                last_known_cy = d.center_y
            elif ts in dets_by_track.get(primary_tid, {}):
                d = dets_by_track[primary_tid][ts]
                last_known_cx = d.center_x
                last_known_cy = d.center_y
            elif is_cut:
                # On scene cut without target face, search any detected face at this timestamp
                cur_faces = [d for d in raw_detections if d.timestamp == ts]
                if cur_faces:
                    best_f = max(cur_faces, key=lambda f: f.width * f.height)
                    last_known_cx = best_f.center_x
                    last_known_cy = best_f.center_y

            target_scaled_x = last_known_cx * scale_factor
            target_scaled_y = last_known_cy * scale_factor
            desired_crop_x = target_scaled_x - (out_width / 2.0)
            clamped_crop_x = max(0.0, min(max_crop_x, desired_crop_x))
            crop_y = 0.0

            raw_points.append((ts, last_known_cx, last_known_cy, clamped_crop_x, crop_y, is_cut))

        # Temporal Smoothing with Scene-Cut Instant Snap
        smoothed_trajectory: List[TrajectoryPoint] = []
        base_alpha = max(0.45, self.settings.reframe_smoothing)
        smoothed_x = default_center_x if not raw_points else raw_points[0][3]

        for i, (ts, tcx, tcy, cx, cy, is_cut) in enumerate(raw_points):
            if is_cut and self.settings.scene_cut_snap:
                smoothed_x = cx
            else:
                diff = abs(cx - smoothed_x)
                if diff < 20.0:
                    # Deadband: minor head-bob micro-jitter held steady
                    target_shift = smoothed_x
                    step_alpha = base_alpha
                elif diff > 100.0:
                    # Speaker switch: snappy responsive pan in 1-2 frames (~0.25-0.35s)
                    target_shift = cx
                    step_alpha = 0.78
                else:
                    # Moderate head/body movement
                    target_shift = cx
                    step_alpha = max(base_alpha, 0.55)

                smoothed_x = step_alpha * target_shift + (1.0 - step_alpha) * smoothed_x

            final_crop_x = max(0.0, min(max_crop_x, smoothed_x))
            smoothed_trajectory.append(
                TrajectoryPoint(
                    timestamp=ts,
                    target_x=round(tcx, 2),
                    target_y=round(tcy, 2),
                    crop_x=round(final_crop_x, 2),
                    crop_y=round(cy, 2),
                    is_scene_cut=is_cut,
                )
            )

        return ReframingAnalysis(
            mode="speaker_aware_tracking",
            layout_mode="TRACK",
            active_speaker_available=active_spk_available,
            face_detection_available=True,
            fallback_applied=not active_spk_available,
            fallback_reason=spk_fallback_reason,
            detections=raw_detections,
            trajectory=smoothed_trajectory,
            primary_track_id=primary_tid,
            secondary_track_id=secondary_tid,
            speaker_timeline=speaker_timeline,
        )

    def build_crop_filter(
        self,
        analysis: ReframingAnalysis,
        source_w: int,
        source_h: int,
        out_w: int = 1080,
        out_h: int = 1920,
    ) -> str:
        """Build FFmpeg video filter for static or trajectory-guided reframing with scene-cut snapping."""
        scale_filter = f"scale={out_w}:{out_h}:force_original_aspect_ratio=increase"

        if (
            analysis.fallback_applied
            or not analysis.trajectory
            or len(analysis.trajectory) < 2
        ):
            return f"{scale_filter},crop={out_w}:{out_h}"

        pts = analysis.trajectory
        # Downsample trajectory to max 24 keypoints to avoid FFmpeg recursion depth limit
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

            if p1.is_scene_cut and self.settings.scene_cut_snap:
                # Instant snap at scene cut: before p1.timestamp hold p0.crop_x, at p1 jump to p1.crop_x
                seg = f"{p0.crop_x:.1f}"
            else:
                # Within scene: linear interpolation between keypoints
                dt = max(0.001, p1.timestamp - p0.timestamp)
                dx = p1.crop_x - p0.crop_x
                seg = f"({p0.crop_x:.1f}+({dx:.2f})*(t-{p0.timestamp:.2f})/{dt:.3f})"

            expr = f"if(lt(t,{p1.timestamp:.2f}),{seg},{expr})"

        scale_str = f"scale=w='max({out_w},trunc(iw*{out_h}/ih/2)*2)':h={out_h}"
        return f"{scale_str},crop={out_w}:{out_h}:x='{expr}':y=0"
    def build_split_filter(
        self,
        analysis: ReframingAnalysis,
        src_w: int,
        src_h: int,
        out_w: int = 1080,
        out_h: int = 1920,
    ) -> str:
        """Build FFmpeg filter_complex for dual stacked 1080x960 split layout."""
        half_h = out_h // 2
        w_c = min(src_w, int(src_h * (out_w / float(half_h))))
        h_c = int(w_c * (float(half_h) / out_w))
        if h_c > src_h:
            h_c = src_h
            w_c = int(h_c * (out_w / float(half_h)))

        c1 = (0, 0, w_c, h_c)
        c2 = (max(0, src_w - w_c), 0, w_c, h_c)
        if analysis.split_crops:
            c1, c2 = analysis.split_crops

        x1, y1, w1, h1 = c1
        x2, y2, w2, h2 = c2
        w1, h1 = (w1 // 2) * 2, (h1 // 2) * 2
        w2, h2 = (w2 // 2) * 2, (h2 // 2) * 2
        x1, y1 = (x1 // 2) * 2, (y1 // 2) * 2
        x2, y2 = (x2 // 2) * 2, (y2 // 2) * 2

        top_filt = f"[0:v]crop={w1}:{h1}:{x1}:{y1},scale={out_w}:{half_h}[top]"
        bot_filt = f"[0:v]crop={w2}:{h2}:{x2}:{y2},scale={out_w}:{half_h}[bot]"
        stack = "[top][bot]vstack=inputs=2[v]"
        return f"{top_filt};{bot_filt};{stack}"


    def render_vertical(
        self,
        source_path: str,
        output_path: str,
        width: int = 1080,
        height: int = 1920,
        framing_mode: str = "track",
        scenes: Optional[List[Dict[str, float]]] = None,
        speech_segments: Optional[Any] = None,
    ) -> Dict[str, Any]:
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"Source video file not found: {source_path}")
        if not source.is_file():
            raise ValueError(f"Source path is not a file: {source_path}")

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        s = Settings()

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

        analysis = self.analyze_footage(
            str(source),
            out_width=width,
            out_height=height,
            scenes=scenes,
            framing_mode=framing_mode,
            speech_segments=speech_segments,
        )
        if analysis.layout_mode == "SPLIT":
            filter_str = self.build_split_filter(analysis, src_w, src_h, out_w=width, out_h=height)
            cmd = [
                s.ffmpeg_bin,
                "-y",
                "-i", str(source),
                "-filter_complex", filter_str,
                "-map", "[v]",
                "-map", "0:a?",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "22",
                "-movflags", "+faststart",
                str(out),
            ]
        else:
            filter_str = self.build_crop_filter(analysis, src_w, src_h, out_w=width, out_h=height)
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
                raise RuntimeError(
                    f"FFmpeg vertical reframing render failed (code {proc.returncode}): {proc.stderr[-400:]}"
                )

        if not out.exists() or out.stat().st_size == 0:
            raise RuntimeError(f"Render completed but output file does not exist or is empty: {output_path}")

        return ReframingResult(str(out), analysis=analysis, filter_applied=filter_str)
