import re
from typing import Any, Dict, List, Optional, Tuple

DANGLING_START_REGEX = re.compile(r"^(dan|tapi|namun|terus|so|atau|karena|sebab|bahwa)\b", re.IGNORECASE)
DANGLING_END_REGEX = re.compile(r"\b(dan|atau|tapi|namun|bahwa|karena|kalau|jika|ketika|yang|untuk|seperti|sebab)$", re.IGNORECASE)
HOOK_QUESTION_REGEX = re.compile(r"(kenapa|mengapa|bagaimana|apa yang|tahukah|pernah gak|pernahkah|\?)\b", re.IGNORECASE)
HOOK_CURIOSITY_REGEX = re.compile(r"(rahasia|ternyata|masalah terbesar|sebenarnya|faktanya|jangan pernah|banyak orang|kuncinya|kesalahan|strategi|alasan)\b", re.IGNORECASE)
HOOK_NUMBER_REGEX = re.compile(r"\b(\d+|satu|dua|tiga|empat|lima|juta|miliar|persen|ribu)\b", re.IGNORECASE)
PAYOFF_MARKER_REGEX = re.compile(r"(hasilnya|kesimpulannya|artinya|sehingga|ujung-ujungnya|kuncinya adalah|solusinya|makanya|akhirnya|terbukti|intinya|inilah)\b", re.IGNORECASE)
FILLER_WORDS = {"eh", "em", "uh", "um", "kayak", "anu", "gitu", "ya kan", "apa ya", "like", "you know"}


class SemanticScorer:
    """Evaluates semantic quality, opening hook, conclusion payoff, and information density."""

    def evaluate_semantic_quality(self, text: str, duration: float, sentences: Optional[List[str]] = None) -> Tuple[float, List[str], List[str]]:
        reasons = []
        penalties = []
        score = 20.0  # baseline

        clean_text = (text or "").strip()
        if not clean_text:
            return 0.0, [], ["No speech transcript available"]

        words = clean_text.split()
        total_words = len(words)
        if total_words < 5:
            return 5.0, [], ["Speech segment too short to form complete thought"]

        # 1. Clean Opening (max +5)
        if not DANGLING_START_REGEX.search(words[0]):
            score += 5.0
            reasons.append("Clean conversational opening without dangling conjunction")
        else:
            score -= 3.0
            penalties.append(f"Opens with dangling conjunction '{words[0]}'")

        # 2. Clean Resolution / Sentence boundary (max +5)
        last_word = re.sub(r"[^\w]", "", words[-1]).lower()
        if not DANGLING_END_REGEX.search(last_word):
            score += 5.0
            reasons.append("Clean conclusion without trailing cutoff")
        else:
            score -= 5.0
            penalties.append(f"Ends abruptly on dangling word '{words[-1]}'")

        # Terminal punctuation bonus (+3)
        if clean_text[-1] in {".", "!", "?"}:
            score += 3.0
            reasons.append("Terminal punctuation confirmed")

        # 3. Filler word density check
        filler_count = sum(1 for w in words if w.lower().strip(".,!?") in FILLER_WORDS)
        filler_ratio = filler_count / max(1, total_words)
        if filler_ratio < 0.08:
            score += 2.0
        elif filler_ratio > 0.20:
            score -= 4.0
            penalties.append(f"High filler speech density ({filler_ratio:.1%})")

        return max(0.0, min(35.0, score)), reasons, penalties

    def evaluate_hook_strength(self, text: str, first_sentence: Optional[str] = None) -> Tuple[float, List[str]]:
        reasons = []
        score = 5.0  # default baseline

        eval_text = first_sentence or " ".join((text or "").split()[:12])
        if not eval_text:
            return score, reasons

        # 1. Question opening (+4.0)
        if HOOK_QUESTION_REGEX.search(eval_text):
            score += 4.0
            reasons.append("Compelling opening question creates curiosity gap")

        # 2. Curiosity / Surprising premise (+4.0)
        if HOOK_CURIOSITY_REGEX.search(eval_text):
            score += 4.0
            reasons.append("Opening contains high-interest curiosity or contrarian keyword")

        # 3. Concrete numbers or quantified claim (+2.0)
        if HOOK_NUMBER_REGEX.search(eval_text):
            score += 2.0
            reasons.append("Quantified specific numbers in hook")

        return max(0.0, min(15.0, score)), reasons

    def evaluate_payoff(self, text: str, sentences: Optional[List[str]] = None) -> Tuple[float, List[str], List[str]]:
        reasons = []
        penalties = []
        score = 5.0  # baseline

        words = (text or "").split()
        if len(words) < 8:
            return 3.0, [], ["Insufficient text for narrative payoff"]

        # Examine the second half of the clip for payoff / conclusion markers
        half_idx = len(words) // 2
        second_half = " ".join(words[half_idx:])

        if PAYOFF_MARKER_REGEX.search(second_half):
            score += 5.0
            reasons.append("Clear payoff resolution marker delivered in second half")
        elif sentences and len(sentences) >= 2:
            score += 3.0
            reasons.append("Multi-sentence progression to conclusion")
        else:
            score -= 2.0
            penalties.append("Setup delivered without definitive resolution payoff")

        return max(0.0, min(10.0, score)), reasons, penalties

    def evaluate_information_density(self, text: str, duration: float) -> Tuple[float, List[str]]:
        reasons = []
        score = 5.0

        words = [w.strip(".,!?").lower() for w in (text or "").split() if w.strip(".,!?")]
        if not words or duration <= 0:
            return 3.0, reasons

        # Words per second (ideal 2.0 to 3.5 wps)
        wps = len(words) / duration
        if 2.0 <= wps <= 3.8:
            score += 2.5
            reasons.append(f"Optimal speech tempo ({wps:.1f} words/sec)")
        elif wps < 1.2:
            score -= 2.0
        elif wps > 4.5:
            score -= 1.0

        # Lexical diversity (unique words / total words)
        unique_words = set(words)
        lexical_diversity = len(unique_words) / len(words)
        if lexical_diversity >= 0.70:
            score += 2.5
            reasons.append("High vocabulary diversity with rich information")
        elif lexical_diversity >= 0.50:
            score += 1.5

        return max(0.0, min(10.0, score)), reasons
