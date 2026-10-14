import json
import os
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from core.models.candidate import CandidateMoment
from core.models.transcript import TranscriptSegment


@dataclass
class MomentSelectionResult:
    candidates: List[CandidateMoment]
    mode: str  # "ai_semantic" | "heuristic_fallback"
    provider: str
    notice: Optional[str] = None


class MomentSelector:
    """Select 3-15 high-potential viral short moments from full transcript, words, and scenes.
    
    Inspired by OpenShorts viral moment selection.
    Supports Gemini, OpenAI-compatible, Local LLM, and automatic Heuristic fallback.
    """

    def __init__(
        self,
        mode: str = "heuristic",  # "ai" | "heuristic"
        provider: str = "gemini",  # "gemini" | "openai" | "local" | "heuristic"
    ):
        self.mode = mode
        self.provider = provider

    def _call_gemini(self, prompt: str) -> Optional[str]:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return None
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
                return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            return None

    def _call_openai_compatible(self, prompt: str, base_url: Optional[str] = None, api_key: Optional[str] = None) -> Optional[str]:
        key = api_key or os.getenv("OPENAI_API_KEY") or "dummy"
        url = (base_url or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1") + "/chat/completions"
        payload = {
            "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "messages": [
                {"role": "system", "content": "You are a viral YouTube Shorts/TikTok video editor. Output only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
                return data["choices"][0]["message"]["content"]
        except Exception:
            return None

    def _heuristic_selection(
        self,
        video_duration: float,
        transcript_segments: List[TranscriptSegment],
        scenes: List[Dict[str, float]],
        min_duration: float,
        max_duration: float,
        max_clips: int,
        media_path: Optional[str] = None,
        youtube_heatmap: Optional[List[Dict[str, Any]]] = None,
    ) -> List[CandidateMoment]:
        """Multi-signal heuristic selection integrating audio energy, motion, face, and speech."""
        eff_min_dur = min(min_duration, max(4.0, video_duration / 4.0)) if video_duration < 45.0 else min_duration
        if media_path and Path(media_path).exists():
            try:
                from services.detection.moment_pipeline import NonLLMMomentDetector
                detector = NonLLMMomentDetector(moment_threshold=0.45)
                moments = detector.detect_moments(
                    media_path=media_path,
                    transcript_segments=transcript_segments,
                    min_clip_duration=eff_min_dur,
                    max_clip_duration=max_duration,
                    max_clips=max_clips,
                )
                if moments and len(moments) >= 2:
                    return moments
            except Exception:
                pass
        """Acoustic + sentence boundary heuristic fallback when LLM is unavailable."""
        candidates: List[CandidateMoment] = []

        if transcript_segments and len(transcript_segments) > 0:
            try:
                from services.detection.thought_detector import ThoughtDetector, extract_sentences
                td = ThoughtDetector(
                    min_clip_duration=eff_min_dur,
                    max_clip_duration=max_duration,
                    max_overlap_ratio=0.35,
                    max_containment_ratio=0.50,
                )
                sentences = extract_sentences(transcript_segments)
                if sentences:
                    tw_list = td.identify_thought_windows(
                        sentences,
                        total_duration=video_duration,
                        scenes=scenes,
                    )
                    td_candidates: List[CandidateMoment] = []
                    for tw in tw_list:
                        dur = tw.duration
                        if dur < eff_min_dur or dur > max_duration:
                            continue
                        score = td.score_thought_window(
                            tw,
                            scenes=scenes,
                            total_duration=video_duration,
                            youtube_heatmap=youtube_heatmap,
                        )
                        reasons = []
                        if tw.has_hook:
                            reasons.append("Strong opening conversational hook")
                        if tw.has_payoff:
                            reasons.append("Complete resolution & payoff")
                        reasons.append(f"Complete conversational thought ({dur:.1f}s)")
                        td_candidates.append(
                            CandidateMoment(
                                start=round(tw.start, 2),
                                end=round(tw.end, 2),
                                score=round(score, 1),
                                reasons=reasons,
                                signals={"duration": dur},
                            )
                        )
                    if td_candidates:
                        valid_td = td.deduplicate_thoughts(td_candidates, max_clips=max_clips)
                        if valid_td:
                            return valid_td
            except Exception:
                pass

            # Secondary Fallback: Dynamic lookahead loop up to max_duration
            n = len(transcript_segments)
            for i in range(n):
                t_start = max(0.0, transcript_segments[i].start - 0.25)
                for j in range(i, n):
                    t_end = min(video_duration, transcript_segments[j].end + 0.35)
                    dur = t_end - t_start
                    if dur > max_duration:
                        break
                    if dur < eff_min_dur:
                        continue
                    scene_aligned = any(abs(t_start - s["start"]) < 1.0 or abs(t_end - s["end"]) < 1.0 for s in scenes)
                    score = 72.0 + (10.0 if scene_aligned else 0.0) + max(0.0, 15.0 - abs(dur - 35.0) / 2.0)
                    reasons = [
                        "Complete sentence thought",
                        f"Target duration ({dur:.1f}s)",
                    ]
                    if scene_aligned:
                        reasons.append("Aligned with visual scene boundary")
                    candidates.append(
                        CandidateMoment(
                            start=round(t_start, 2),
                            end=round(t_end, 2),
                            score=round(min(96.0, score), 1),
                            reasons=reasons,
                            signals={"duration": dur, "scene_aligned": 1.0 if scene_aligned else 0.0},
                        )
                    )
        # Fallback to scene cuts if transcript is empty
        if not candidates and scenes:
            for sc in scenes:
                dur = sc["duration"]
                if dur >= min_duration:
                    candidates.append(
                        CandidateMoment(
                            start=sc["start"],
                            end=sc["end"],
                            score=75.0,
                            reasons=["Natural scene transition window"],
                            signals={"duration": dur},
                        )
                    )

        # If no genuine acoustic/speech candidates found, return empty list (NO_VALID_MOMENTS)
        if not candidates:
            return []

        return candidates

    def select_moments(
        self,
        video_duration: float,
        transcript_segments: List[TranscriptSegment],
        words_json: List[Dict[str, Any]],
        scenes: List[Dict[str, float]],
        min_duration: float = 12.0,
        max_duration: float = 55.0,
        max_clips: int = 5,
        media_path: Optional[str] = None,
        youtube_heatmap: Optional[List[Dict[str, Any]]] = None,
    ) -> MomentSelectionResult:
        ai_raw_json = None
        active_mode = "heuristic_fallback"
        notice = None

        if self.mode == "ai":
            # Build OpenShorts-style prompt
            transcript_text = "\n".join([f"[{s.start:.2f} - {s.end:.2f}] {s.text}" for s in transcript_segments[:60]])
            prompt = f"""You are an elite video editor and viral short-form content curator.
Analyze the following timestamped video transcript and scene boundaries to find {max_clips} independent, high-potential viral moments.

Video Duration: {video_duration:.1f}s
Minimum Clip Duration: {min_duration}s
Maximum Clip Duration: {max_duration}s

Scene Boundaries (visual cuts):
{json.dumps(scenes[:20])}

Transcript:
{transcript_text}

Rules:
1. Each moment MUST be a complete thought with a hook, context, and clear payoff.
2. DO NOT cut in the middle of a sentence or thought.
3. Avoid generic video intros, welcomes, sponsor reads, or outros.
4. Each clip MUST have duration between {min_duration} and {max_duration} seconds.
5. Return exactly valid JSON in this schema:
{{
  "shorts": [
    {{
      "start": 12.4,
      "end": 28.9,
      "reason": "Clear emotional hook with complete payoff",
      "score": 92.5
    }}
  ]
}}
"""
            if self.provider == "gemini":
                ai_raw_json = self._call_gemini(prompt)
            elif self.provider in ("openai", "local"):
                ai_raw_json = self._call_openai_compatible(
                    prompt,
                    base_url="http://localhost:11434/v1" if self.provider == "local" else None,
                )

        parsed_candidates: List[CandidateMoment] = []
        if ai_raw_json:
            try:
                # Strip markdown codeblocks if model returned ```json ... ```
                clean_json = re.sub(r"^```(?:json)?\s*|\s*```$", "", ai_raw_json.strip())
                data = json.loads(clean_json)
                shorts_list = data.get("shorts", [])
                for item in shorts_list:
                    s_start = float(item["start"])
                    s_end = float(item["end"])
                    s_dur = s_end - s_start
                    if min_duration <= s_dur <= (max_duration + 5.0) and s_start < video_duration:
                        parsed_candidates.append(
                            CandidateMoment(
                                start=round(max(0.0, s_start), 2),
                                end=round(min(video_duration, s_end), 2),
                                score=float(item.get("score") or 88.0),
                                reasons=[str(item.get("reason", "AI selected high-potential viral moment"))],
                                signals={"ai_semantic": 1.0, "duration": s_dur},
                            )
                        )
                if parsed_candidates:
                    active_mode = "ai_semantic"
                    notice = f"AI Semantic Analysis ({self.provider}) selected {len(parsed_candidates)} moments."
            except Exception:
                pass

        # Fallback to heuristic if AI was not requested or failed
        if not parsed_candidates:
            parsed_candidates = self._heuristic_selection(
                video_duration=video_duration,
                transcript_segments=transcript_segments,
                scenes=scenes,
                min_duration=min_duration,
                max_duration=max_duration,
                max_clips=max_clips,
                media_path=media_path,
                youtube_heatmap=youtube_heatmap,
            )
            active_mode = "heuristic_fallback"
            notice = "AI semantic provider unavailable or unconfigured. Using acoustic + sentence boundary heuristic fallback."

        # Temporal Non-Maximum Suppression (NMS) to eliminate duplicate overlapping clips
        parsed_candidates.sort(key=lambda c: c.score, reverse=True)
        filtered: List[CandidateMoment] = []
        for cand in parsed_candidates:
            is_overlap = False
            for prev in filtered:
                overlap_start = max(cand.start, prev.start)
                overlap_end = min(cand.end, prev.end)
                if overlap_end > overlap_start:
                    overlap_dur = overlap_end - overlap_start
                    min_dur = min(cand.duration, prev.duration)
                    if (overlap_dur / min_dur) > 0.35:
                        is_overlap = True
                        break
            if not is_overlap:
                filtered.append(cand)
                if len(filtered) >= max_clips:
                    break

        return MomentSelectionResult(
            candidates=filtered,
            mode=active_mode,
            provider=self.provider if active_mode == "ai_semantic" else "heuristic",
            notice=notice,
        )
