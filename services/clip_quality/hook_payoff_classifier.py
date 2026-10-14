import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class HookType(str, Enum):
    QUESTION = "QUESTION"
    STRONG_CLAIM = "STRONG_CLAIM"
    SURPRISE = "SURPRISE"
    CONTRAST = "CONTRAST"
    NUMBER = "NUMBER"
    PERSONAL_EXPERIENCE = "PERSONAL_EXPERIENCE"
    EMOTIONAL = "EMOTIONAL"
    CURIOSITY_GAP = "CURIOSITY_GAP"
    GENERAL = "GENERAL"


class PayoffType(str, Enum):
    ANSWER = "ANSWER"
    CONCLUSION = "CONCLUSION"
    REVELATION = "REVELATION"
    LESSON = "LESSON"
    PUNCHLINE = "PUNCHLINE"
    RESULT = "RESULT"
    RECOMMENDATION = "RECOMMENDATION"
    GENERAL = "GENERAL"


@dataclass
class HookClassification:
    category: HookType
    confidence: float
    evidence: str


@dataclass
class PayoffClassification:
    category: PayoffType
    confidence: float
    evidence: str


class HookPayoffClassifier:
    """Categorizes conversational hook and payoff types with fine-grained pattern recognition."""

    def classify_hook(self, text: str) -> HookClassification:
        clean = (text or "").strip()
        if not clean:
            return HookClassification(category=HookType.GENERAL, confidence=0.5, evidence="Empty text")

        lower = clean.lower()

        # 1. Question hook
        if "?" in clean or re.search(r"^(kenapa|mengapa|bagaimana|apa yang|apakah|tahukah|pernah gak)\b", lower):
            return HookClassification(category=HookType.QUESTION, confidence=0.92, evidence="Opening interrogative question")

        # 2. Number / Quantified hook
        if re.search(r"\b(\d+|satu|dua|tiga|empat|lima|sepuluh|juta|miliar|persen|%)\b", lower):
            return HookClassification(category=HookType.NUMBER, confidence=0.88, evidence="Concrete quantitative metric or number")

        # 3. Curiosity gap
        if re.search(r"\b(rahasia|ternyata|faktanya|masalah terbesar|banyak orang salah|kuncinya)\b", lower):
            return HookClassification(category=HookType.CURIOSITY_GAP, confidence=0.90, evidence="Curiosity gap keyword")

        # 4. Personal experience
        if re.search(r"\b(gue pernah|saya pernah|pengalaman gue|waktu itu gue|pertama kali gue)\b", lower):
            return HookClassification(category=HookType.PERSONAL_EXPERIENCE, confidence=0.85, evidence="First-person personal narrative hook")

        # 5. Surprise
        if re.search(r"\b(kaget banget|gak nyangka|siapa sangka|plot twist|anehnya)\b", lower):
            return HookClassification(category=HookType.SURPRISE, confidence=0.86, evidence="Surprise or unexpected discovery")

        # 6. Contrast
        if re.search(r"\b(banyak orang kira|padahal|bukan karena|sebenarnya bukan|melainkan)\b", lower):
            return HookClassification(category=HookType.CONTRAST, confidence=0.84, evidence="Cognitive contrast premise")

        # 7. Strong claim
        if re.search(r"\b(pasti|selalu|tidak ada yang|satu-satunya|paling penting|mustahil)\b", lower):
            return HookClassification(category=HookType.STRONG_CLAIM, confidence=0.82, evidence="Bold definitive claim")

        # 8. Emotional
        if re.search(r"\b(takut|sedih|marah|kecewa|senang banget|gila banget)\b", lower):
            return HookClassification(category=HookType.EMOTIONAL, confidence=0.80, evidence="High affective emotion marker")

        return HookClassification(category=HookType.GENERAL, confidence=0.60, evidence="Conversational premise")

    def classify_payoff(self, text: str, full_clip_text: Optional[str] = None) -> PayoffClassification:
        clean = (text or "").strip()
        if not clean:
            return PayoffClassification(category=PayoffType.GENERAL, confidence=0.5, evidence="Empty text")

        lower = clean.lower()

        # 1. Lesson / Rule
        if re.search(r"\b(pelajarannya|kuncinya|makanya harus|jangan sampai|prinsipnya|yang penting)\b", lower):
            return PayoffClassification(category=PayoffType.LESSON, confidence=0.90, evidence="Core moral, key rule, or takeaway lesson")

        # 2. Recommendation / Actionable advice
        if re.search(r"\b(solusinya|saran gue|mendingan|tipsnya|langkah terbaik|rekomendasi)\b", lower):
            return PayoffClassification(category=PayoffType.RECOMMENDATION, confidence=0.91, evidence="Prescriptive actionable solution")

        # 3. Result / Direct Outcome
        if re.search(r"\b(hasilnya|akhirnya berhasil|ujung-ujungnya|dampaknya|terbukti)\b", lower):
            return PayoffClassification(category=PayoffType.RESULT, confidence=0.89, evidence="Empirical resolution or outcome delivered")

        # 4. Conclusion
        if re.search(r"\b(kesimpulannya|intinya|jadi kesimpulannya|dari sini kita tahu)\b", lower):
            return PayoffClassification(category=PayoffType.CONCLUSION, confidence=0.88, evidence="Structured logical conclusion")

        # 5. Revelation / Breakthrough
        if re.search(r"\b(ternyata begini|baru sadar|terbongkar|inilah alasannya)\b", lower):
            return PayoffClassification(category=PayoffType.REVELATION, confidence=0.85, evidence="Key revelation or insight epiphany")

        # 6. Punchline / Humorous payoff
        if re.search(r"\b(malah|ya gitu deh|ngakak|konyol banget|eh zonk)\b", lower):
            return PayoffClassification(category=PayoffType.PUNCHLINE, confidence=0.80, evidence="Humorous or satirical punchline")

        # 7. Answer to prior inquiry
        if re.search(r"\b(jawabannya adalah|karena|alasannya|itu disebabkan)\b", lower):
            return PayoffClassification(category=PayoffType.ANSWER, confidence=0.83, evidence="Direct explanatory answer")

        return PayoffClassification(category=PayoffType.GENERAL, confidence=0.60, evidence="Dialogue continuation")
