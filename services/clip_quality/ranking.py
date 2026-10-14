from typing import Any, Dict, List, Optional
from services.clip_quality.models import ClipQualityFeatures


class ClipRanker:
    """Ranks candidate clips using quality composite score, temporal deduplication, and diversity penalty."""

    def __init__(
        self,
        temporal_overlap_threshold: float = 0.35,
        diversity_opening_penalty: float = 12.0,
        diversity_speaker_penalty: float = 4.0,
    ):
        self.temporal_overlap_threshold = temporal_overlap_threshold
        self.diversity_opening_penalty = diversity_opening_penalty
        self.diversity_speaker_penalty = diversity_speaker_penalty

    def rank_clips(
        self,
        clips: List[Dict[str, Any]],
        quality_map: Optional[Dict[str, ClipQualityFeatures]] = None,
        temporal_overlap_threshold: Optional[float] = None,
        diversity_opening_penalty: Optional[float] = None,
        diversity_speaker_penalty: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        if not clips:
            return []
        overlap_thresh = temporal_overlap_threshold if temporal_overlap_threshold is not None else self.temporal_overlap_threshold
        opening_pen = diversity_opening_penalty if diversity_opening_penalty is not None else self.diversity_opening_penalty
        speaker_pen = diversity_speaker_penalty if diversity_speaker_penalty is not None else self.diversity_speaker_penalty

        # 1. Attach composite quality score
        scored_items = []
        for c in clips:
            c_id = c.get("id") or c.get("clip_id") or ""
            q_feat = quality_map.get(c_id) if quality_map else None
            score_field = c.get("score_raw")
            if score_field is None:
                score_str = str(c.get("score") or "0.0").split("/")[0]
                try:
                    raw_score = float(score_str)
                except ValueError:
                    raw_score = 0.0
            else:
                raw_score = float(score_field)

            if q_feat:
                base_score = q_feat.breakdown.total
                reasons = list(q_feat.reasons)
                breakdown = q_feat.breakdown.to_dict()
            else:
                base_score = raw_score
                reasons = list(c.get("reasons", []))
                breakdown = {}
            scored_items.append({
                "clip": c,
                "base_score": base_score,
                "final_score": base_score,
                "reasons": reasons,
                "breakdown": breakdown,
                "start": float(c.get("start_time", 0.0)),
                "end": float(c.get("end_time", 0.0)),
                "speaker": c.get("speaker_track_id", "face_01"),
                "title": c.get("title", ""),
                "text": c.get("text", ""),
            })

        # 2. Sort by base score descending
        scored_items.sort(key=lambda x: x["base_score"], reverse=True)

        # 3. Apply Diversity & Temporal Deduplication Penalty
        ranked_results: List[Dict[str, Any]] = []
        selected_intervals = []
        selected_openings = []
        speaker_counts: Dict[str, int] = {}

        for item in scored_items:
            start = item["start"]
            end = item["end"]
            dur = max(0.01, end - start)
            penalty = 0.0

            # A. Temporal Overlap Check (NMS-style IoU penalty)
            for s_start, s_end in selected_intervals:
                overlap = max(0.0, min(end, s_end) - max(start, s_start))
                union = max(end, s_end) - min(start, s_start)
                iou = overlap / max(0.01, union) if union > 0 else 0.0
                containment = overlap / dur

                if iou > overlap_thresh or containment > 0.50:
                    penalty += 35.0  # heavy overlap penalty

            # B. Opening Phrase Diversity Check
            words = item["text"].split()
            opening_prefix = " ".join(words[:4]).lower() if len(words) >= 4 else ""
            if opening_prefix and any(opening_prefix == op for op in selected_openings):
                penalty += opening_pen
                item["reasons"].append(f"Opening diversity adjustment (-{opening_pen:.0f})")

            # C. Speaker Dominance Diversity Check
            spk = item["speaker"]
            spk_count = speaker_counts.get(spk, 0)
            if spk_count >= 2:
                penalty += speaker_pen * (spk_count - 1)

            adj_score = max(0.0, item["base_score"] - penalty)
            item["final_score"] = round(adj_score, 1)

            # Record selection metrics
            selected_intervals.append((start, end))
            if opening_prefix:
                selected_openings.append(opening_prefix)
            speaker_counts[spk] = speaker_counts.get(spk, 0) + 1

        # Re-sort after diversity penalty adjustments
        scored_items.sort(key=lambda x: x["final_score"], reverse=True)

        for rank_idx, item in enumerate(scored_items, 1):
            clip_dict = dict(item["clip"])
            clip_dict["rank"] = rank_idx
            clip_dict["ranking"] = rank_idx
            clip_dict["score_value"] = item["final_score"]
            clip_dict["quality_breakdown"] = item["breakdown"]
            clip_dict["why_this_clip"] = item["reasons"][:5]
            ranked_results.append(clip_dict)

        return ranked_results
