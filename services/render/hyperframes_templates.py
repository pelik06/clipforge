"""HyperFrames Composition Templates & AI Automation Generator.

Provides pre-built motion graphics layout archetypes (VIRAL_PODCAST, TWO_SPEAKER,
INTERVIEW, FINANCE, MINIMAL) and generates draft compositions from clip metadata.
"""

from typing import Any, Dict, List, Optional
import uuid

from core.models.transcript import TranscriptSegment, Word
from services.render.hyperframes_models import (
    AnimationType,
    CompositionLayer,
    HyperframesComposition,
    LayerType,
    TemplateType,
)


def extract_indonesian_viral_hook(
    clip: Dict[str, Any],
    clean_title: str,
    transcript_segments: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    """Generates structured Indonesian viral hook parts directly from clip dialogue:
    - top_tag (black brush box with white text)
    - badge_tag (red badge with white text)
    - highlight_text (bright yellow brush box with black text)
    - sub_text (white brush box with black text)
    - punchline (giant neon green bold text without excessive glow)
    """
    import re
    raw_str = (clean_title + " " + str(clip.get("title", "")) + " " + str(clip.get("vod", ""))).lower()
    uploader = str(clip.get("uploader", "")).upper()

    # Detect speaker name
    if "timothy" in raw_str:
        speaker_tag = "TIMOTHY"
    elif "bevan" in raw_str:
        speaker_tag = "BEVAN"
    elif "leon" in raw_str:
        speaker_tag = "LEON"
    elif uploader and uploader not in ("CREATOR", "UNKNOWN STREAMER"):
        speaker_tag = uploader.split()[0].upper()[:12]
    else:
        speaker_tag = "VIRAL"

    # 1. Discover most exciting dialogue directly from this clip's spoken segments
    selected_dialogue = None
    if transcript_segments:
        c_start = float(clip.get("start_time", 0.0))
        dur_val = float(str(clip.get("duration", "60.0")).replace("s", ""))
        c_end = float(clip.get("end_time", c_start + dur_val))
        clip_segs = [s for s in transcript_segments if getattr(s, "end", 0.0) > c_start and getattr(s, "start", 0.0) < c_end]

        VIRAL_KEYWORDS = {
            "miliar": 25, "miliaran": 25, "juta": 15, "cuan": 18, "untung": 15, "rugi": 16,
            "kaya": 16, "miskin": 14, "modal": 14, "kripto": 14, "crypto": 14, "trump": 18,
            "coin": 15, "meme": 16, "gila": 18, "parah": 16, "palsu": 20, "bohong": 18,
            "kaget": 16, "diusir": 20, "security": 20, "recall": 20, "ternyata": 16, "bocorin": 18,
            "rahasia": 18, "beneran": 16, "parah banget": 22, "onchain": 16, "wallet": 16,
        }
        best_score = -100
        for i, s in enumerate(clip_segs):
            txt = getattr(s, "text", "").strip()
            clean_txt = re.sub(r"[\r\n\t]+", " ", txt).strip()
            w_list = clean_txt.split()
            if len(w_list) < 2:
                continue
            sc = 0
            low = clean_txt.lower()
            for kw, pts in VIRAL_KEYWORDS.items():
                if kw in low:
                    sc += pts
            if i < 6:
                sc += 15
            if 3 <= len(w_list) <= 10:
                sc += 12
            elif len(w_list) > 14:
                sc -= 6
            if sc > best_score:
                best_score = sc
                selected_dialogue = clean_txt

    if selected_dialogue:
        words = [w.strip(".,!?:;\"'()[]") for w in selected_dialogue.split() if len(w.strip(".,!?:;\"'()[]")) > 0]
        filler = {"di", "e", "eh", "lah", "sih", "gitu", "terus", "gua", "lu", "itu", "yang", "ada", "basically"}
        content_words = [w for w in words if w.lower() not in filler]
        if not content_words:
            content_words = words

        if len(content_words) >= 4:
            highlight = " ".join(content_words[:2]).upper()
            sub = " ".join(content_words[2:5]).upper()
        elif len(content_words) >= 2:
            highlight = " ".join(content_words[:2]).upper()
            sub = "BONGKAR FAKTA NYATA"
        else:
            highlight = content_words[0].upper()
            sub = "LANGSUNG DARI PEMBICARA"

        badge = "NGAKU SENDIRI" if any(w in selected_dialogue.lower() for w in ("ngaku", "palsu", "gila")) else "BOCORIN RAHASIA"
        punchline = "PARAH BANGET!" if any(w in selected_dialogue.lower() for w in ("palsu", "gila", "parah")) else "NEXT BULL RUN!"

        return {
            "top_tag": speaker_tag,
            "badge_tag": badge,
            "highlight_text": highlight[:22],
            "sub_text": sub[:24],
            "punchline": punchline,
            "intro_blur_grayscale": True,
            "intro_duration": 2.2,
        }

    # Fallback to metadata
    if any(k in raw_str for k in ("meme", "coin", "4 miliar", "miliar", "cuan", "investasi", "kripto", "crypto", "bull", "market", "financial")):
        return {
            "top_tag": speaker_tag,
            "badge_tag": "BOCORIN RAHASIA",
            "highlight_text": "CUAN 4 MILIAR",
            "sub_text": "DARI MEME COIN",
            "punchline": "NEXT BULL RUN!",
            "intro_blur_grayscale": True,
            "intro_duration": 2.2,
        }
    elif any(k in raw_str for k in ("recall", "security", "diusir", "depan muka")):
        return {
            "top_tag": "TIMOTHY",
            "badge_tag": "DI RECALL RECALL",
            "highlight_text": "DEPAN MUKA",
            "sub_text": "SAMPE DIUSIR",
            "punchline": "SECURITY!",
            "intro_blur_grayscale": True,
            "intro_duration": 2.2,
        }
    else:
        words = [w for w in clean_title.upper().split() if w not in ("HIGHLIGHT", "#1", "#2", "#3", "#4", "#5")]
        h_main = " ".join(words[:2]) if len(words) >= 2 else (clean_title.upper() or "RAHASIA BESAR")
        h_sub = " ".join(words[2:5]) if len(words) > 2 else "WAJIB TAHU"
        return {
            "top_tag": speaker_tag,
            "badge_tag": "WAJIB NONTON",
            "highlight_text": h_main[:22],
            "sub_text": h_sub[:24],
            "punchline": "CUAN MAKSIMAL!",
            "intro_blur_grayscale": True,
            "intro_duration": 2.2,
        }

def generate_initial_composition(
    clip: Dict[str, Any],
    transcript_segments: Optional[List[Any]] = None,
    rf_analysis: Optional[Any] = None,
    template: Optional[str] = None,
) -> HyperframesComposition:
    """Automatically constructs an editable multi-layer HyperFrames composition

    from AI-detected clip moments, speakers, and transcript segments.
    """
    clip_id = str(clip.get("id", f"clip_{uuid.uuid4().hex[:6]}"))
    dur_val = float(str(clip.get("duration", "60.0")).replace("s", ""))
    src_start = float(clip.get("start_time", 0.0))
    src_end = float(clip.get("end_time", src_start + dur_val))

    raw_title = str(clip.get("title", "VIRAL HIGHLIGHT MOMENT"))
    # Clean up title for hook card (strip technical tags)
    clean_title = raw_title.split("[")[0].replace("Highlight #", "").strip()
    if ":" in clean_title:
        parts = clean_title.split(":", 1)
        clean_title = parts[1].strip() if len(parts) > 1 else parts[0].strip()
    if not clean_title or len(clean_title) < 4:
        clean_title = "CANVAS HIGHLIGHT"

    viral_hook_data = extract_indonesian_viral_hook(clip, clean_title, transcript_segments=transcript_segments)

    # Auto-select template based on detected speakers and content
    layout_mode = str(clip.get("layout_mode", "TRACK")).upper()
    has_dual_speakers = layout_mode == "SPLIT" or (
        rf_analysis and getattr(rf_analysis, "secondary_track_id", None) is not None
    )

    if template:
        selected_template = template
    elif has_dual_speakers:
        selected_template = TemplateType.TWO_SPEAKER.value
    elif "miliar" in raw_title.lower() or "cuan" in raw_title.lower() or "crypto" in raw_title.lower() or "financial" in raw_title.lower():
        selected_template = TemplateType.FINANCE.value
    elif "interview" in raw_title.lower() or "podcast" in raw_title.lower():
        selected_template = TemplateType.VIRAL_PODCAST.value
    else:
        selected_template = TemplateType.VIRAL_PODCAST.value

    # Parse and rebase words for caption layer
    clip_words: List[Dict[str, Any]] = []
    if transcript_segments:
        for s in transcript_segments:
            s_start = getattr(s, "start", 0.0)
            s_end = getattr(s, "end", 0.0)
            if s_end > src_start and s_start < src_end:
                words = getattr(s, "words", []) or []
                if words:
                    for w in words:
                        w_start = getattr(w, "start", s_start)
                        w_end = getattr(w, "end", s_end)
                        if w_end > src_start and w_start < src_end:
                            rel_s = max(0.0, round(w_start - src_start, 3))
                            rel_e = min(dur_val, round(w_end - src_start, 3))
                            if rel_e > rel_s:
                                clip_words.append({
                                    "text": getattr(w, "text", ""),
                                    "start": rel_s,
                                    "end": rel_e,
                                })
                else:
                    # Synthesize words from text tokens
                    text = getattr(s, "text", "")
                    toks = text.split()
                    if toks:
                        seg_dur = max(0.1, s_end - s_start)
                        step = seg_dur / max(1, len(toks))
                        for i, tok in enumerate(toks):
                            w0 = s_start + i * step
                            w1 = min(s_end, s_start + (i + 1) * step)
                            if w1 > src_start and w0 < src_end:
                                rel_s = max(0.0, round(w0 - src_start, 3))
                                rel_e = min(dur_val, round(w1 - src_start, 3))
                                if rel_e > rel_s:
                                    clip_words.append({
                                        "text": tok,
                                        "start": rel_s,
                                        "end": rel_e,
                                    })

    composition = HyperframesComposition(
        composition_id=f"comp_{clip_id}_{uuid.uuid4().hex[:6]}",
        clip_id=clip_id,
        template=selected_template,
        width=1080,
        height=1920,
        duration=dur_val,
        captions=clip_words,
        metadata={
            "source_vod": clip.get("vod"),
            "score": clip.get("score"),
            "hook_type": clip.get("hook_type"),
            "payoff_type": clip.get("payoff_type"),
        },
    )

    # 1. Base Video Layer (Always Present)
    video_src = clip.get("media_url") or "video.mp4"
    composition.add_layer(
        CompositionLayer(
            id="layer_video_bg",
            type=LayerType.VIDEO,
            start=0.0,
            end=dur_val,
            x=540.0,
            y=960.0,
            width=1080.0,
            height=1920.0,
            scale=1.0,
            z_index=0,
            visible=True,
            animation_in={"type": "none"},
            animation_out={"type": "none"},
            data={
                "src": video_src,
                "has_audio": True,
                "volume": 1.0,
            },
        )
    )

    # 2. Progress Bar Layer
    composition.add_layer(
        CompositionLayer(
            id="layer_progress_bar",
            type=LayerType.PROGRESS_BAR,
            start=0.0,
            end=dur_val,
            x=540.0,
            y=1914.0,
            width=1080.0,
            height=12.0,
            scale=1.0,
            z_index=10,
            visible=True,
            animation_in={"type": "none"},
            animation_out={"type": "none"},
            data={
                "color": "#00FF66" if selected_template == TemplateType.FINANCE.value else "#FCD34D",
                "bg_color": "rgba(41, 50, 69, 0.7)",
                "height": 12,
            },
        )
    )

    # 3. Template-Specific Layers
    hook_end = min(12.0, max(5.0, dur_val * 0.20))

    if selected_template == TemplateType.TWO_SPEAKER.value:
        # Person A (Left/Top)
        composition.add_layer(
            CompositionLayer(
                id="layer_person_a",
                type=LayerType.PERSON,
                start=0.0,
                end=dur_val,
                x=320.0,
                y=650.0,
                width=500.0,
                height=650.0,
                scale=1.0,
                z_index=2,
                visible=True,
                animation_in={"type": "slide_left", "duration": 0.5},
                data={"person_label": "Speaker 1", "badge": "HOST", "highlight": True},
            )
        )
        # Person B (Right/Bottom)
        composition.add_layer(
            CompositionLayer(
                id="layer_person_b",
                type=LayerType.PERSON,
                start=0.0,
                end=dur_val,
                x=760.0,
                y=650.0,
                width=500.0,
                height=650.0,
                scale=1.0,
                z_index=2,
                visible=True,
                animation_in={"type": "slide_right", "duration": 0.5},
                data={"person_label": "Speaker 2", "badge": "GUEST", "highlight": False},
            )
        )
        # Hook Title
        composition.add_layer(
            CompositionLayer(
                id="layer_hook_title",
                type=LayerType.HOOK,
                start=0.0,
                end=hook_end,
                x=540.0,
                y=180.0,
                width=960.0,
                height=160.0,
                scale=1.0,
                z_index=5,
                visible=True,
                animation_in={"type": "slide_down", "duration": 0.5},
                animation_out={"type": "fade", "duration": 0.4},
                data={
                    "title": clean_title,
                    "subtitle": "DUAL CONVERSATION",
                    "badge": "★ PODCAST HIGHLIGHT",
                    "bg_color": "rgba(26, 30, 43, 0.92)",
                    "border_color": "#293245",
                    "text_color": "#E9ECEE",
                    **viral_hook_data,
                },
            )
        )

    elif selected_template == TemplateType.FINANCE.value:
        composition.add_layer(
            CompositionLayer(
                id="layer_hook_title",
                type=LayerType.HOOK,
                start=0.0,
                end=hook_end,
                x=540.0,
                y=200.0,
                width=980.0,
                height=170.0,
                scale=1.0,
                z_index=5,
                visible=True,
                animation_in={"type": "pop", "duration": 0.4},
                animation_out={"type": "fade", "duration": 0.4},
                data={
                    "title": clean_title,
                    "subtitle": "NEXT BULL MARKET ALPHA",
                    "badge": "💰 WEALTH HIGHLIGHT",
                    "bg_color": "rgba(20, 38, 29, 0.94)",
                    "border_color": "#1F4A3D",
                    "text_color": "#FFDE00",
                    "accent_color": "#00FF66",
                    **viral_hook_data,
                },
            )
        )
        composition.add_layer(
            CompositionLayer(
                id="layer_person_a",
                type=LayerType.PERSON,
                start=0.0,
                end=dur_val,
                x=540.0,
                y=800.0,
                width=800.0,
                height=900.0,
                scale=1.0,
                z_index=1,
                visible=True,
                animation_in={"type": "fade", "duration": 0.3},
                data={"person_label": "Financial Expert", "badge": "ALPHA CALL"},
            )
        )

    elif selected_template == TemplateType.INTERVIEW.value:
        composition.add_layer(
            CompositionLayer(
                id="layer_hook_title",
                type=LayerType.HOOK,
                start=0.0,
                end=hook_end,
                x=540.0,
                y=220.0,
                width=940.0,
                height=150.0,
                scale=1.0,
                z_index=5,
                visible=True,
                animation_in={"type": "slide_down", "duration": 0.5},
                animation_out={"type": "fade", "duration": 0.4},
                data={
                    "title": clean_title,
                    "subtitle": "EXCLUSIVE INTERVIEW",
                    "badge": "🎙️ TALK HIGHLIGHT",
                    "bg_color": "rgba(26, 30, 43, 0.92)",
                    "border_color": "#293245",
                    "text_color": "#E9ECEE",
                    **viral_hook_data,
                },
            )
        )

    elif selected_template == TemplateType.MINIMAL.value:
        composition.add_layer(
            CompositionLayer(
                id="layer_hook_title",
                type=LayerType.HOOK,
                start=0.0,
                end=min(6.0, hook_end),
                x=540.0,
                y=160.0,
                width=880.0,
                height=120.0,
                scale=1.0,
                z_index=4,
                visible=True,
                animation_in={"type": "fade", "duration": 0.4},
                animation_out={"type": "fade", "duration": 0.4},
                data={
                    "title": clean_title,
                    "badge": "HIGHLIGHT",
                    "bg_color": "rgba(19, 21, 31, 0.85)",
                    "border_color": "#293245",
                    "text_color": "#E9ECEE",
                },
            )
        )

    else:  # VIRAL_PODCAST (Default)
        composition.add_layer(
            CompositionLayer(
                id="layer_person_a",
                type=LayerType.PERSON,
                start=0.0,
                end=dur_val,
                x=540.0,
                y=780.0,
                width=850.0,
                height=920.0,
                scale=1.0,
                z_index=1,
                visible=True,
                animation_in={"type": "scale", "duration": 0.4},
                data={"person_label": "Key Speaker", "badge": "HOT TAKE"},
            )
        )
        composition.add_layer(
            CompositionLayer(
                id="layer_hook_title",
                type=LayerType.HOOK,
                start=0.0,
                end=hook_end,
                x=540.0,
                y=190.0,
                width=960.0,
                height=160.0,
                scale=1.0,
                z_index=5,
                visible=True,
                animation_in={"type": "spring", "duration": 0.6},
                animation_out={"type": "fade", "duration": 0.4},
                data={
                    "title": clean_title,
                    "subtitle": "BEST VIRAL TAKE",
                    "badge": "🔥 VIRAL MOMENT",
                    "bg_color": "rgba(26, 30, 43, 0.92)",
                    "border_color": "#293245",
                    "text_color": "#E9ECEE",
                    **viral_hook_data,
                },
            )
        )

    # 4. Kinetic Captions Layer (Overlay across clip duration)
    composition.add_layer(
        CompositionLayer(
            id="layer_captions",
            type=LayerType.CAPTION,
            start=0.0,
            end=dur_val,
            x=540.0,
            y=1640.0,
            width=960.0,
            height=240.0,
            scale=1.0,
            z_index=8,
            visible=True,
            animation_in={"type": "word_pop", "duration": 0.15},
            data={
                "font_family": "Anton",
                "font_size": 72,
                "text_color": "#FFDE00" if selected_template == TemplateType.FINANCE.value else "#FFFFFF",
                "active_color": "#00FF66" if selected_template == TemplateType.FINANCE.value else "#FCD34D",
                "stroke_color": "#000000",
                "stroke_width": 4,
                "position": "bottom_safe",
            },
        )
    )

    return composition
