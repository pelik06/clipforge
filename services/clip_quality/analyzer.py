from typing import Any, Dict, List, Optional

from services.clip_quality.audio_score import AudioReactionScorer
from services.clip_quality.caption_score import CaptionQualityScorer
from services.clip_quality.models import ClipQualityFeatures, QualityBreakdown
from services.clip_quality.semantic_score import SemanticScorer
from services.clip_quality.speaker_score import SpeakerFramingScorer
from services.clip_quality.visual_score import DurationContinuityScorer


class ClipQualityAnalyzer:
    """Computes comprehensive composite quality score for short-form candidate clips.
    
    Formula:
      35% Semantic Quality
      15% Hook Strength
      10% Payoff / Resolution
      10% Information Density
      10% Emotional / Audio Reaction
      10% Speaker + Framing Quality
       5% Caption Quality
       5% Duration / Continuity Quality
    ----------------------------------
     100% Total Composite Score
    """

    def __init__(self):
        self.semantic_scorer = SemanticScorer()
        self.audio_scorer = AudioReactionScorer()
        self.speaker_scorer = SpeakerFramingScorer()
        self.caption_scorer = CaptionQualityScorer()
        self.duration_scorer = DurationContinuityScorer()

    def analyze_clip(
        self,
        clip_id: str,
        text: str,
        duration: float,
        sentences: Optional[List[str]] = None,
        audio_reactions: Optional[List[Any]] = None,
        clip_start: float = 0.0,
        clip_end: float = 0.0,
        active_speaker_confidence: float = 0.85,
        face_detected: bool = True,
        layout_mode: str = "TRACK",
        layout_switches: int = 0,
        face_centered_ratio: float = 0.90,
        avg_chunk_size: float = 3.5,
        face_collision_detected: bool = False,
        safe_area_compliant: bool = True,
        scene_cuts_count: int = 1,
        cut_on_scene_boundary: bool = True,
    ) -> ClipQualityFeatures:
        all_reasons: List[str] = []
        all_penalties: List[str] = []

        # 1. Semantic Quality (max 35)
        sem_score, sem_reasons, sem_penalties = self.semantic_scorer.evaluate_semantic_quality(
            text=text, duration=duration, sentences=sentences
        )
        all_reasons.extend(sem_reasons)
        all_penalties.extend(sem_penalties)

        # 2. Hook Strength (max 15)
        first_sent = sentences[0] if sentences else None
        hook_score, hook_reasons = self.semantic_scorer.evaluate_hook_strength(
            text=text, first_sentence=first_sent
        )
        all_reasons.extend(hook_reasons)

        # 3. Payoff / Resolution (max 10)
        pay_score, pay_reasons, pay_penalties = self.semantic_scorer.evaluate_payoff(
            text=text, sentences=sentences
        )
        all_reasons.extend(pay_reasons)
        all_penalties.extend(pay_penalties)

        # 4. Information Density (max 10)
        info_score, info_reasons = self.semantic_scorer.evaluate_information_density(
            text=text, duration=duration
        )
        all_reasons.extend(info_reasons)

        # 5. Emotional / Audio Reaction (max 10)
        emo_score, emo_reasons = self.audio_scorer.evaluate_audio_emotion(
            audio_reactions=audio_reactions, clip_start=clip_start, clip_end=clip_end
        )
        all_reasons.extend(emo_reasons)

        # 6. Speaker + Framing Quality (max 10)
        spk_score, spk_reasons, spk_penalties = self.speaker_scorer.evaluate_speaker_framing(
            active_speaker_confidence=active_speaker_confidence,
            face_detected=face_detected,
            layout_mode=layout_mode,
            layout_switches=layout_switches,
            face_centered_ratio=face_centered_ratio,
        )
        all_reasons.extend(spk_reasons)
        all_penalties.extend(spk_penalties)

        # 7. Caption Quality (max 5)
        cap_score, cap_reasons, cap_penalties = self.caption_scorer.evaluate_caption_quality(
            avg_chunk_size=avg_chunk_size,
            face_collision_detected=face_collision_detected,
            safe_area_compliant=safe_area_compliant,
            has_word_timestamps=True,
        )
        all_reasons.extend(cap_reasons)
        all_penalties.extend(cap_penalties)

        # 8. Duration / Continuity (max 5)
        dur_score, dur_reasons, dur_penalties = self.duration_scorer.evaluate_duration_continuity(
            duration=duration,
            scene_cuts_count=scene_cuts_count,
            cut_on_scene_boundary=cut_on_scene_boundary,
        )
        all_reasons.extend(dur_reasons)
        all_penalties.extend(dur_penalties)

        # Total Composite Score (0.0 to 100.0)
        total = (
            sem_score
            + hook_score
            + pay_score
            + info_score
            + emo_score
            + spk_score
            + cap_score
            + dur_score
        )
        total = max(0.0, min(100.0, total))

        breakdown = QualityBreakdown(
            semantic=sem_score,
            hook=hook_score,
            payoff=pay_score,
            information=info_score,
            emotion=emo_score,
            speaker_framing=spk_score,
            caption=cap_score,
            duration_continuity=dur_score,
            total=total,
        )

        return ClipQualityFeatures(
            clip_id=clip_id,
            breakdown=breakdown,
            reasons=list(dict.fromkeys(all_reasons)),  # deduplicate while preserving order
            penalties=list(dict.fromkeys(all_penalties)),
            raw_metrics={
                "duration": duration,
                "text_length": len(text.split()),
                "layout_mode": layout_mode,
                "active_speaker_confidence": active_speaker_confidence,
            },
        )
