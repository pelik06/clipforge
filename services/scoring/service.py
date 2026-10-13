from typing import List

from core.models.candidate import CandidateMoment


class MomentScorer:
    """Rank candidate moments using streamer acoustic and transcript signals.
    
    Provides transparent scoring without claiming fake AI models.
    Applies temporal Non-Maximum Suppression (NMS) to eliminate duplicate overlapping clips.
    """

    def __init__(
        self,
        weight_audio: float = 0.35,
        weight_reaction: float = 0.25,
        weight_speech: float = 0.20,
        weight_sentence: float = 0.10,
        weight_duration: float = 0.10,
    ):
        self.w_audio = weight_audio
        self.w_reaction = weight_reaction
        self.w_speech = weight_speech
        self.w_sentence = weight_sentence
        self.w_duration = weight_duration

    def score(
        self,
        candidates: List[CandidateMoment],
        top_n: int = 3,
        max_overlap_ratio: float = 0.35,
    ) -> List[CandidateMoment]:
        """Compute transparent scores, generate reason strings, and suppress overlapping duplicates."""
        if not candidates:
            return []

        # 1. Score each candidate
        scored: List[CandidateMoment] = []
        for c in candidates:
            sig = c.signals
            audio_val = sig.get("audio_energy", 0.5)
            reaction_val = sig.get("reaction_signal", 0.5)
            speech_val = sig.get("speech_density", 0.5)
            sentence_val = sig.get("sentence_completeness", 0.5)
            duration_val = sig.get("duration_score", 0.5)

            raw_score = (
                self.w_audio * audio_val
                + self.w_reaction * reaction_val
                + self.w_speech * speech_val
                + self.w_sentence * sentence_val
                + self.w_duration * duration_val
            )
            # Normalize to 55-98 range for practical streamer scoring
            final_score = round(55.0 + (raw_score * 43.0), 1)
            c.score = min(98.0, max(50.0, final_score))

            # Grounded transparent reasons
            reasons = []
            if reaction_val > 0.65:
                reasons.append("High acoustic reaction energy (volume peak)")
            elif audio_val > 0.6:
                reasons.append("Consistent active acoustic volume")

            if speech_val > 0.65:
                reasons.append("High speech density / engaging pacing")

            if sentence_val >= 0.9:
                reasons.append("Complete sentence thought with clear punchline")

            if duration_val > 0.7:
                reasons.append(f"Optimal short-form duration ({c.duration:.1f}s)")

            if not reasons:
                reasons.append(f"Highlight candidate window ({c.duration:.1f}s)")

            c.reasons = reasons
            scored.append(c)

        # 2. Sort by score descending
        scored.sort(key=lambda m: m.score, reverse=True)

        # 3. Duplicate Suppression (Temporal Non-Maximum Suppression)
        selected: List[CandidateMoment] = []
        for cand in scored:
            is_duplicate = False
            for prev in selected:
                # Calculate temporal intersection
                overlap_start = max(cand.start, prev.start)
                overlap_end = min(cand.end, prev.end)
                if overlap_end > overlap_start:
                    overlap_dur = overlap_end - overlap_start
                    min_dur = min(cand.duration, prev.duration)
                    if (overlap_dur / min_dur) > max_overlap_ratio:
                        is_duplicate = True
                        break

            if not is_duplicate:
                selected.append(cand)
                if len(selected) >= top_n:
                    break

        return selected if selected else scored[:top_n]
