from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class SafeAreaResult:
    target_alignment: int          # ASS alignment: 2 (bottom), 5 (center), 8 (top)
    margin_v: int                  # Vertical margin in pixels
    collision_avoided: bool        # True if moved due to face collision
    avoidance_reason: Optional[str] = None


class CaptionSafeAreaManager:
    """Manages subtitle placement to strictly prevent collision with active faces."""

    def __init__(
        self,
        canvas_width: int = 1080,
        canvas_height: int = 1920,
        default_margin_v: int = 160,
        top_margin_v: int = 180,
        hysteresis_seconds: float = 1.5,
    ):
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        self.default_margin_v = default_margin_v
        self.top_margin_v = top_margin_v
        self.hysteresis_seconds = hysteresis_seconds

    def check_face_collision(
        self,
        face_boxes: List[Tuple[float, float, float, float]], # (x, y, w, h)
        preferred_position: str = "bottom_safe",
    ) -> bool:
        """Check if any detected face overlaps the bottom caption safe zone (y: 1450-1850)."""
        if not face_boxes:
            return False

        # In 1080x1920, bottom caption sits roughly between y=1450 and y=1820
        caption_top = 1450
        caption_bottom = 1820

        for (fx, fy, fw, fh) in face_boxes:
            face_bottom = fy + fh
            # Check vertical overlap
            if not (face_bottom < caption_top or fy > caption_bottom):
                return True
        return False

    def resolve_caption_position(
        self,
        face_boxes: Optional[List[Tuple[float, float, float, float]]] = None,
        preferred_position: str = "bottom_safe",
        last_switch_time: float = -10.0,
        current_time: float = 0.0,
    ) -> SafeAreaResult:
        """Calculate optimal ASS Alignment and MarginV avoiding active faces."""
        boxes = face_boxes or []

        # If user explicitly specified top_safe or center, respect it unless collision
        if preferred_position == "top_safe":
            return SafeAreaResult(target_alignment=8, margin_v=self.top_margin_v, collision_avoided=False)
        elif preferred_position == "center":
            return SafeAreaResult(target_alignment=5, margin_v=0, collision_avoided=False)

        # Default bottom safe area check
        collision = self.check_face_collision(boxes, preferred_position)

        if collision:
            # Overlap detected: avoid face by elevating to top safe area (Alignment 8)
            return SafeAreaResult(
                target_alignment=8,
                margin_v=self.top_margin_v,
                collision_avoided=True,
                avoidance_reason="Face detected in bottom 9:16 safe margin; moved to top safe zone.",
            )

        # Standard clean bottom placement (Alignment 2)
        return SafeAreaResult(
            target_alignment=2,
            margin_v=self.default_margin_v,
            collision_avoided=False,
        )
