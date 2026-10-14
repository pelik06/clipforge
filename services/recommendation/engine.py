from typing import Any, Dict, List, Optional
from services.clip_quality.ranking import ClipRanker
from services.recommendation.models import RecommendationItem


class RecommendationEngine:
    """Selects top recommended clips balancing quality, diversity, and completeness."""

    def __init__(self, default_top_k: int = 5, min_score_threshold: float = 70.0):
        self.default_top_k = default_top_k
        self.min_score_threshold = min_score_threshold
        self.ranker = ClipRanker()

    def recommend_clips(
        self,
        clips: List[Dict[str, Any]],
        quality_map: Optional[Dict[str, Any]] = None,
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Rank and tag candidate clips with explicit recommendation flags and reasons."""
        if not clips:
            return []

        limit = top_k or self.default_top_k

        # 1. Rank using diversity-aware ClipRanker
        ranked = self.ranker.rank_clips(clips, quality_map=quality_map)

        results: List[Dict[str, Any]] = []
        rec_count = 0

        for item in ranked:
            score_val = float(item.get("score_value") or float(str(item.get("score", "0")).split("/")[0]))
            reasons = item.get("why_this_clip", [])
            rank = item.get("rank", len(results) + 1)

            # Recommendation eligibility
            is_rec = False
            rec_reasons = []

            if rec_count < limit and score_val >= self.min_score_threshold:
                is_rec = True
                rec_count += 1
                rec_reasons.append("Top quality score surpassing benchmark")
                if reasons:
                    rec_reasons.extend(reasons[:3])
            elif score_val < self.min_score_threshold:
                rec_reasons.append(f"Score below recommendation threshold ({score_val:.1f} < {self.min_score_threshold:.1f})")
            else:
                rec_reasons.append(f"Rank #{rank} deferred by Top-{limit} limit")

            out_item = dict(item)
            out_item["ranking"] = rank
            out_item["is_recommended"] = is_rec
            out_item["recommendation_reasons"] = rec_reasons
            results.append(out_item)

        return results
