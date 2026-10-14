from typing import Any, Dict, List, Optional, Tuple
from core.models.transcript import Word


class PauseBoundaryAnalyzer:
    """Detects speech pauses and aligns clip cuts into acoustic silence valleys."""

    def find_nearest_pause(
        self,
        target_timestamp: float,
        words: List[Word],
        search_window: float = 1.5,
        min_pause_duration: float = 0.20,
    ) -> Optional[Tuple[float, float]]:
        """Return (pause_start, pause_end) within search_window of target_timestamp if found."""
        if not words:
            return None

        best_pause = None
        best_dist = 999.0

        for i in range(len(words) - 1):
            w_curr = words[i]
            w_next = words[i + 1]
            gap = w_next.start - w_curr.end

            if gap >= min_pause_duration:
                # Pause center
                p_center = round((w_curr.end + w_next.start) / 2.0, 3)
                dist = abs(p_center - target_timestamp)
                if dist <= search_window and dist < best_dist:
                    best_dist = dist
                    best_pause = (w_curr.end, w_next.start)

        return best_pause

    def align_timestamp_to_pause(
        self,
        target_timestamp: float,
        words: List[Word],
        is_start: bool = True,
        max_shift: float = 2.0,
    ) -> float:
        """Snap timestamp into an adjacent pause valley without exceeding max_shift."""
        pause = self.find_nearest_pause(target_timestamp, words, search_window=max_shift)
        if not pause:
            return target_timestamp

        p_start, p_end = pause
        p_center = round((p_start + p_end) / 2.0, 3)

        if abs(p_center - target_timestamp) <= max_shift:
            return p_center
        return target_timestamp
