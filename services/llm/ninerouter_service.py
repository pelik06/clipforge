import json
import logging
import re
from typing import Any, Dict, List, Optional
import urllib.error
import urllib.request

from core.config.settings import Settings
from services.render.hyperframes_templates import extract_indonesian_viral_hook

logger = logging.getLogger(__name__)


class NineRouterService:
    """9Router LLM service for viral short-form hooks and captions."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 12.0,
    ) -> None:
        settings = Settings()
        self.api_key: str = (api_key if api_key is not None else settings.ninerouter_api_key).strip()
        self.base_url: str = (base_url if base_url is not None else settings.ninerouter_base_url).rstrip("/")
        self.model: str = (model if model is not None else settings.ninerouter_model).strip()
        self.timeout: float = timeout

    @property
    def is_enabled(self) -> bool:
        return bool(self.api_key)

    def filter_clip_segments(
        self,
        transcript_segments: Optional[List[Any]],
        clip_start: float,
        clip_end: float,
    ) -> List[Any]:
        """Filters segments that overlap [clip_start, clip_end]: s.end > clip_start and s.start < clip_end."""
        if not transcript_segments:
            return []

        matched = []
        for s in transcript_segments:
            s_start = getattr(s, "start", None)
            s_end = getattr(s, "end", None)

            if s_start is None and isinstance(s, dict):
                s_start = s.get("start")
                s_end = s.get("end")

            try:
                s_start_f = float(s_start) if s_start is not None else 0.0
                s_end_f = float(s_end) if s_end is not None else s_start_f
            except (ValueError, TypeError):
                continue

            # Overlap check
            if s_end_f > clip_start and s_start_f < clip_end:
                matched.append(s)

        return matched

    def _extract_dialogue_text(self, segments: List[Any]) -> str:
        texts = []
        for s in segments:
            txt = getattr(s, "text", None)
            if txt is None and isinstance(s, dict):
                txt = s.get("text", "")
            if txt:
                clean = re.sub(r"[\r\n\t]+", " ", str(txt)).strip()
                if clean:
                    texts.append(clean)
        return " ".join(texts)

    def _build_fallback_result(
        self,
        clip_dict: Dict[str, Any],
        transcript_segments: Optional[List[Any]],
    ) -> Dict[str, Any]:
        """Local dialogue keyword fallback with is_fallback=True."""
        clean_title = str(clip_dict.get("title", "") or clip_dict.get("vod", "HIGHLIGHT"))
        local_hook = extract_indonesian_viral_hook(clip_dict, clean_title, transcript_segments)

        top_tag = str(local_hook.get("top_tag", "VIRAL")).upper()
        badge_tag = str(local_hook.get("badge_tag", "BOCORIN RAHASIA")).upper()
        highlight_text = str(local_hook.get("highlight_text", "CUAN 4 MILIAR")).upper()
        sub_text = str(local_hook.get("sub_text", "DARI MEME COIN")).upper()
        punchline = str(local_hook.get("punchline", "PARAH BANGET!")).upper()

        caption = f"{badge_tag}! {highlight_text} {sub_text} - {punchline}. Nonton full clip sampai selesai!"
        hashtags = ["#fyp", "#viral", "#trending", f"#{top_tag.lower()}", "#clipforge"]

        return {
            "top_tag": top_tag,
            "badge_tag": badge_tag,
            "highlight_text": highlight_text,
            "sub_text": sub_text,
            "punchline": punchline,
            "social_post_caption": caption,
            "hashtags": hashtags,
            "is_fallback": True,
        }

    def generate_clip_hook(
        self,
        clip_dict: Dict[str, Any],
        transcript_segments: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        """Generates viral Indonesian hook lines and social caption via 9Router LLM or deterministic fallback."""
        c_start = float(clip_dict.get("start_time", 0.0))
        dur_raw = clip_dict.get("duration", 60.0)
        dur = float(str(dur_raw).replace("s", "")) if dur_raw else 60.0
        c_end = float(clip_dict.get("end_time", c_start + dur))

        clip_segs = self.filter_clip_segments(transcript_segments, c_start, c_end)
        dialogue = self._extract_dialogue_text(clip_segs)

        if not self.is_enabled:
            return self._build_fallback_result(clip_dict, clip_segs)

        title = str(clip_dict.get("title", "Highlight Moment"))
        speaker = str(clip_dict.get("uploader", "Streamer"))

        system_prompt = (
            "You are a viral short-form video editor for TikTok, Instagram Reels, and YouTube Shorts. "
            "Given the exact transcript dialogue between clip start and clip end, write an Indonesian viral hook and social post caption. "
            "You MUST respond with a JSON object containing EXACTLY these keys:\n"
            "- top_tag: str (1-2 words, speaker name or punchy topic tag, e.g. 'TIMOTHY', 'RAHASIA')\n"
            "- badge_tag: str (2-3 words, high curiosity badge, e.g. 'BOCORIN RAHASIA', 'DI RECALL RECALL')\n"
            "- highlight_text: str (2-4 words, core shocking claim/highlight, e.g. 'CUAN 4 MILIAR', 'DEPAN MUKA')\n"
            "- sub_text: str (2-4 words, supporting context, e.g. 'DARI MEME COIN', 'SAMPE DIUSIR')\n"
            "- punchline: str (1-2 words, final high-energy punchline, e.g. 'PARAH BANGET!', 'NEXT BULL RUN!')\n"
            "- social_post_caption: str (1-2 compelling sentences for TikTok/Reels caption with CTA)\n"
            "- hashtags: list of strings (4-6 trending viral hashtags starting with #)"
        )

        user_content = (
            f"Speaker / Creator: {speaker}\n"
            f"Clip Title: {title}\n"
            f"Clip Window: {c_start:.1f}s - {c_end:.1f}s (Duration: {dur:.1f}s)\n"
            f"Spoken Dialogue:\n\"\"\"{dialogue if dialogue else title}\"\"\"\n\n"
            "Generate the viral Indonesian hook JSON now."
        )

        endpoint = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.7,
            "response_format": {"type": "json_object"},
        }

        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                endpoint,
                data=req_data,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "ClipForge/1.0",
                },
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                status_code = response.getcode()
                raw_body = response.read().decode("utf-8")

            if status_code != 200:
                logger.warning("9Router returned HTTP %s, fallback to local hook", status_code)
                return self._build_fallback_result(clip_dict, clip_segs)

            res_obj = json.loads(raw_body)
            choices = res_obj.get("choices", [])
            if not choices:
                logger.warning("9Router response had no choices, fallback to local hook")
                return self._build_fallback_result(clip_dict, clip_segs)

            content_text = choices[0].get("message", {}).get("content", "")
            data = json.loads(content_text)

            # Validate required fields
            required_keys = ["top_tag", "badge_tag", "highlight_text", "sub_text", "punchline", "social_post_caption", "hashtags"]
            for k in required_keys:
                if k not in data:
                    raise ValueError(f"Missing required key in LLM hook response: {k}")

            top_tag = str(data["top_tag"]).strip().upper()[:15]
            badge_tag = str(data["badge_tag"]).strip().upper()[:25]
            highlight_text = str(data["highlight_text"]).strip().upper()[:30]
            sub_text = str(data["sub_text"]).strip().upper()[:30]
            punchline = str(data["punchline"]).strip().upper()[:20]
            caption = str(data["social_post_caption"]).strip()
            raw_tags = data["hashtags"]
            if isinstance(raw_tags, list):
                hashtags = [f"#{t.lstrip('#')}" for t in raw_tags if str(t).strip()]
            else:
                hashtags = ["#fyp", "#viral", "#clipforge"]

            return {
                "top_tag": top_tag,
                "badge_tag": badge_tag,
                "highlight_text": highlight_text,
                "sub_text": sub_text,
                "punchline": punchline,
                "social_post_caption": caption,
                "hashtags": hashtags,
                "is_fallback": False,
            }

        except Exception as exc:
            # Never crash pipeline; log warning without sensitive auth header
            logger.warning("9Router hook generation error (%s): %s", type(exc).__name__, exc)
            return self._build_fallback_result(clip_dict, clip_segs)
