import pytest
from services.context import ContextCompletenessAnalyzer, SentenceRole


def test_context_completeness():
    analyzer = ContextCompletenessAnalyzer()
    sentences = [
        "Kenapa banyak startup gagal di fase awal?",
        "Masalahnya adalah kurangnya riset pasar yang mendalam.",
        "Dan solusinya adalah validasi masalah sebelum membangun produk.",
    ]
    eval_res = analyzer.evaluate(sentences)
    assert eval_res.context_score >= 80.0
    assert eval_res.context_completeness >= 0.80
    assert eval_res.has_unresolved_pronoun is False


def test_unresolved_pronoun():
    analyzer = ContextCompletenessAnalyzer()
    # Opens with 'Dia' without introducing who 'Dia' is
    sentences = [
        "Dia melakukan hal itu karena tidak punya pilihan lain.",
        "Akhirnya semua rencana berantakan.",
    ]
    eval_res = analyzer.evaluate(sentences)
    assert eval_res.has_unresolved_pronoun is True
    assert eval_res.context_score < 70.0
    assert any("pronoun" in p.lower() for p in eval_res.penalties)


def test_context_bridge():
    analyzer = ContextCompletenessAnalyzer()
    sentences = [
        "Banyak orang bingung menentukan prioritas kerja.",
        "Untuk memahami ini coba kita lihat analogi ember bocor.", # Bridge sentence
        "Hasilnya kita bisa tahu mana yang paling mendesak.",
    ]
    eval_res = analyzer.evaluate(sentences)
    assert eval_res.bridge_count >= 1
    assert any("bridge" in r.lower() for r in eval_res.reasons)
