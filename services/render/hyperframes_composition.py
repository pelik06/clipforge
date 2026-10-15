"""HyperFrames HTML Video Composition Generator.

Generates frame-perfect HTML/CSS/JS compositions compatible with HyperFrames CLI (0.8.x).
Supports 9:16 vertical video compositing, kinetic HTML/CSS word captions,
top hook headline card, and bottom animated progress bar.
"""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import shutil

from core.models.transcript import Word


@dataclass
class HyperframesConfig:
    title: str = "HIGHLIGHT MOMENT"
    caption_preset: str = "karaoke"
    caption_position: str = "bottom_safe"
    font_size: int = 68
    text_color: str = "#E9ECEE"
    highlight_color: str = "#00FF66"
    theme_bg: str = "#13151f"
    theme_surface: str = "#1a1e2b"
    theme_border: str = "#293245"


class HyperframesCompositionBuilder:
    """Builds ready-to-render HyperFrames project directory containing index.html,

    meta.json, and hyperframes.json.
    """

    def build_composition(
        self,
        output_dir: Path,
        source_video_path: Path,
        clip_duration: float,
        words: List[Word],
        config: Optional[HyperframesConfig] = None,
    ) -> Path:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        cfg = config or HyperframesConfig()

        # Copy or symlink video into composition folder as video.mp4
        local_video = output_dir / "video.mp4"
        if not local_video.exists():
            shutil.copyfile(source_video_path, local_video)

        # Build meta.json
        meta_json = {
            "id": output_dir.name,
            "name": cfg.title[:30],
            "createdAt": "2026-10-15T00:00:00.000Z",
        }
        (output_dir / "meta.json").write_text(json.dumps(meta_json, indent=2), encoding="utf-8")

        # Build hyperframes.json
        hf_json = {
            "$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
            "registry": "https://raw.githubusercontent.com/heygen-com/hyperframes/main/registry",
            "paths": {
                "blocks": "compositions",
                "components": "compositions/components",
                "assets": "assets",
            },
            "media": {"autoProxy": True},
        }
        (output_dir / "hyperframes.json").write_text(json.dumps(hf_json, indent=2), encoding="utf-8")

        # Group words into adaptive phrases (3-4 words per phrase)
        phrases = []
        if words:
            chunk_size = 4
            for i in range(0, len(words), chunk_size):
                chunk = words[i : i + chunk_size]
                p_start = max(0.0, chunk[0].start)
                p_end = min(clip_duration, chunk[-1].end + 0.15)
                if p_end > p_start:
                    phrases.append({
                        "start": p_start,
                        "duration": max(0.4, p_end - p_start),
                        "words": chunk,
                    })

        # Generate index.html
        html_content = self._generate_html(
            duration=clip_duration,
            phrases=phrases,
            cfg=cfg,
        )
        (output_dir / "index.html").write_text(html_content, encoding="utf-8")

        return output_dir

    def _generate_html(
        self,
        duration: float,
        phrases: List[Dict[str, Any]],
        cfg: HyperframesConfig,
    ) -> str:
        pos_styles = {
            "top_safe": "top: 260px;",
            "center": "top: 50%; transform: translateY(-50%);",
            "bottom_safe": "bottom: 240px;",
        }
        caption_box_pos = pos_styles.get(cfg.caption_position, pos_styles["bottom_safe"])

        # Colors by preset
        if cfg.caption_preset == "viral_beast":
            font_family = "'Anton', sans-serif"
            text_color = "#FFDE00"
            active_color = "#00FF66"
        elif cfg.caption_preset == "neon_cyan":
            font_family = "'Montserrat', sans-serif"
            text_color = "#00FFFF"
            active_color = "#FFFFFF"
        else:
            font_family = "'Anton', sans-serif"
            text_color = "#FFFFFF"
            active_color = "#FCD34D"
        # Build phrases HTML & GSAP timeline calls
        phrases_html = []
        gsap_calls = []

        for p_idx, p in enumerate(phrases):
            p_id = f"phrase-{p_idx}"
            word_spans = []
            for w_idx, w in enumerate(p["words"]):
                w_id = f"w-{p_idx}-{w_idx}"
                word_spans.append(f'<span id="{w_id}" class="word-span">{w.text}</span>')
                # Active word highlight animation in GSAP
                w_start_rel = max(0.0, w.start)
                w_dur = max(0.12, (w.end - w.start))
                gsap_calls.append(
                    f'tl.fromTo("#{w_id}", {{ color: "{text_color}", scale: 0.96 }}, {{ color: "{active_color}", scale: 1.12, duration: {w_dur:.2f}, textDecoration: "underline" }}, {w_start_rel:.2f});'
                )

            words_str = " ".join(word_spans)
            p_start = p["start"]
            p_dur = p["duration"]
            phrases_html.append(
                f'<div id="{p_id}" class="clip phrase-card" data-start="{p_start:.2f}" data-duration="{p_dur:.2f}" data-track-index="2">'
                f'<div class="phrase-text">{words_str}</div>'
                f"</div>"
            )

        all_phrases_html = "\n      ".join(phrases_html)
        gsap_script = "\n      ".join(gsap_calls)

        return f"""<!doctype html>
<html lang="en" data-resolution="portrait">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link href="https://fonts.googleapis.com/css2?family=Anton&family=Montserrat:wght@800;900&display=swap" rel="stylesheet" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{
        width: 1080px;
        height: 1920px;
        background: {cfg.theme_bg};
        overflow: hidden;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      }}
      #root {{
        position: relative;
        width: 1080px;
        height: 1920px;
      }}
      .bg-video {{
        position: absolute;
        inset: 0;
        width: 1080px;
        height: 1920px;
        object-fit: cover;
      }}
      .hook-banner {{
        position: absolute;
        top: 80px;
        left: 60px;
        right: 60px;
        padding: 24px 32px;
        background: rgba(26, 30, 43, 0.92);
        border: 2px solid {cfg.theme_border};
        border-radius: 20px;
        box-shadow: 0 16px 36px rgba(0,0,0,0.6);
        color: #e9ecee;
        display: flex;
        align-items: center;
        gap: 18px;
        z-index: 10;
      }}
      .hook-badge {{
        background: #fcd34d;
        color: #13151f;
        font-weight: 800;
        font-size: 24px;
        padding: 6px 16px;
        border-radius: 12px;
        letter-spacing: -0.01em;
      }}
      .hook-title {{
        font-size: 32px;
        font-weight: 700;
        color: #e9ecee;
        line-height: 1.2;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }}
      .caption-container {{
        position: absolute;
        left: 50px;
        right: 50px;
        {caption_box_pos}
        z-index: 20;
        display: flex;
        flex-direction: column;
        align-items: center;
      }}
      .phrase-card {{
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
        width: 100%;
      }}
      .phrase-text {{
        font-family: {font_family};
        font-size: {cfg.font_size}px;
        font-weight: 900;
        color: {text_color};
        text-shadow: 0 4px 16px rgba(0,0,0,0.95), 0 0 4px #000;
        letter-spacing: -0.01em;
        text-transform: uppercase;
        line-height: 1.2;
      }}
      .word-span {{
        display: inline-block;
        margin: 0 8px;
      }}
      .progress-bar-container {{
        position: absolute;
        bottom: 0;
        left: 0;
        width: 1080px;
        height: 12px;
        background: rgba(41, 50, 69, 0.7);
        z-index: 30;
      }}
      .progress-fill {{
        height: 100%;
        width: 0%;
        background: #00FF66;
        box-shadow: 0 0 12px rgba(0,255,102,0.8);
      }}
    </style>
  </head>
  <body>
    <div
      id="root"
      data-composition-id="main"
      data-start="0"
      data-duration="{duration:.2f}"
      data-width="1080"
      data-height="1920"
    >
      <video
        id="bg-video"
        class="clip bg-video"
        src="video.mp4"
        data-start="0"
        data-duration="{duration:.2f}"
        data-track-index="0"
        data-has-audio="true"
      ></video>

      <div id="hook" class="clip hook-banner" data-start="0" data-duration="{min(10.0, duration):.2f}" data-track-index="1">
        <span class="hook-badge">★ VIRAL</span>
        <span class="hook-title">{cfg.title}</span>
      </div>

      <div class="caption-container">
        {all_phrases_html}
      </div>

      <div class="progress-bar-container">
        <div id="progress" class="progress-fill"></div>
      </div>
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
      tl.to("#progress", {{ width: "100%", duration: {duration:.2f}, ease: "none" }}, 0);
      tl.fromTo("#hook", {{ y: -50, opacity: 0 }}, {{ y: 0, opacity: 1, duration: 0.6, ease: "power2.out" }}, 0);
      tl.to("#hook", {{ opacity: 0, y: -20, duration: 0.5 }}, {min(9.5, duration - 0.5):.2f});
      {gsap_script}
      window.__timelines["main"] = tl;
      tl.seek(0);
    </script>
  </body>
</html>
"""
