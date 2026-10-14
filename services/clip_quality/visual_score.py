from typing import Any, Dict, List, Optional, Tuple


class DurationContinuityScorer:
    """Evaluates short-form duration sweet-spot and scene continuity."""

    def evaluate_duration_continuity(
        self,
        duration: float,
        scene_cuts_count: int = 1,
        cut_on_scene_boundary: bool = True,
    ) -> Tuple[float, List[str], List[str]]:
        reasons = []
        penalties = []
        score = 3.0  # baseline

        # Duration sweet spot for TikTok/Reels/Shorts (20s - 60s)
        if 20.0 <= duration <= 60.0:
            score += 1.5
            reasons.append(f"Ideal short-form viral duration ({duration:.1f}s)")
        elif 15.0 <= duration < 20.0 or 60.0 < duration <= 90.0:
            score += 0.5
        elif duration < 10.0:
            score -= 1.5
            penalties.append(f"Sub-optimal short duration ({duration:.1f}s)")
        elif duration > 120.0:
            score -= 1.5
            penalties.append(f"Excessive duration for short-form video ({duration:.1f}s)")

        if cut_on_scene_boundary:
            score += 0.5
            reasons.append("Cut synchronized with visual scene cut boundary")

        return max(0.0, min(5.0, score)), reasons, penalties
