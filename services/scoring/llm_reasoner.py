import json
import os
import re
import urllib.request
from typing import Any, Dict, List, Optional

from core.models.candidate import CandidateMoment


class MomentReasoner:
    """Optional LLM Reasoner refining candidate virality, hooks, and context completeness with deterministic fallback."""

    def __init__(self, provider: str = "none", api_key: Optional[str] = None):
        self.provider = provider.lower() if provider else "none"
        self.api_key = api_key or (
            os.getenv("GEMINI_API_KEY") if self.provider == "gemini" else
            os.getenv("GROQ_API_KEY") if self.provider == "groq" else None
        )

    @property
    def is_enabled(self) -> bool:
        return self.provider in ("gemini", "groq") and bool(self.api_key)

    def refine_candidates(
        self,
        transcript_text: str,
        candidates: List[CandidateMoment],
        mock_response: Optional[str] = None,
    ) -> List[CandidateMoment]:
        """Refine candidate virality scores using structured LLM judgment or return deterministic scores."""
        if not candidates:
            return []

        # Deterministic fallback when LLM is not configured or disabled
        if not self.is_enabled and mock_response is None:
            return candidates

        prompt = f"""You are an elite short-form video editor. Score these candidate moments based on viral hook, emotional intensity, information density, payoff quality, and context completeness.

Transcript excerpt:
{transcript_text[:1500]}

Candidates to score:
{json.dumps([{"moment_id": c.moment_id, "start": c.start, "end": c.end, "duration": c.duration} for c in candidates])}

Return STRICT JSON matching this schema:
{{
  "candidates": [
    {{
      "moment_id": "mom_...",
      "hook_score": 0.90,
      "emotion_score": 0.85,
      "information_score": 0.80,
      "payoff_score": 0.88,
      "context_score": 0.85,
      "reason": "Clear narrative arc with immediate hook"
    }}
  ]
}}
"""
        raw_response = mock_response
        if raw_response is None:
            try:
                if self.provider == "groq":
                    raw_response = self._call_groq(prompt)
                elif self.provider == "gemini":
                    raw_response = self._call_gemini(prompt)
            except Exception:
                # Deterministic fallback on network / provider failure
                return candidates

        if not raw_response:
            return candidates

        # Parse and validate structured output
        try:
            clean_json = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_response.strip())
            data = json.loads(clean_json)
            cand_evals = data.get("candidates", [])
            if not isinstance(cand_evals, list):
                return candidates

            eval_by_id = {item["moment_id"]: item for item in cand_evals if "moment_id" in item}

            refined: List[CandidateMoment] = []
            for c in candidates:
                if c.moment_id in eval_by_id:
                    ev = eval_by_id[c.moment_id]
                    h = float(ev.get("hook_score", 0.8))
                    e = float(ev.get("emotion_score", 0.8))
                    info = float(ev.get("information_score", 0.8))
                    p = float(ev.get("payoff_score", 0.8))
                    ctx = float(ev.get("context_score", 0.8))

                    # Blend 70% deterministic score + 30% LLM judgment
                    llm_avg = (h + e + info + p + ctx) / 5.0
                    refined_score = round(0.70 * c.score + 0.30 * (llm_avg * 100.0), 1)

                    reason = str(ev.get("reason") or "LLM evaluated high-potential moment")
                    reasons = list(c.reasons)
                    if reason not in reasons:
                        reasons.insert(0, reason)

                    c.score = refined_score
                    c.reasons = reasons
                    c.signals["llm_reasoned"] = 1.0
                refined.append(c)

            return refined
        except Exception:
            # Deterministic fallback on malformed JSON
            return candidates

    def _call_groq(self, prompt: str) -> Optional[str]:
        req_data = json.dumps({
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=req_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "ClipForge/1.0",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]

    def _call_gemini(self, prompt: str) -> Optional[str]:
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
        req_data = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        }).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=req_data,
            headers={"Content-Type": "application/json", "User-Agent": "ClipForge/1.0"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["candidates"][0]["content"]["parts"][0]["text"]
