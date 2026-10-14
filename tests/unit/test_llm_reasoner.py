import pytest
from core.models.candidate import CandidateMoment
from services.scoring.llm_reasoner import MomentReasoner


def test_llm_optional_fallback():
    """Verify that when no API key or provider is none, pipeline proceeds deterministically without network calls."""
    reasoner = MomentReasoner(provider="none")
    assert reasoner.is_enabled is False

    candidates = [
        CandidateMoment(start=10.0, end=35.0, score=85.0, reasons=["Deterministic complete thought"]),
        CandidateMoment(start=50.0, end=78.0, score=82.0, reasons=["Deterministic complete thought"]),
    ]

    refined = reasoner.refine_candidates("Transcript text here...", candidates)
    # Output identical to input deterministic scores
    assert len(refined) == 2
    assert refined[0].score == 85.0
    assert refined[1].score == 82.0


def test_llm_invalid_response_fallback():
    """Verify that malformed or non-schema LLM response falls back to deterministic scores without crashing."""
    reasoner = MomentReasoner(provider="groq", api_key="dummy_key")

    candidates = [
        CandidateMoment(start=10.0, end=35.0, score=85.0, reasons=["Base score"]),
    ]

    # Malformed non-JSON response
    refined_bad_json = reasoner.refine_candidates(
        "Transcript...",
        candidates,
        mock_response="Sorry, I cannot help with that.",
    )
    assert len(refined_bad_json) == 1
    assert refined_bad_json[0].score == 85.0

    # Malformed JSON without candidates schema
    refined_bad_schema = reasoner.refine_candidates(
        "Transcript...",
        candidates,
        mock_response='{"random_key": "not a list"}',
    )
    assert len(refined_bad_schema) == 1
    assert refined_bad_schema[0].score == 85.0


def test_llm_valid_score_refinement():
    """Verify valid structured LLM judgment refines score blending 70% deterministic + 30% LLM."""
    reasoner = MomentReasoner(provider="gemini", api_key="dummy_key")

    mom = CandidateMoment(start=10.0, end=35.0, score=80.0, reasons=["Base thought"])
    mock_llm_json = f"""{{
      "candidates": [
        {{
          "moment_id": "{mom.moment_id}",
          "hook_score": 0.95,
          "emotion_score": 0.90,
          "information_score": 0.92,
          "payoff_score": 0.95,
          "context_score": 0.90,
          "reason": "Outstanding conversational hook with high virality potential"
        }}
      ]
    }}"""

    refined = reasoner.refine_candidates("Transcript...", [mom], mock_response=mock_llm_json)
    assert len(refined) == 1
    # LLM average: (0.95 + 0.90 + 0.92 + 0.95 + 0.90) / 5 = 0.924 (92.4 points)
    # Blend: 0.70 * 80 + 0.30 * 92.4 = 56.0 + 27.72 = 83.72 -> 83.7
    assert refined[0].score == 83.7
    assert "Outstanding conversational hook" in refined[0].reasons[0]
    assert refined[0].signals.get("llm_reasoned") == 1.0
