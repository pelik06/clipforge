import re
from typing import List, Optional, Tuple

from services.boundary_refinement.models import BoundaryEvaluation

DANGLING_START_REGEX = re.compile(r"^(dan|terus|jadi|karena|itu|nah|namun|atau|so|tapi)\b", re.IGNORECASE)
DANGLING_END_REGEX = re.compile(r"\b(karena|jadi|kalau|dan|atau|bahwa|ketika|yang|untuk|sebab|tapi)$", re.IGNORECASE)


class SentenceBoundaryAnalyzer:
    """Evaluates opening and closing sentence completeness and dangling conjunctions."""

    def evaluate(self, text: str) -> BoundaryEvaluation:
        clean = (text or "").strip()
        if not clean:
            return BoundaryEvaluation(is_clean_start=False, is_clean_end=False, reasons=["Empty speech text"])

        words = clean.split()
        reasons = []
        is_clean_start = True
        is_clean_end = True
        start_word = words[0].lower().strip(".,!?")
        end_word = words[-1].lower().strip(".,!?")

        start_penalty = 0.0
        end_penalty = 0.0

        if DANGLING_START_REGEX.search(start_word):
            is_clean_start = False
            start_penalty = 12.0
            reasons.append(f"Incomplete start: opens with dangling conjunction '{start_word}'")

        if DANGLING_END_REGEX.search(end_word):
            is_clean_end = False
            end_penalty = 15.0
            reasons.append(f"Incomplete end: terminates with dangling word '{end_word}'")
        elif clean[-1] not in {".", "!", "?"}:
            is_clean_end = False
            end_penalty = 8.0
            reasons.append("Missing terminal sentence punctuation (cut off mid-sentence)")

        if is_clean_start:
            reasons.append("Clean conversational sentence start")
        if is_clean_end:
            reasons.append("Complete sentence closure")

        return BoundaryEvaluation(
            is_clean_start=is_clean_start,
            is_clean_end=is_clean_end,
            dangling_start_word=start_word if not is_clean_start else None,
            dangling_end_word=end_word if not is_clean_end else None,
            start_penalty=start_penalty,
            end_penalty=end_penalty,
            reasons=reasons,
        )
