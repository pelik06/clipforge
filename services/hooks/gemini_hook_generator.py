"""Gemini AI Studio Hook & Social Post Generator for Indonesian viral clips."""

import json
import logging
import os
import re
import urllib.request
from typing import Any, Dict, List, Optional

from core.config.settings import Settings
from services.render.hyperframes_templates import extract_indonesian_viral_hook

logger = logging.getLogger(__name__)


class GeminiHookGenerator:
    """Generates viral Indonesian hooks and social post captions using Gemini 1.5 Flash

    with deterministic local keyword fallback.
    """

    def __init__(self, api_key: Optional[str] = None):
        if api_key is not None:
            self.api_key = api_key
        else:
            settings_key = getattr(Settings, "gemini_api_key", "")
            if isinstance(settings_key, str) and settings_key:
                self.api_key = settings_key
            else:
                self.api_key = os.getenv("GEMINI_API_KEY", "")

    @property
    def is_enabled(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def generate_hook_and_post(
        self,
        clip: Dict[str, Any],
        transcript_segments: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        """Generate structured hook parts, caption, and hashtags for a clip.

        Uses Gemini 1.5 Flash when enabled, falls back safely to local extraction.
        """
        # Determine fallback base first
        clean_title = str(clip.get("title", "VIRAL HIGHLIGHT MOMENT")).split("[")[0].strip()
        if ":" in clean_title:
            clean_title = clean_title.split(":", 1)[1].strip() or clean_title
        fallback_data = extract_indonesian_viral_hook(
            clip,
            clean_title=clean_title,
            transcript_segments=transcript_segments,
        )
        # Ensure fallback includes social_post_caption and hashtags
        if "social_post_caption" not in fallback_data:
            fallback_data["social_post_caption"] = (
                f"{fallback_data.get('highlight_text', '')} {fallback_data.get('sub_text', '')}! "
                f"Tonton sampai habis biar paham konteksnya."
            )
        if "hashtags" not in fallback_data or not fallback_data["hashtags"]:
            fallback_data["hashtags"] = ["#viral", "#fyp", "#shorts", "#trending", "#indonesia"]

        if not self.is_enabled:
            return fallback_data

        # Build prompt from clip dialogue
        c_start = float(clip.get("start_time", 0.0))
        dur_val = float(str(clip.get("duration", "60.0")).replace("s", ""))
        c_end = float(clip.get("end_time", c_start + dur_val))

        dialogue_lines: List[str] = []
        if transcript_segments:
            for s in transcript_segments:
                s_end = getattr(s, "end", 0.0)
                s_start = getattr(s, "start", 0.0)
                if s_end > c_start and s_start < c_end:
                    txt = getattr(s, "text", "").strip()
                    if txt:
                        dialogue_lines.append(txt)

        dialogue_text = " ".join(dialogue_lines) if dialogue_lines else clean_title

        prompt = f"""Kamu adalah editor video pendek viral (TikTok, Reels, YouTube Shorts) profesional berbahasa Indonesia.
Analisis percakapan dalam klip video berikut:
Judul Klip: {clean_title}
Transkrip Percakapan:
"{dialogue_text[:1200]}"

Buat hook 4-tier banner dan materi caption postingan media sosial dalam Bahasa Indonesia.
Kembalikan HANYA JSON murni dengan format persis:
{{
  "top_tag": "1-2 kata subjek/nama pembicara (contoh: TIMOTHY, PODCAST, VIRAL)",
  "badge_tag": "2-3 kata emosi/aksi (contoh: BOCORIN RAHASIA, NGAKU SENDIRI, DI RECALL RECALL)",
  "highlight_text": "2-4 kata inti hook huruf besar (contoh: CUAN 4 MILIAR, DEPAN MUKA)",
  "sub_text": "2-4 kata konteks lanjutan (contoh: DARI MEME COIN, SAMPE DIUSIR)",
  "punchline": "1-2 kata klimaks singkat (contoh: NEXT BULL RUN!, SECURITY!, PARAH BANGET!)",
  "social_post_caption": "Caption singkat menarik 1-2 kalimat untuk posting TikTok/Reels/Shorts dengan CTA tonton sampai habis",
  "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"]
}}
"""
        try:
            raw_response = self._call_gemini_api(prompt)
            if not raw_response:
                return fallback_data

            clean_json = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_response.strip())
            data = json.loads(clean_json)

            top_tag = str(data.get("top_tag") or fallback_data.get("top_tag", "VIRAL")).strip().upper()[:20]
            badge_tag = str(data.get("badge_tag") or fallback_data.get("badge_tag", "BOCORIN RAHASIA")).strip().upper()[:24]
            highlight_text = str(data.get("highlight_text") or fallback_data.get("highlight_text", "")).strip().upper()[:24]
            sub_text = str(data.get("sub_text") or fallback_data.get("sub_text", "")).strip().upper()[:28]
            punchline = str(data.get("punchline") or fallback_data.get("punchline", "PARAH BANGET!")).strip().upper()[:20]
            social_post_caption = str(data.get("social_post_caption") or fallback_data["social_post_caption"]).strip()

            raw_tags = data.get("hashtags")
            if isinstance(raw_tags, list) and len(raw_tags) >= 3:
                hashtags = [f"#{t.lstrip('#')}" for t in raw_tags if isinstance(t, str) and t.strip()]
            else:
                hashtags = fallback_data["hashtags"]

            return {
                "top_tag": top_tag or fallback_data.get("top_tag", "VIRAL"),
                "badge_tag": badge_tag or fallback_data.get("badge_tag", "BOCORIN RAHASIA"),
                "highlight_text": highlight_text or fallback_data.get("highlight_text", clean_title[:22]),
                "sub_text": sub_text or fallback_data.get("sub_text", "BONGKAR FAKTA NYATA"),
                "punchline": punchline or fallback_data.get("punchline", "PARAH BANGET!"),
                "social_post_caption": social_post_caption,
                "hashtags": hashtags,
                "intro_blur_grayscale": True,
                "intro_duration": 2.2,
            }
        except Exception as e:
            logger.warning(f"Gemini API call failed, falling back to local heuristic: {e}")
            return fallback_data

    def _call_gemini_api(self, prompt: str) -> Optional[str]:
        """Make HTTP request to Gemini 1.5 Flash generateContent API."""
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        }
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=req_data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "ClipForge/1.0",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["candidates"][0]["content"]["parts"][0]["text"]
