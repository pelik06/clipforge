import pytest
from services.clip_quality import HookPayoffClassifier, HookType, PayoffType


def test_question_hook():
    classifier = HookPayoffClassifier()
    res = classifier.classify_hook("Kenapa 99% orang tidak pernah mencapai financial freedom?")
    assert res.category == HookType.QUESTION
    assert res.confidence >= 0.90


def test_curiosity_gap():
    classifier = HookPayoffClassifier()
    res = classifier.classify_hook("Inilah rahasia terbesar industri perbankan yang jarang dibahas.")
    assert res.category == HookType.CURIOSITY_GAP
    assert res.confidence >= 0.88


def test_strong_claim():
    classifier = HookPayoffClassifier()
    res = classifier.classify_hook("Paling penting dalam bisnis adalah menjaga arus kas positif.")
    assert res.category == HookType.STRONG_CLAIM


def test_number_hook():
    classifier = HookPayoffClassifier()
    res = classifier.classify_hook("Ada 3 langkah sederhana untuk meningkatkan fokus harian.")
    assert res.category == HookType.NUMBER


def test_answer_payoff():
    classifier = HookPayoffClassifier()
    res = classifier.classify_payoff("Jawabannya adalah karena otak manusia menyukai kebiasaan berulang.")
    assert res.category == PayoffType.ANSWER


def test_lesson_payoff():
    classifier = HookPayoffClassifier()
    res = classifier.classify_payoff("Pelajarannya adalah jangan pernah mengabaikan biaya tak terduga.")
    assert res.category == PayoffType.LESSON
    assert res.confidence >= 0.88


def test_punchline():
    classifier = HookPayoffClassifier()
    res = classifier.classify_payoff("Pas udah bayar mahal eh zonk gak ada apa-apanya ngakak.")
    assert res.category == PayoffType.PUNCHLINE
