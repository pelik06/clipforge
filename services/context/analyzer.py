import re
from typing import List, Optional

from services.context.bridge_detector import SemanticBridgeDetector
from services.context.models import ContextEvaluation, SentenceRole

UNRESOLVED_PRONOUNS_REGEX = re.compile(
    r"^(dia|ia|mereka|beliau|he|she|they)\b",
    re.IGNORECASE,
)
DEICTIC_OPENING_REGEX = re.compile(
    r"^(karena itu|gara-gara itu|hal itu|gara-gara hal ini|makanya begitu|oleh karena itu)\b",
    re.IGNORECASE,
)


class ContextCompletenessAnalyzer:
    """Evaluates context preservation, pronoun references, and semantic bridges."""

    def __init__(self):
        self.bridge_detector = SemanticBridgeDetector()

    def evaluate(self, sentences: List[str], full_text: Optional[str] = None) -> ContextEvaluation:
        text = full_text or " ".join(sentences)
        s_list = sentences or [text]
        reasons = []
        penalties = []
        unresolved = []

        score = 80.0  # baseline
        has_unresolved_pronoun = False

        if not s_list or not text.strip():
            return ContextEvaluation(
                context_score=0.0,
                context_completeness=0.0,
                has_unresolved_pronoun=False,
                reasons=["Empty text"],
            )

        # 1. Opening Pronoun Dependency Check
        first_sentence = s_list[0].strip()
        first_words = first_sentence.split()
        if first_words:
            opener = first_words[0].lower().strip(".,!?")
            if UNRESOLVED_PRONOUNS_REGEX.search(opener):
                has_unresolved_pronoun = True
                unresolved.append(f"Opening 3rd person pronoun '{opener}' without explicit antecedent")
                score -= 25.0
                penalties.append(f"Unresolved opening pronoun '{opener}' creates context ambiguity")

            if DEICTIC_OPENING_REGEX.search(first_sentence):
                unresolved.append("Deictic reference ('karena itu'/'hal itu') missing preceding context setup")
                score -= 20.0
                penalties.append("Clip opens with deictic reference dependent on prior speech")

        # 2. Semantic Bridge Analysis
        analyses = self.bridge_detector.analyze_passage(s_list)
        bridges = [a.text for a in analyses if a.role == SentenceRole.BRIDGE]
        if bridges:
            score += min(15.0, len(bridges) * 7.5)
            reasons.append(f"Identified {len(bridges)} semantic bridge(s) connecting premise to payoff")

        # 3. Content Sentence Continuity
        content_count = sum(1 for a in analyses if a.role in {SentenceRole.CONTENT, SentenceRole.PAYOFF})
        if content_count >= 2:
            score += 5.0
            reasons.append("Sufficient content sentences for standalone conversational comprehension")
        elif content_count == 1:
            reasons.append("Single statement thought unit")

        if not has_unresolved_pronoun and not unresolved:
            reasons.append("Self-contained conversational context without missing pronouns")

        final_score = max(0.0, min(100.0, score))
        completeness = round(final_score / 100.0, 2)

        return ContextEvaluation(
            context_score=final_score,
            context_completeness=completeness,
            has_unresolved_pronoun=has_unresolved_pronoun,
            unresolved_references=unresolved,
            bridge_count=len(bridges),
            bridge_sentences=bridges,
            reasons=reasons,
            penalties=penalties,
        )
