import re
from typing import List, Tuple
from services.context.models import SentenceAnalysis, SentenceRole

BRIDGE_REGEX = re.compile(
    r"(seperti yang (saya|kita)|untuk memahami|masalahnya adalah|yang terjadi sebenarnya|"
    r"coba kita (lihat|pikirkan)|kuncinya ada|nah dalam hal ini|artinya begini|analoginya|"
    r"sebagai contoh|to understand this|the reason why|here is the thing)\b",
    re.IGNORECASE,
)
PAYOFF_REGEX = re.compile(
    r"(hasilnya|kesimpulannya|solusinya|akhirnya|intinya|ujung-ujungnya|terbukti bahwa|"
    r"makanya|inilah kenapa|pelajarannya adalah|the conclusion is|the solution is)\b",
    re.IGNORECASE,
)
HOOK_REGEX = re.compile(
    r"(kenapa|mengapa|bagaimana|apa yang|tahukah|pernah gak|rahasia terbesar|"
    r"masalah paling|jangan pernah|banyak orang salah|\?)\b",
    re.IGNORECASE,
)
FILLER_REGEX = re.compile(
    r"^(apa ya|ya gitu deh|gitu deh|ya pokoknya|kayak gitu sih|you know what i mean)$",
    re.IGNORECASE,
)


class SemanticBridgeDetector:
    """Classifies sentence roles into HOOK, BRIDGE, CONTENT, PAYOFF, and FILLER."""

    def classify_sentence(self, sentence_text: str, index: int = 0, total_sentences: int = 1) -> SentenceAnalysis:
        text = (sentence_text or "").strip()
        if not text:
            return SentenceAnalysis(text="", role=SentenceRole.FILLER, confidence=0.5, reason="Empty text")

        # 1. Opening sentence check for HOOK
        if index == 0 and HOOK_REGEX.search(text):
            return SentenceAnalysis(
                text=text,
                role=SentenceRole.HOOK,
                confidence=0.88,
                reason="Opening question or curiosity gap creates a strong conversational hook",
            )

        # 2. Payoff check in conclusion / later sentences
        if index >= max(1, total_sentences - 2) and PAYOFF_REGEX.search(text):
            return SentenceAnalysis(
                text=text,
                role=SentenceRole.PAYOFF,
                confidence=0.90,
                reason="Delivers conclusive resolution, outcome, or core lesson payoff",
            )

        # 3. Semantic Bridge check
        if BRIDGE_REGEX.search(text):
            return SentenceAnalysis(
                text=text,
                role=SentenceRole.BRIDGE,
                confidence=0.85,
                reason="Serves as semantic bridge connecting contextual setup to resolution",
            )

        # 4. Pure filler check
        if FILLER_REGEX.search(text.lower()):
            return SentenceAnalysis(
                text=text,
                role=SentenceRole.FILLER,
                confidence=0.80,
                reason="Conversational filler without standalone semantic payload",
            )

        # 5. Default content sentence
        return SentenceAnalysis(
            text=text,
            role=SentenceRole.CONTENT,
            confidence=0.75,
            reason="Core informative content sentence",
        )

    def analyze_passage(self, sentences: List[str]) -> List[SentenceAnalysis]:
        results = []
        total = len(sentences)
        for i, s in enumerate(sentences):
            results.append(self.classify_sentence(s, index=i, total_sentences=total))
        return results
