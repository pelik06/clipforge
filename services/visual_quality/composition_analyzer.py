from typing import Any, Dict, List, Optional, Tuple

from services.visual_quality.models import VisualCompositionEvaluation


class VisualCompositionAnalyzer:
    """Analyzes framing headroom, face scale, speaker balance, and visual stability for mobile 9:16."""

    def __init__(self, target_width: int = 1080, target_height: int = 1920):
        self.target_width = target_width
        self.target_height = target_height

    def evaluate_headroom(self, face_y: float, face_height: float) -> Tuple[float, List[str], List[str]]:
        reasons = []
        penalties = []
        # Optimal headroom: 12% - 24% of frame height (230px - 460px in 1920)
        norm_headroom = face_y / float(self.target_height)

        if 0.10 <= norm_headroom <= 0.25:
            score = 95.0
            reasons.append("Optimal cinematic headroom for vertical mobile display")
        elif norm_headroom < 0.06:
            score = 55.0
            penalties.append("Insufficient headroom: subject face uncomfortably close to top frame edge")
        elif norm_headroom > 0.40:
            score = 65.0
            penalties.append("Excessive headroom: subject placed too low in vertical composition")
        else:
            score = 80.0
            reasons.append("Acceptable vertical headroom")

        return score, reasons, penalties

    def evaluate_face_size(self, face_height: float) -> Tuple[float, List[str], List[str]]:
        reasons = []
        penalties = []
        # Optimal face height on mobile screen: 14% - 28% of canvas height (270px - 540px)
        norm_size = face_height / float(self.target_height)

        if 0.12 <= norm_size <= 0.32:
            score = 95.0
            reasons.append("Subject face size is optimally scaled for smartphone viewing")
        elif norm_size < 0.08:
            score = 50.0
            penalties.append("Subject face is too small and distant for vertical short-form format")
        elif norm_size > 0.50:
            score = 65.0
            penalties.append("Over-cropped: face occupies disproportionate frame area")
        else:
            score = 80.0
            reasons.append("Adequate facial scaling")

        return score, reasons, penalties

    def evaluate(
        self,
        faces: Optional[List[Tuple[float, float, float, float]]] = None, # (x, y, w, h)
        caption_face_collision: bool = False,
        layout_mode: str = "TRACK",
    ) -> VisualCompositionEvaluation:
        reasons = []
        penalties = []

        if not faces:
            return VisualCompositionEvaluation(
                visual_quality_score=60.0,
                headroom_score=60.0,
                face_size_score=60.0,
                speaker_balance_score=60.0,
                caption_collision=caption_face_collision,
                reasons=["General frame crop without active face detections"],
            )

        # Primary face analysis
        fx, fy, fw, fh = faces[0]
        h_score, h_reasons, h_penalties = self.evaluate_headroom(fy, fh)
        reasons.extend(h_reasons)
        penalties.extend(h_penalties)

        s_score, s_reasons, s_penalties = self.evaluate_face_size(fh)
        reasons.extend(s_reasons)
        penalties.extend(s_penalties)

        # Multi-speaker balance
        bal_score = 90.0
        if len(faces) >= 2:
            f2_h = faces[1][3]
            size_ratio = min(fh, f2_h) / max(fh, f2_h)
            if size_ratio >= 0.60:
                bal_score = 92.0
                reasons.append("Balanced visual hierarchy between visible speakers")
            else:
                bal_score = 75.0
                reasons.append("Uneven scale between primary and secondary speakers")

        # Collision penalty
        if caption_face_collision:
            penalties.append("Subtitle bounding box collides with active facial area")

        # Weighted composite visual quality score
        composite = (
            h_score * 0.40
            + s_score * 0.35
            + bal_score * 0.25
            - (20.0 if caption_face_collision else 0.0)
        )
        final_score = max(0.0, min(100.0, composite))

        return VisualCompositionEvaluation(
            visual_quality_score=final_score,
            headroom_score=h_score,
            face_size_score=s_score,
            speaker_balance_score=bal_score,
            caption_collision=caption_face_collision,
            reasons=list(dict.fromkeys(reasons)),
            penalties=list(dict.fromkeys(penalties)),
        )
