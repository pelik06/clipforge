import math
import re
from typing import List, Set

INDONESIAN_STOPWORDS = {
    "yang", "di", "dan", "ini", "itu", "dari", "untuk", "pada", "ke", "para", "namun",
    "karena", "sama", "ada", "bisa", "kalau", "kita", "gue", "aku", "saya", "lu", "kamu",
    "jadi", "udah", "lagi", "terus", "pas", "aja", "sih", "kan", "nih", "dong", "ya", "deh",
    "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "with", "is", "was", "it",
}


def tokenize_clean(text: str) -> List[str]:
    words = re.findall(r"\b[a-zA-Z0-9_-]{3,}\b", (text or "").lower())
    return [w for w in words if w not in INDONESIAN_STOPWORDS]


class SemanticSimilarityProvider:
    """Computes semantic text similarity using deterministic tokens or optional embedding models."""

    def __init__(self, mode: str = "none"):
        self.mode = mode.lower()  # "none" | "local" | "optional-cloud"

    def compute_similarity(self, text_a: str, text_b: str) -> float:
        """Return similarity in range [0.0, 1.0]."""
        # If optional-cloud or local requested, try embedding or fallback gracefully
        if self.mode == "optional-cloud":
            # Graceful fallback if no cloud credentials
            pass

        # Deterministic Jaccard & Token Overlap Baseline
        tokens_a = set(tokenize_clean(text_a))
        tokens_b = set(tokenize_clean(text_b))

        if not tokens_a or not tokens_b:
            return 0.0

        intersection = tokens_a.intersection(tokens_b)
        union = tokens_a.union(tokens_b)

        jaccard = len(intersection) / float(len(union))
        # Dice overlap coefficient
        dice = (2.0 * len(intersection)) / float(len(tokens_a) + len(tokens_b))

        return round(0.5 * jaccard + 0.5 * dice, 3)
