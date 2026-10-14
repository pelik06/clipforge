from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from services.clustering.models import TopicFamily
from services.clustering.provider import SemanticSimilarityProvider, tokenize_clean


class TopicClusterer:
    """Clusters candidate clips into semantic Topic Families and enforces recommendation diversity."""

    def __init__(
        self,
        similarity_threshold: float = 0.25,
        provider_mode: str = "none",
    ):
        self.similarity_threshold = similarity_threshold
        self.similarity_provider = SemanticSimilarityProvider(mode=provider_mode)

    def cluster_clips(self, clips: List[Dict[str, Any]]) -> List[TopicFamily]:
        if not clips:
            return []

        clusters: List[List[Dict[str, Any]]] = []

        for clip in clips:
            text = clip.get("text") or clip.get("title") or ""
            placed = False

            for cluster in clusters:
                # Compare against centroid/first member of cluster
                rep_text = cluster[0].get("text") or cluster[0].get("title") or ""
                sim = self.similarity_provider.compute_similarity(text, rep_text)
                if sim >= self.similarity_threshold:
                    cluster.append(clip)
                    placed = True
                    break

            if not placed:
                clusters.append([clip])

        families: List[TopicFamily] = []
        for idx, cluster in enumerate(clusters, 1):
            family_id = f"family_{idx:02d}"
            members = [c.get("id") or c.get("clip_id") or "" for c in cluster]

            # Collect top keywords
            all_tokens = []
            scores = []
            for c in cluster:
                txt = c.get("text") or c.get("title") or ""
                all_tokens.extend(tokenize_clean(txt))
                raw_s = c.get("score_value") or float(str(c.get("score", "0")).split("/")[0])
                scores.append(float(raw_s))

            top_keywords = [word for word, _ in Counter(all_tokens).most_common(4)]
            label = " & ".join(top_keywords[:2]).title() if top_keywords else f"Topic {idx}"
            avg_s = sum(scores) / max(1, len(scores))

            fam = TopicFamily(
                family_id=family_id,
                topic_label=label,
                keywords=top_keywords,
                members=members,
                avg_score=avg_s,
            )
            families.append(fam)

            # Assign topic_family and topic_label to each clip dict
            for c in cluster:
                c["topic_family"] = family_id
                c["topic_label"] = label

        return families

    def enforce_family_diversity(
        self,
        ranked_clips: List[Dict[str, Any]],
        max_per_family: int = 2,
    ) -> List[Dict[str, Any]]:
        """Re-order or penalize excessive clips from the exact same topic family."""
        if not ranked_clips:
            return []

        family_counts: Dict[str, int] = {}
        primary: List[Dict[str, Any]] = []
        deferred: List[Dict[str, Any]] = []

        for c in ranked_clips:
            fam = c.get("topic_family", "general")
            cnt = family_counts.get(fam, 0)
            if cnt < max_per_family:
                primary.append(c)
                family_counts[fam] = cnt + 1
            else:
                deferred.append(c)

        # Append deferred clips at the end
        result = primary + deferred
        for rank_idx, c in enumerate(result, 1):
            c["rank"] = rank_idx
            c["ranking"] = rank_idx

        return result
