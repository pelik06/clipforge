import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from core.config.settings import Settings
from core.models.configuration import (
    CaptionLanguage,
    CaptionPosition,
    CaptionPreset,
    CaptionSize,
    JobConfig,
)
from core.models.transcript import TranscriptSegment, Word


def hex_to_ass_color(hex_color: str, alpha: str = "00") -> str:
    """Convert #RRGGBB or #RGB to ASS format &H<AA><BB><GG><RR>&."""
    clean = (hex_color or "#FFFFFF").strip().lstrip("#")
    if len(clean) == 3:
        clean = "".join([c * 2 for c in clean])
    if len(clean) != 6:
        clean = "FFFFFF"
    r = clean[0:2].upper()
    g = clean[2:4].upper()
    b = clean[4:6].upper()
    return f"&H{alpha}{b}{g}{r}&"


def format_ass_time(seconds: float) -> str:
    """Format float seconds to ASS timestamp format H:MM:SS.cs."""
    s = max(0.0, float(seconds))
    hrs = int(s // 3600)
    mins = int((s % 3600) // 60)
    secs = int(s % 60)
    cs = int(round((s - int(s)) * 100))
    if cs >= 100:
        secs += 1
        cs = 0
    return f"{hrs}:{mins:02d}:{secs:02d}.{cs:02d}"


def escape_ass_text(text: str) -> str:
    """Escape special ASS characters and clean newlines."""
    # Replace backslashes and braces that could disrupt ASS override tags
    t = text.replace("\\", "\\\\").replace("{", "(").replace("}", ")")
    t = t.replace("\n", " ").strip()
    return t
def adjust_segments_for_clip(
    segments: List[TranscriptSegment],
    clip_start: float = 0.0,
    clip_end: Optional[float] = None,
) -> List[TranscriptSegment]:
    """Adjust absolute source video timestamps to relative clip timestamps [0, clip_duration]."""
    if clip_start <= 0.0 and clip_end is None:
        return segments

    adjusted: List[TranscriptSegment] = []
    max_t = (clip_end - clip_start) if clip_end is not None else float("inf")

    for seg in segments:
        # If segment is completely outside clip window, skip
        if seg.end <= clip_start or (clip_end is not None and seg.start >= clip_end):
            continue

        rel_start = max(0.0, round(seg.start - clip_start, 3))
        rel_end = max(rel_start + 0.1, round(seg.end - clip_start, 3))
        if clip_end is not None:
            rel_end = min(max_t, rel_end)

        adjusted_words: List[Word] = []
        if seg.words:
            for w in seg.words:
                if w.end <= clip_start or (clip_end is not None and w.start >= clip_end):
                    continue
                w_rel_start = max(0.0, round(w.start - clip_start, 3))
                w_rel_end = max(w_rel_start + 0.05, round(w.end - clip_start, 3))
                if clip_end is not None:
                    w_rel_end = min(max_t, w_rel_end)
                adjusted_words.append(Word(text=w.text, start=w_rel_start, end=w_rel_end))

        adjusted.append(
            TranscriptSegment(
                text=seg.text,
                start=rel_start,
                end=rel_end,
                words=adjusted_words,
            )
        )
    return adjusted


def validate_ass_file(ass_path: str, clip_duration: float = 0.0) -> Dict[str, Any]:
    """Validate that an ASS subtitle file is non-empty, contains styles and valid dialogues."""
    p = Path(ass_path)
    if not p.exists() or p.stat().st_size == 0:
        raise ValueError(f"ASS file does not exist or is empty: {ass_path}")

    content = p.read_text(encoding="utf-8", errors="ignore")
    if "[Script Info]" not in content:
        raise ValueError("Invalid ASS file: missing [Script Info] header")
    if "[V4+ Styles]" not in content:
        raise ValueError("Invalid ASS file: missing [V4+ Styles] section")

    dialogues = [line for line in content.splitlines() if line.strip().startswith("Dialogue:")]
    if not dialogues:
        raise ValueError(f"ASS validation failed: zero Dialogue events found in {ass_path}")

    return {
        "valid": True,
        "dialogue_count": len(dialogues),
        "file_size": p.stat().st_size,
    }


def verify_caption_in_frame(
    video_path: str,
    timestamp: float = 1.0,
    raw_reference_video: Optional[str] = None,
    save_verification_name: Optional[str] = None,
) -> bool:
    """Inspect actual video frame to verify that burned subtitle pixels exist, saving proof frames."""
    try:
        import cv2
        import numpy as np

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return False
        cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, timestamp) * 1000.0)
        ret, frame_burned = cap.read()
        cap.release()
        if not ret or frame_burned is None:
            return False

        verification_dir = Path("caption_verification")
        verification_dir.mkdir(parents=True, exist_ok=True)
        base_name = save_verification_name or Path(video_path).stem

        # Save captioned frame
        cv2.imwrite(str(verification_dir / f"{base_name}_captioned.jpg"), frame_burned)

        if raw_reference_video and Path(raw_reference_video).exists():
            cap_raw = cv2.VideoCapture(raw_reference_video)
            if cap_raw.isOpened():
                cap_raw.set(cv2.CAP_PROP_POS_MSEC, max(0.0, timestamp) * 1000.0)
                ret_raw, frame_raw = cap_raw.read()
                cap_raw.release()
                if ret_raw and frame_raw is not None and frame_raw.shape == frame_burned.shape:
                    cv2.imwrite(str(verification_dir / f"{base_name}_raw.jpg"), frame_raw)
                    diff = np.abs(frame_burned.astype(np.int32) - frame_raw.astype(np.int32))
                    return bool(diff.max() > 25 and np.count_nonzero(diff > 20) > 50)

        # High-contrast edge check in subtitle region
        gray = cv2.cvtColor(frame_burned, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 80, 180)
        h = gray.shape[0]
        sub_region = edges[int(h * 0.65):, :]
        return bool(np.count_nonzero(sub_region) > 30)
    except Exception:
        return False


class CaptionRenderer:
    """Generate ASS subtitle scripts and burn them into video via FFmpeg libass."""

    def __init__(self):
        self.settings = Settings()

    def generate_ass_script(
        self,
        segments: List[TranscriptSegment],
        config: Optional[JobConfig] = None,
        video_width: int = 1080,
        video_height: int = 1920,
        clip_start: float = 0.0,
        clip_end: Optional[float] = None,
    ) -> str:
        """Generate complete ASS subtitle script content matching user preset and styling."""
        cfg = config or JobConfig()
        if clip_start > 0.0 or clip_end is not None:
            segments = adjust_segments_for_clip(segments, clip_start=clip_start, clip_end=clip_end)

        preset = cfg.caption_preset
        text_color_ass = hex_to_ass_color(cfg.caption_text_color)
        highlight_color_ass = hex_to_ass_color(cfg.caption_highlight_color)

        # 1. Font size mapping
        size_map = {
            CaptionSize.SMALL.value: 46,
            CaptionSize.MEDIUM.value: 64,
            CaptionSize.LARGE.value: 86,
        }
        font_size = size_map.get(cfg.caption_size, 64)

        # 2. Position and margin mapping
        # ASS Alignment: 2 = bottom-center, 5 = middle-center, 8 = top-center
        pos_map = {
            CaptionPosition.BOTTOM_SAFE.value: (2, 260),  # Safe above platform UI
            CaptionPosition.CENTER.value: (5, 0),
            CaptionPosition.TOP_SAFE.value: (8, 220),     # Safe below status bars
        }
        alignment, margin_v = pos_map.get(cfg.caption_position, (2, 260))

        # 3. Preset specific styling
        # Font choices available across standard Windows installations
        if preset == CaptionPreset.CREATOR_BOLD.value:
            font_name = "Impact"
            bold = -1
            outline = 4
            shadow = 2
            outline_color = "&H00000000&"
            back_color = "&H80000000&"
        elif preset == CaptionPreset.KARAOKE.value:
            font_name = "Arial Black"
            bold = -1
            outline = 4
            shadow = 2
            outline_color = "&H00000000&"
            back_color = "&H80000000&"
        elif preset == CaptionPreset.MINIMAL.value:
            font_name = "Segoe UI"
            bold = 0
            outline = 1
            shadow = 0
            outline_color = "&H40000000&"
            back_color = "&H00000000&"
            font_size = int(round(font_size * 0.85))
        else:  # CLEAN preset default
            font_name = "Arial"
            bold = -1
            outline = 2
            shadow = 1
            outline_color = "&H00000000&"
            back_color = "&H80000000&"

        header = f"""[Script Info]
Title: ClipForge Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: {video_width}
PlayResY: {video_height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},{text_color_ass},{highlight_color_ass},{outline_color},{back_color},{bold},0,0,0,100,100,0,0,1,{outline},{shadow},{alignment},60,60,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        events = []
        is_highlight_active = (
            preset == CaptionPreset.KARAOKE.value or cfg.caption_word_highlight
        )

        for seg in segments:
            seg_start = format_ass_time(seg.start)
            seg_end = format_ass_time(seg.end)
            seg_text = escape_ass_text(seg.text)

            has_words = bool(seg.words and len(seg.words) > 0)

            if is_highlight_active and has_words:
                # Word-level highlighting using actual verified timestamps
                words_list = seg.words
                for curr_idx, w in enumerate(words_list):
                    w_start = format_ass_time(w.start)
                    w_end = format_ass_time(w.end)

                    # Build phrase with active word wrapped in highlight color tags
                    phrase_parts = []
                    for idx, other_w in enumerate(words_list):
                        w_clean = escape_ass_text(other_w.text)
                        if idx == curr_idx:
                            # Highlighted active word
                            phrase_parts.append(f"{{\\c{highlight_color_ass}}}{w_clean}{{\\c{text_color_ass}}}")
                        else:
                            phrase_parts.append(w_clean)

                    line_text = " ".join(phrase_parts)
                    events.append(
                        f"Dialogue: 0,{w_start},{w_end},Default,,0,0,0,,{line_text}"
                    )
            else:
                if preset == CaptionPreset.KARAOKE.value and not has_words:
                    # In karaoke preset without word timestamps, cannot synthesize timing
                    raise ValueError(
                        "Karaoke preset requires verified word-level timestamps, but segment has no word timestamps."
                    )
                # Static segment subtitle
                events.append(
                    f"Dialogue: 0,{seg_start},{seg_end},Default,,0,0,0,,{seg_text}"
                )

        return header + "\n".join(events) + "\n"

    def render(
        self,
        transcript_segments: List[TranscriptSegment],
        video_path: str,
        output_path: str,
        config: Optional[JobConfig] = None,
        clip_start: float = 0.0,
        clip_end: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Burn captions into video using FFmpeg and libass, adjusting for clip timeline offset."""
        cfg = config or JobConfig()
        adjusted_segments = adjust_segments_for_clip(
            transcript_segments, clip_start=clip_start, clip_end=clip_end
        )

        src = Path(video_path)
        if not src.exists():
            raise FileNotFoundError(f"Source video not found: {video_path}")

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        # If user selected no_captions, skip rendering directly
        if cfg.caption_preset == CaptionPreset.NO_CAPTIONS.value:
            # Copy or hardlink video unchanged
            if src.resolve() != out.resolve():
                out.write_bytes(src.read_bytes())
            return {
                "status": "skipped",
                "reason": "captions disabled by user",
                "output_path": str(out),
                "ass_path": None,
            }

        if not adjusted_segments:
            # No dialogue falls within this specific clip window
            if src.resolve() != out.resolve():
                out.write_bytes(src.read_bytes())
            return {
                "status": "skipped",
                "reason": "no speech transcript in clip window",
                "output_path": str(out),
                "ass_path": None,
            }

        # Check karaoke requirement
        if cfg.caption_preset == CaptionPreset.KARAOKE.value:
            has_any_words = any(s.words and len(s.words) > 0 for s in transcript_segments)
            if not has_any_words:
                raise ValueError("word-level timestamps unavailable for Karaoke preset")

        # Generate ASS script in work directory
        work_dir = Path("data/work")
        work_dir.mkdir(parents=True, exist_ok=True)
        ass_path = work_dir / f"caption_{out.stem}.ass"

        ass_content = self.generate_ass_script(adjusted_segments, config=cfg)
        ass_path.write_text(ass_content, encoding="utf-8")
        validate_ass_file(str(ass_path))
        # Windows FFmpeg escaping for libass filter: forward slashes + colon escaped
        escaped_ass = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")
        vf_filter = f"ass=filename='{escaped_ass}'"

        cmd = [
            self.settings.ffmpeg_bin,
            "-y",
            "-i", str(src),
            "-vf", vf_filter,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "22",
            "-c:a", "copy",
            "-movflags", "+faststart",
            str(out),
        ]

        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=180,
        )

        if proc.returncode != 0:
            # Fallback audio transcode if audio copy rejected by container
            fallback_cmd = [
                self.settings.ffmpeg_bin,
                "-y",
                "-i", str(src),
                "-vf", vf_filter,
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "22",
                "-c:a", "aac",
                "-movflags", "+faststart",
                str(out),
            ]
            proc = subprocess.run(
                fallback_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=180,
            )
            if proc.returncode != 0:
                raise RuntimeError(
                    f"FFmpeg caption rendering failed (code {proc.returncode}): {proc.stderr[-400:]}"
                )

        if not out.exists() or out.stat().st_size == 0:
            raise RuntimeError(f"Caption rendering completed but output file missing or empty: {output_path}")

        is_visible = verify_caption_in_frame(
            str(out),
            timestamp=1.2,
            raw_reference_video=str(src),
            save_verification_name=out.stem,
        )
        return {
            "status": "completed",
            "reason": None,
            "output_path": str(out),
            "ass_path": str(ass_path),
            "preset": cfg.caption_preset,
            "caption_visible": is_visible,
        }
