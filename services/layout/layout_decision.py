from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class LayoutMode(str, Enum):
    TRACK = "TRACK"
    SPLIT = "SPLIT"
    GENERAL = "GENERAL"


@dataclass
class LayoutDecision:
    mode: str                          # "TRACK" | "SPLIT" | "GENERAL"
    confidence: float                  # [0.0, 1.0]
    primary_track_id: Optional[int] = None
    secondary_track_id: Optional[int] = None
    reason: str = ""
    switch_count: int = 0
    switched: bool = False


class AdvancedLayoutEngine:
    """Intelligent layout decision engine with temporal hysteresis, scene cut resets, and distance awareness."""

    def __init__(
        self,
        min_layout_duration: float = 1.0,
        layout_switch_margin: float = 0.15,
        split_distance_threshold: float = 0.35,
    ):
        self.min_layout_duration = min_layout_duration
        self.layout_switch_margin = layout_switch_margin
        self.split_distance_threshold = split_distance_threshold

        self.current_layout: Optional[str] = None
        self.last_switch_time = -100.0
        self.switch_count = 0

    def reset(self):
        """Reset state for a new video or clip."""
        self.current_layout = None
        self.last_switch_time = -100.0
        self.switch_count = 0

    def evaluate_layout(
        self,
        timestamp: float,
        visible_faces: List[Dict[str, Any]],
        active_speaker_id: Optional[int] = None,
        is_scene_cut: bool = False,
        speech_overlap: bool = False,
        requested_mode: Optional[str] = None,
    ) -> LayoutDecision:
        """Decide layout between TRACK, SPLIT, and GENERAL based on multi-speaker geometry and speech."""
        # Scene-cut reset: resets duration lock and allows instant cut
        if is_scene_cut:
            self.last_switch_time = -100.0
        # If user explicitly requested split or general mode, adhere to it
        if requested_mode and requested_mode.lower() in {"split", "track", "general"}:
            target_mode = requested_mode.upper()
            primary_id = active_speaker_id or (visible_faces[0].get("track_id") if visible_faces else None)
            secondary_id = (visible_faces[1].get("track_id") if len(visible_faces) > 1 else None) if target_mode == "SPLIT" else None
            return LayoutDecision(
                mode=target_mode,
                confidence=0.95,
                primary_track_id=primary_id,
                secondary_track_id=secondary_id,
                reason=f"Explicit requested mode: {target_mode}",
                switch_count=self.switch_count,
                switched=False,
            )

        # 0 faces -> GENERAL fallback
        if not visible_faces:
            candidate_mode = LayoutMode.GENERAL.value
            candidate_conf = 0.70
            reason = "No faces detected in frame; fallback to GENERAL"
            primary_id = None
            secondary_id = None
        elif len(visible_faces) == 1:
            candidate_mode = LayoutMode.TRACK.value
            candidate_conf = 0.90
            primary_id = visible_faces[0].get("track_id", 1)
            secondary_id = None
            reason = "Single dominant visible speaker; using TRACK"
        else:
            # 2+ faces: evaluate spatial separation and active speakers
            f1 = visible_faces[0]
            f2 = visible_faces[1]
            c1_x = f1.get("center_x", 0.0)
            c2_x = f2.get("center_x", 0.0)
            norm_dist = abs(c1_x - c2_x)

            # Both faces visible and widely separated
            if norm_dist >= self.split_distance_threshold or speech_overlap:
                candidate_mode = LayoutMode.SPLIT.value
                candidate_conf = 0.85
                primary_id = active_speaker_id or f1.get("track_id", 1)
                other_faces = [f for f in visible_faces if f.get("track_id") != primary_id]
                secondary_id = other_faces[0].get("track_id", 2) if other_faces else f2.get("track_id", 2)
                reason = f"Dual speakers separated ({norm_dist:.2f} > {self.split_distance_threshold:.2f}); using SPLIT"
            else:
                candidate_mode = LayoutMode.TRACK.value
                candidate_conf = 0.80
                primary_id = active_speaker_id or f1.get("track_id", 1)
                secondary_id = None
                reason = f"Speakers close together ({norm_dist:.2f} <= {self.split_distance_threshold:.2f}); using TRACK"

        # Apply Temporal Hysteresis & Minimum Layout Duration
        switched = False
        if self.current_layout is None:
            self.current_layout = candidate_mode
            self.last_switch_time = timestamp
        elif candidate_mode != self.current_layout:
            time_since_switch = timestamp - self.last_switch_time
            # Allowed to switch if beyond min duration or scene cut
            if is_scene_cut or time_since_switch >= self.min_layout_duration:
                self.current_layout = candidate_mode
                self.last_switch_time = timestamp
                self.switch_count += 1
                switched = True
            else:
                # Maintain current layout to suppress rapid layout jitter
                candidate_mode = self.current_layout
                reason = f"Layout switch suppressed by hysteresis ({time_since_switch:.2f}s < {self.min_layout_duration:.2f}s)"

        return LayoutDecision(
            mode=candidate_mode,
            confidence=candidate_conf,
            primary_track_id=primary_id,
            secondary_track_id=secondary_id,
            reason=reason,
            switch_count=self.switch_count,
            switched=switched,
        )
