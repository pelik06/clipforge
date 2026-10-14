from typing import Any, Dict, List, Optional, Tuple


class CaptionQualityScorer:
    """Evaluates subtitle readability, adaptive chunk cadence, and safe-area compliance."""

    def evaluate_caption_quality(
        self,
        avg_chunk_size: float = 3.5,
        face_collision_detected: bool = False,
        safe_area_compliant: bool = True,
        has_word_timestamps: bool = True,
    ) -> Tuple[float, List[str], List[str]]:
        reasons = []
        penalties = []
        score = 3.0  # baseline

        if has_word_timestamps:
            score += 1.0
            reasons.append("Millisecond word-level timing synchronization")

        # Chunk cadence check
        if 2.0 <= avg_chunk_size <= 4.0:
            score += 0.5
            reasons.append("Clean 2-4 word rhythmic caption chunking")
        elif avg_chunk_size > 6.0:
            score -= 1.0
            penalties.append("Overcrowded subtitle chunks")

        # Safe area / face collision check
        if safe_area_compliant and not face_collision_detected:
            score += 0.5
            reasons.append("Captions clear of active speaker face and platform safe margins")
        elif face_collision_detected:
            score -= 2.0
            penalties.append("Captions occlude active speaker face")

        return max(0.0, min(5.0, score)), reasons, penalties
