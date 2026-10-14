from typing import List, Optional, Tuple
from services.detection.thought_detector import SentenceWindow


class ThoughtBoundaryMatcher:
    """Aligns candidate timestamps with underlying sentence thought boundaries."""

    def __init__(self, max_start_expansion: float = 2.0, max_end_expansion: float = 3.0):
        self.max_start_expansion = max_start_expansion
        self.max_end_expansion = max_end_expansion

    def match_boundaries(
        self,
        candidate_start: float,
        candidate_end: float,
        sentences: List[SentenceWindow],
    ) -> Tuple[float, float, List[str]]:
        reasons = []
        best_start = candidate_start
        best_end = candidate_end

        if not sentences:
            return best_start, best_end, ["No sentence metadata available"]

        # 1. Match Start Boundary: find sentence overlapping or starting right before candidate_start
        for s in sentences:
            # If candidate_start cuts into the beginning of a sentence by <= max_start_expansion
            if s.start <= candidate_start <= s.end:
                shift = candidate_start - s.start
                if shift <= self.max_start_expansion:
                    best_start = s.start
                    reasons.append(f"Expanded start backward by {shift:.2f}s to include full sentence opener")
                break
            elif 0.0 < (s.start - candidate_start) <= 0.8:
                best_start = s.start
                reasons.append(f"Snapped start forward to sentence opener at {s.start:.2f}s")
                break

        # 2. Match End Boundary: find sentence ending right after candidate_end
        for s in sentences:
            if s.start <= candidate_end <= s.end:
                shift = s.end - candidate_end
                if shift <= self.max_end_expansion:
                    best_end = s.end
                    reasons.append(f"Expanded end forward by {shift:.2f}s to complete sentence closure")
                break
            elif 0.0 < (candidate_end - s.end) <= 1.0:
                best_end = s.end
                reasons.append(f"Snapped end backward to clean sentence termination at {s.end:.2f}s")

        return best_start, best_end, reasons
