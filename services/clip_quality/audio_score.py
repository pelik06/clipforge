from typing import Any, Dict, List, Optional, Tuple


class AudioReactionScorer:
    """Evaluates audio energy, laughter, applause, and emotional reactions as supporting signal.
    
    Constraint: Audio reactions can contribute at most 10.0 points to the total score.
    A loud moment without semantic depth must never dominate the ranking.
    """

    def evaluate_audio_emotion(
        self,
        audio_reactions: Optional[List[Any]] = None,
        clip_start: float = 0.0,
        clip_end: float = 0.0,
    ) -> Tuple[float, List[str]]:
        reasons = []
        score = 4.0  # neutral baseline for clean conversational speech

        if not audio_reactions:
            return score, ["Clean steady conversational audio"]

        relevant_reactions = []
        for r in audio_reactions:
            r_start = getattr(r, "start", 0.0)
            r_end = getattr(r, "end", 0.0)
            r_conf = getattr(r, "confidence", 0.0)
            r_label = getattr(r, "label", "reaction")

            # Check overlap with clip window
            if r_end > clip_start and r_start < clip_end:
                relevant_reactions.append((r_label, r_conf))

        if relevant_reactions:
            # Reward highest confidence reaction
            best_label, best_conf = max(relevant_reactions, key=lambda x: x[1])
            boost = min(6.0, 3.0 + best_conf * 3.0)
            score += boost
            label_name = best_label.replace("_", " ").title()
            reasons.append(f"Engaging audio reaction ({label_name}, {best_conf:.0%} confidence)")
        else:
            reasons.append("Steady dialogue tone")

        return max(0.0, min(10.0, score)), reasons
