"""HyperFrames HTML Video Composition Generator.

Compiles layer-based HyperframesComposition models into frame-perfect HTML/CSS/GSAP
projects ready for deterministic rendering via HyperFrames CLI.
"""

from dataclasses import dataclass
import json
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional

from core.models.transcript import Word
from services.render.hyperframes_models import (
    AnimationType,
    CompositionLayer,
    HyperframesComposition,
    LayerType,
    TemplateType,
)


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
    """Compiles HyperframesComposition data models into executable HyperFrames projects."""

    def build_from_composition(
        self,
        output_dir: Path,
        source_video_path: Path,
        composition: HyperframesComposition,
    ) -> Path:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 1. Copy source video to local video.mp4
        local_video = output_dir / "video.mp4"
        if not local_video.exists():
            shutil.copyfile(source_video_path, local_video)

        # 2. Build meta.json
        meta_json = {
            "id": composition.composition_id,
            "name": composition.metadata.get("title", composition.clip_id)[:40],
            "createdAt": "2026-10-15T00:00:00.000Z",
        }
        (output_dir / "meta.json").write_text(json.dumps(meta_json, indent=2), encoding="utf-8")

        # 3. Build hyperframes.json
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

        # 4. Generate index.html from layers and captions
        html_content = self._compile_composition_to_html(composition)
        (output_dir / "index.html").write_text(html_content, encoding="utf-8")

        return output_dir

    def build_composition(
        self,
        output_dir: Path,
        source_video_path: Path,
        clip_duration: float,
        words: List[Word],
        config: Optional[HyperframesConfig] = None,
    ) -> Path:
        """Legacy / convenient adapter creating a default composition and delegating to build_from_composition."""
        from services.render.hyperframes_templates import generate_initial_composition

        cfg = config or HyperframesConfig()
        clip_dict = {
            "id": output_dir.name,
            "title": cfg.title,
            "duration": f"{clip_duration:.1f}s",
            "start_time": 0.0,
            "end_time": clip_duration,
            "caption_preset": cfg.caption_preset,
            "caption_position": cfg.caption_position,
        }
        # Fake transcript segment with provided words
        from core.models.transcript import TranscriptSegment
        dummy_seg = [TranscriptSegment(text=" ".join([w.text for w in words]), start=0.0, end=clip_duration, words=words)] if words else []

        composition = generate_initial_composition(clip_dict, transcript_segments=dummy_seg)
        # Apply config overrides
        for l in composition.layers:
            if l.type == LayerType.HOOK:
                l.data["title"] = cfg.title
            if l.type == LayerType.CAPTION:
                l.data["font_size"] = cfg.font_size
                l.data["position"] = cfg.caption_position

        return self.build_from_composition(output_dir, source_video_path, composition)

    def _compile_composition_to_html(self, composition: HyperframesComposition) -> str:
        duration = max(0.1, composition.duration)
        w_canvas = composition.width or 1080
        h_canvas = composition.height or 1920

        # Extract specific layers
        hook_layers = [l for l in composition.layers if l.type == LayerType.HOOK and l.visible]
        person_layers = [l for l in composition.layers if l.type == LayerType.PERSON and l.visible]
        caption_layers = [l for l in composition.layers if l.type == LayerType.CAPTION and l.visible]
        progress_layers = [l for l in composition.layers if l.type == LayerType.PROGRESS_BAR and l.visible]
        text_layers = [l for l in composition.layers if l.type == LayerType.TEXT and l.visible]

        # Font styles & Caption styling
        caption_cfg = caption_layers[0].data if caption_layers else {}
        font_family = caption_cfg.get("font_family", "Anton")
        if font_family not in ("Anton", "Montserrat", "Inter", "Roboto"):
            font_family = "Anton"
        font_size = caption_cfg.get("font_size", 72)
        text_color = caption_cfg.get("text_color", "#FFFFFF")
        active_color = caption_cfg.get("active_color", "#00FF66")
        caption_pos = caption_cfg.get("position", "bottom_safe")

        pos_styles = {
            "top_safe": "top: 260px;",
            "center": "top: 50%; transform: translateY(-50%);",
            "bottom_safe": "bottom: 240px;",
        }
        caption_box_pos = pos_styles.get(caption_pos, pos_styles["bottom_safe"])

        # Check if viral stacked Indonesian hook is used
        has_intro_blur = False
        intro_dur = 2.2
        for h_l in hook_layers:
            h_d = h_l.data or {}
            if h_d.get("top_tag") or h_d.get("highlight_text") or h_d.get("punchline") or h_d.get("intro_blur_grayscale"):
                has_intro_blur = True
                intro_dur = float(h_d.get("intro_duration", 2.2))
                break

        # Group words into 3-4 word phrases
        phrases = []
        raw_captions = composition.captions or []
        if raw_captions:
            chunk_size = 4
            for i in range(0, len(raw_captions), chunk_size):
                chunk = raw_captions[i : i + chunk_size]
                p_start = max(0.0, float(chunk[0].get("start", 0.0)))
                p_end = min(duration, float(chunk[-1].get("end", 0.0)) + 0.15)
                if has_intro_blur and p_start < intro_dur:
                    if p_end <= intro_dur:
                        continue
                    p_start = intro_dur
                if p_end > p_start:
                    phrases.append({
                        "start": p_start,
                        "duration": max(0.4, p_end - p_start),
                        "words": chunk,
                    })
        phrases_html = []
        gsap_calls = []

        # Progress bar animation
        if progress_layers:
            gsap_calls.append(f'tl.to("#progress", {{ width: "100%", duration: {duration:.2f}, ease: "none" }}, 0);')

        # Hook layers rendering and animation
        hook_html_parts = []
        has_intro_blur = False
        intro_dur = 2.2

        for h_layer in hook_layers:
            h_data = h_layer.data or {}
            top_tag = h_data.get("top_tag")
            badge_tag = h_data.get("badge_tag")
            highlight_text = h_data.get("highlight_text")
            sub_text = h_data.get("sub_text")
            punchline = h_data.get("punchline")
            is_viral_stacked = bool(top_tag or highlight_text or punchline)

            if is_viral_stacked:
                has_intro_blur = bool(h_data.get("intro_blur_grayscale", True))
                intro_dur = float(h_data.get("intro_duration", 2.2))
                top_tag_str = str(top_tag or "VIRAL").upper()
                badge_tag_str = str(badge_tag or "BOCORIN RAHASIA").upper()
                highlight_str = str(highlight_text or "CUAN 4 MILIAR").upper()
                sub_str = str(sub_text or "MODAL KECIL").upper()
                punchline_str = str(punchline or "NEXT BULL RUN!").upper()

                hook_html_parts.append(f"""
      <div id="{h_layer.id}" class="clip viral-hook-container" data-start="{h_layer.start:.2f}" data-duration="{intro_dur:.2f}" data-track-index="{h_layer.z_index}">
        <div class="hook-row-1">
          <div class="hook-brush-black"><span>{top_tag_str}</span></div>
          <div class="hook-badge-red"><span>{badge_tag_str}</span></div>
        </div>
        <div class="hook-row-2">
          <div class="hook-brush-yellow"><span>{highlight_str}</span></div>
        </div>
        <div class="hook-row-3">
          <div class="hook-brush-white"><span>{sub_str}</span></div>
        </div>
        <div class="hook-row-4">
          <div class="hook-neon-green"><span>{punchline_str}</span></div>
        </div>
      </div>""")

                gsap_calls.append(f'tl.fromTo("#{h_layer.id}", {{ scale: 0.65, opacity: 0, y: 50 }}, {{ scale: 1.0, opacity: 1, y: 0, duration: 0.55, ease: "back.out(2.0)" }}, {h_layer.start:.2f});')
                exit_t = max(0.4, intro_dur - 0.4)
                gsap_calls.append(f'tl.to("#{h_layer.id}", {{ scale: 0.85, opacity: 0, y: -40, duration: 0.4, ease: "power2.in" }}, {exit_t:.2f});')
            else:
                h_title = h_data.get("title", "VIRAL MOMENT")
                h_badge = h_data.get("badge", "★ HIGHLIGHT")
                h_bg = h_data.get("bg_color", "rgba(26, 30, 43, 0.94)")
                h_border = h_data.get("border_color", "#293245")
                h_text = h_data.get("text_color", "#E9ECEE")

                h_anim = h_layer.animation_in.get("type", "spring")
                h_dur = h_layer.duration

                hook_html_parts.append(f"""
      <div id="{h_layer.id}" class="clip hook-banner" data-start="{h_layer.start:.2f}" data-duration="{h_dur:.2f}" data-track-index="{h_layer.z_index}"
           style="background: {h_bg}; border-color: {h_border}; opacity: {h_layer.opacity}; transform: scale({h_layer.scale});">
        <span class="hook-badge">{h_badge}</span>
        <span class="hook-title" style="color: {h_text};">{h_title}</span>
      </div>""")

                if h_anim == "spring":
                    gsap_calls.append(f'tl.fromTo("#{h_layer.id}", {{ y: -60, opacity: 0 }}, {{ y: 0, opacity: 1, duration: 0.6, ease: "back.out(1.7)" }}, {h_layer.start:.2f});')
                elif h_anim == "pop":
                    gsap_calls.append(f'tl.fromTo("#{h_layer.id}", {{ scale: 0.7, opacity: 0 }}, {{ scale: 1, opacity: 1, duration: 0.4, ease: "power2.out" }}, {h_layer.start:.2f});')
                else:
                    gsap_calls.append(f'tl.fromTo("#{h_layer.id}", {{ opacity: 0, y: -30 }}, {{ opacity: 1, y: 0, duration: 0.5 }}, {h_layer.start:.2f});')

                gsap_calls.append(f'tl.to("#{h_layer.id}", {{ opacity: 0, y: -20, duration: 0.4 }}, {max(0.0, h_layer.end - 0.4):.2f});')

        if has_intro_blur:
            gsap_calls.append(f'tl.to(".bg-video", {{ filter: "blur(0px) grayscale(0%) contrast(100%) brightness(1.0)", duration: 0.6, ease: "power2.out" }}, {max(0.2, intro_dur - 0.4):.2f});')
        # Person layers rendering and animation
        person_html_parts = []
        for p_layer in person_layers:
            p_data = p_layer.data or {}
            p_label = p_data.get("person_label", "Speaker")
            p_badge = p_data.get("badge", "SPEAKER")
            p_x = p_layer.x
            p_y = p_layer.y
            p_scale = p_layer.scale
            p_anim = p_layer.animation_in.get("type", "fade")

            person_html_parts.append(f"""
      <div id="{p_layer.id}" class="clip person-card" data-start="{p_layer.start:.2f}" data-duration="{p_layer.duration:.2f}" data-track-index="{p_layer.z_index}"
           style="left: {p_x:.1f}px; top: {p_y:.1f}px; opacity: {p_layer.opacity}; transform: translate(-50%, -50%) scale({p_scale});">
        <span class="person-tag">{p_badge}: {p_label}</span>
      </div>""")

            if p_anim == "slide_left":
                gsap_calls.append(f'tl.fromTo("#{p_layer.id}", {{ x: "-=100", opacity: 0 }}, {{ x: "+=0", opacity: 1, duration: 0.5 }}, {p_layer.start:.2f});')
            elif p_anim == "slide_right":
                gsap_calls.append(f'tl.fromTo("#{p_layer.id}", {{ x: "+=100", opacity: 0 }}, {{ x: "+=0", opacity: 1, duration: 0.5 }}, {p_layer.start:.2f});')
            elif p_anim == "pop":
                gsap_calls.append(f'tl.fromTo("#{p_layer.id}", {{ scale: 0.5, opacity: 0 }}, {{ scale: {p_scale}, opacity: 1, duration: 0.4 }}, {p_layer.start:.2f});')
            else:
                gsap_calls.append(f'tl.fromTo("#{p_layer.id}", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.3 }}, {p_layer.start:.2f});')

        # Captions rendering
        for p_idx, p in enumerate(phrases):
            p_id = f"phrase-{p_idx}"
            word_spans = []
            for w_idx, w in enumerate(p["words"]):
                w_id = f"w-{p_idx}-{w_idx}"
                w_text = w.get("text", "")
                word_spans.append(f'<span id="{w_id}" class="word-span">{w_text}</span>')

                # Word active animation
                w_start_rel = max(0.0, float(w.get("start", 0.0)))
                w_end_rel = max(w_start_rel + 0.12, float(w.get("end", w_start_rel + 0.25)))
                w_dur = max(0.12, w_end_rel - w_start_rel)
                gsap_calls.append(
                    f'tl.fromTo("#{w_id}", {{ color: "{text_color}", scale: 0.96 }}, {{ color: "{active_color}", scale: 1.12, duration: {w_dur:.2f}, textDecoration: "underline" }}, {w_start_rel:.2f});'
                )

            words_str = " ".join(word_spans)
            p_start = p["start"]
            p_dur = p["duration"]
            phrases_html.append(
                f'<div id="{p_id}" class="clip phrase-card" data-start="{p_start:.2f}" data-duration="{p_dur:.2f}" data-track-index="8">'
                f'<div class="phrase-text">{words_str}</div>'
                f"</div>"
            )

        all_hooks_html = "\n".join(hook_html_parts)
        all_persons_html = "\n".join(person_html_parts)
        all_phrases_html = "\n      ".join(phrases_html)
        gsap_script = "\n      ".join(gsap_calls)

        progress_color = progress_layers[0].data.get("color", "#00FF66") if progress_layers else "#00FF66"

        return f"""<!doctype html>
<html lang="en" data-resolution="portrait">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={w_canvas}, height={h_canvas}" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link href="https://fonts.googleapis.com/css2?family=Anton&family=Montserrat:wght@800;900&display=swap" rel="stylesheet" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{
        width: {w_canvas}px;
        height: {h_canvas}px;
        background: #13151f;
        overflow: hidden;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      }}
      #root {{
        position: relative;
        width: {w_canvas}px;
        height: {h_canvas}px;
      }}
      .bg-video {{
        position: absolute;
        inset: 0;
        width: {w_canvas}px;
        height: {h_canvas}px;
        object-fit: cover;
        { "filter: blur(8px) grayscale(85%) contrast(115%) brightness(0.65);" if has_intro_blur else "" }
      }}
      .viral-hook-container {{
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 960px;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 16px;
        z-index: 15;
        pointer-events: none;
      }}
      .hook-row-1 {{
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 16px;
      }}
      .hook-brush-black {{
        background: #000000;
        color: #FFFFFF;
        padding: 10px 32px;
        border-radius: 4px;
        font-family: 'Anton', Impact, sans-serif;
        font-size: 58px;
        font-weight: 900;
        text-transform: uppercase;
        transform: rotate(-2deg);
        box-shadow: 0 10px 30px rgba(0,0,0,0.85);
        border: 2px solid #222222;
        letter-spacing: 0.02em;
      }}
      .hook-badge-red {{
        background: #D90429;
        color: #FFFFFF;
        padding: 8px 24px;
        border-radius: 8px;
        font-family: 'Anton', Impact, sans-serif;
        font-size: 38px;
        font-weight: 900;
        text-transform: uppercase;
        transform: rotate(1.5deg);
        box-shadow: 0 8px 24px rgba(217, 4, 41, 0.6);
        line-height: 1.1;
        letter-spacing: 0.02em;
      }}
      .hook-brush-yellow {{
        background: #FFE500;
        color: #000000;
        padding: 14px 44px;
        border-radius: 6px;
        font-family: 'Anton', Impact, sans-serif;
        font-size: 76px;
        font-weight: 900;
        text-transform: uppercase;
        letter-spacing: -0.02em;
        transform: rotate(-1deg);
        box-shadow: 0 12px 36px rgba(0,0,0,0.75);
      }}
      .hook-brush-white {{
        background: #FFFFFF;
        color: #000000;
        padding: 8px 30px;
        border-radius: 6px;
        font-family: 'Montserrat', sans-serif;
        font-size: 42px;
        font-weight: 900;
        text-transform: uppercase;
        transform: rotate(1deg);
        box-shadow: 0 8px 24px rgba(0,0,0,0.5);
      }}
      .hook-neon-green {{
        color: #39FF14;
        font-family: 'Anton', Impact, sans-serif;
        font-size: 104px;
        font-weight: 900;
        text-transform: uppercase;
        letter-spacing: -0.03em;
        text-shadow: 0 0 24px rgba(57, 255, 20, 0.85), 0 4px 20px #000000;
        text-align: center;
        line-height: 1.0;
      }}
      .hook-banner {{
        position: absolute;
        top: 80px;
        left: 60px;
        right: 60px;
        padding: 24px 32px;
        background: rgba(26, 30, 43, 0.94);
        border: 2px solid #293245;
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
      .person-card {{
        position: absolute;
        z-index: 5;
        pointer-events: none;
      }}
      .person-tag {{
        background: rgba(30, 35, 51, 0.85);
        color: #aab9c7;
        border: 1px solid #293245;
        font-size: 18px;
        font-weight: 700;
        padding: 6px 14px;
        border-radius: 8px;
        letter-spacing: 0.05em;
        text-transform: uppercase;
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
        font-family: '{font_family}', sans-serif;
        font-size: {font_size}px;
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
        width: {w_canvas}px;
        height: 12px;
        background: rgba(41, 50, 69, 0.7);
        z-index: 30;
      }}
      .progress-fill {{
        height: 100%;
        width: 0%;
        background: {progress_color};
        box-shadow: 0 0 12px {progress_color};
      }}
    </style>
  </head>
  <body>
    <div
      id="root"
      data-composition-id="main"
      data-start="0"
      data-duration="{duration:.2f}"
      data-width="{w_canvas}"
      data-height="{h_canvas}"
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

      {all_persons_html}

      {all_hooks_html}

      <div class="caption-container">
        {all_phrases_html}
      </div>

      <div class="progress-bar-container">
        <div id="progress" class="progress-fill"></div>
      </div>
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
      {gsap_script}
      window.__timelines["main"] = tl;
      tl.seek(0);
    </script>
  </body>
</html>
"""
