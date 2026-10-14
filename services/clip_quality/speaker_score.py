from typing import Any, Dict, List, Optional, Tuple


class SpeakerFramingScorer:
    """Evaluates speaker tracking confidence, framing centering, and layout stability."""

    def evaluate_speaker_framing(
        self,
        active_speaker_confidence: float = 0.5,
        face_detected: bool = True,
        layout_mode: str = "TRACK",
        layout_switches: int = 0,
        face_centered_ratio: float = 0.9,
    ) -> Tuple[float, List[str], List[str]]:
        reasons = []
        penalties = []
        score = 5.0  # baseline

        if face_detected:
            score += 2.0
            reasons.append("Subject face detected and tracked")
        else:
            score -= 2.0
            penalties.append("No primary face tracked in video")

        # Active speaker confidence
        if active_speaker_confidence >= 0.80:
            score += 2.0
            reasons.append(f"High speaker identification confidence ({active_speaker_confidence:.0%})")
        elif active_speaker_confidence < 0.40:
            score -= 1.0
            penalties.append("Uncertain active speaker attribution")

        # Framing centering quality
        if face_centered_ratio >= 0.85:
            score += 1.0
            reasons.append("Subject maintained in 9:16 vertical center")
        elif face_centered_ratio < 0.60:
            score -= 1.5
            penalties.append("Frequent subject drift outside 9:16 vertical safe zone")

        # Layout stability / jitter check
        if layout_switches > 2:
            score -= 2.5
            penalties.append(f"Excessive camera layout switching ({layout_switches} switches)")
        elif layout_mode in {"TRACK", "SPLIT"}:
            reasons.append(f"Stable {layout_mode} 9:16 composition")

        return max(0.0, min(10.0, score)), reasons, penalties
