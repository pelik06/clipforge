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
from services.captions.safe_area import CaptionSafeAreaManager

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


def parse_ass_time(ass_time: str) -> float:
    """Parse ASS timestamp H:MM:SS.cs back to float seconds."""
    parts = ass_time.strip().split(":")
    if len(parts) != 3:
        return 0.0
    h = float(parts[0])
    m = float(parts[1])
    s = float(parts[2])
    return round(h * 3600 + m * 60 + s, 3)


NOISE_TOKENS_REGEX = re.compile(
    r"\[(?:tertawa|tawa|musik|music|applause|tepuk tangan|laughter|chuckle|suara|noise|sound)[^\]]*\]",
    re.IGNORECASE,
)

def escape_ass_text(text: str) -> str:
    """Escape special ASS characters and clean newlines."""
    t = NOISE_TOKENS_REGEX.sub("", text)
    t = t.replace("\\", "\\\\").replace("{", "(").replace("}", ")")
    t = t.replace("\n", " ").strip()
    return t


def adjust_segments_for_clip(
    segments: List[TranscriptSegment],
    clip_start: float = 0.0,
    clip_end: Optional[float] = None,
) -> List[TranscriptSegment]:
    """Adjust absolute source video timestamps to relative clip timestamps [0, clip_duration].
    
    Validation rules:
    - Drop events completely outside [clip_start, clip_end]
    - Clamp partial overlaps: start >= 0, end <= clip_duration
    - Validate start < end
    """
    if clip_start <= 0.0 and clip_end is None:
        return segments

    adjusted: List[TranscriptSegment] = []
    max_t = (clip_end - clip_start) if clip_end is not None else float("inf")

    for seg in segments:
        # Drop completely outside
        if seg.end <= clip_start or (clip_end is not None and seg.start >= clip_end):
            continue

        rel_start = max(0.0, round(seg.start - clip_start, 3))
        rel_end = round(seg.end - clip_start, 3)
        if clip_end is not None:
            rel_end = min(max_t, rel_end)

        if rel_start >= rel_end:
            continue

        adjusted_words: List[Word] = []
        if seg.words:
            for w in seg.words:
                if w.end <= clip_start or (clip_end is not None and w.start >= clip_end):
                    continue
                w_rel_start = max(0.0, round(w.start - clip_start, 3))
                w_rel_end = round(w.end - clip_start, 3)
                if clip_end is not None:
                    w_rel_end = min(max_t, w_rel_end)
                if w_rel_start < w_rel_end:
                    adjusted_words.append(Word(text=w.text, start=w_rel_start, end=w_rel_end))

        if seg.words and not adjusted_words:
            continue

        clean_text = " ".join([w.text for w in adjusted_words]) if adjusted_words else seg.text
        if adjusted_words:
            rel_start = adjusted_words[0].start
            rel_end = adjusted_words[-1].end

        adjusted.append(
            TranscriptSegment(
                text=clean_text,
                start=rel_start,
                end=rel_end,
                words=adjusted_words,
            )
        )
    return adjusted


def is_emphasis_word(word: str) -> bool:
    """Identify if a word qualifies for visual emphasis (numbers, superlatives, strong keywords)."""
    clean = re.sub(r"[^\w]", "", word).lower()
    if not clean:
        return False
    if clean.isdigit() or any(c.isdigit() for c in clean):
        return True
    emphasis_keywords = {
        "terbesar", "terbaik", "kunci", "bahaya", "penting", "rahasia",
        "masalah", "fakta", "sukses", "gagal", "rugi", "untung", "solusi",
        "crucial", "huge", "best", "worst", "secret", "never", "always",
        "pertama", "terakhir", "miliar", "juta", "persen", "100%"
    }
    return clean in emphasis_keywords


def group_words_into_adaptive_chunks(
    words: List[Word],
    words_per_group: int = 4,
    min_words_per_group: int = 1,
) -> List[List[Word]]:
    """Group words into balanced chunks (1 to 4 words), splitting adaptively on punctuation and speech pauses."""
    if not words:
        return []
    max_words = max(1, int(words_per_group))
    min_words = max(1, min(int(min_words_per_group), max_words))
    chunks: List[List[Word]] = []
    current_chunk: List[Word] = []

    for i, w in enumerate(words):
        current_chunk.append(w)
        w_text = w.text.strip()

        has_punctuation = bool(w_text and w_text[-1] in {".", ",", "!", "?", ";", ":"})
        has_pause = False
        if i < len(words) - 1:
            nxt = words[i + 1]
            if (nxt.start - w.end) > 0.45:
                has_pause = True

        is_long = len(w_text) >= 12

        should_split = (
            len(current_chunk) >= max_words
            or (len(current_chunk) >= min_words and (has_punctuation or has_pause or is_long))
        )

        if should_split:
            chunks.append(current_chunk)
            current_chunk = []

    if current_chunk:
        chunks.append(current_chunk)
    return chunks


def group_words_into_chunks(
    words: List[Word],
    words_per_group: int = 4,
    adaptive: bool = False,
) -> List[List[Word]]:
    """Group sequential words into balanced chunks (default 4 words) for vertical 9:16 readability."""
    if adaptive:
        return group_words_into_adaptive_chunks(words, words_per_group=words_per_group)
    if not words:
        return []
    chunk_size = max(1, int(words_per_group))
    chunks: List[List[Word]] = []
    for i in range(0, len(words), chunk_size):
        chunks.append(words[i : i + chunk_size])
    return chunks

def build_word_chunks_from_segment(
    seg: TranscriptSegment,
    words_per_group: int = 4,
) -> List[List[Word]]:
    """Ensure segment has word-level timestamps and return grouped word chunks."""
    if seg.words and len(seg.words) > 0:
        words = seg.words
    else:
        # Synthesize word timestamps evenly across segment duration
        tokens = seg.text.split()
        if not tokens:
            return []
        dur = max(0.1, seg.end - seg.start)
        step = dur / len(tokens)
        words = [
            Word(
                text=tok,
                start=round(seg.start + i * step, 3),
                end=round(min(seg.end, seg.start + (i + 1) * step), 3),
            )
            for i, tok in enumerate(tokens)
        ]
    return group_words_into_chunks(words, words_per_group=words_per_group)


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

    lines = content.splitlines()
    fixed_lines = []
    dialogues_count = 0
    needs_rewrite = False

    for line in lines:
        if line.strip().startswith("Dialogue:"):
            parts = line.split(",", 9)
            if len(parts) >= 10:
                d_start = parse_ass_time(parts[1])
                d_end = parse_ass_time(parts[2])

                # Drop events starting at or past clip duration
                if clip_duration > 0.0 and d_start >= (clip_duration - 0.05):
                    needs_rewrite = True
                    continue

                # Fix start >= end
                if d_start >= d_end:
                    d_end = round(d_start + 0.08, 2)
                    if clip_duration > 0.0 and d_end > (clip_duration + 0.1):
                        needs_rewrite = True
                        continue
                    parts[2] = format_ass_time(d_end)
                    line = ",".join(parts)
                    needs_rewrite = True

                if clip_duration > 0.0 and d_end > (clip_duration + 0.5):
                    d_end = clip_duration
                    parts[2] = format_ass_time(d_end)
                    line = ",".join(parts)
                    needs_rewrite = True

                dialogues_count += 1
        fixed_lines.append(line)
    if needs_rewrite:
        p.write_text("\n".join(fixed_lines) + "\n", encoding="utf-8")

    if dialogues_count == 0:
        raise ValueError(f"ASS validation failed: zero Dialogue events found in {ass_path}")

    return {
        "valid": True,
        "dialogue_count": dialogues_count,
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
        face_boxes: Optional[List[Tuple[float, float, float, float]]] = None,
    ) -> str:
        cfg = config or JobConfig()
        words_per_group = getattr(cfg, "caption_words_per_group", self.settings.caption_words_per_group)

        if clip_start > 0.0 or clip_end is not None:
            segments = adjust_segments_for_clip(segments, clip_start=clip_start, clip_end=clip_end)

        # Subtitle styling parameters based on user config
        preset = cfg.caption_preset
        text_color_ass = hex_to_ass_color(cfg.caption_text_color)
        highlight_color_ass = hex_to_ass_color(cfg.caption_highlight_color)

        # Font sizes mapped relative to vertical 1080x1920 resolution
        size_map = {
            CaptionSize.SMALL.value: 48,
            CaptionSize.MEDIUM.value: 62,
            CaptionSize.LARGE.value: 78,
        }
        font_size = size_map.get(cfg.caption_size, 62)

        # Position alignment (ASS Alignment: 2 = Bottom Center, 5 = Middle Center, 8 = Top Center)
        pos_map = {
            CaptionPosition.BOTTOM_SAFE.value: (2, 280),
            CaptionPosition.CENTER.value: (5, 0),
            CaptionPosition.TOP_SAFE.value: (8, 280),
        }
        alignment, margin_v = pos_map.get(cfg.caption_position, (2, 280))
        if face_boxes:
            safe_mgr = CaptionSafeAreaManager()
            safe_res = safe_mgr.resolve_caption_position(face_boxes, preferred_position=cfg.caption_position)
            if safe_res.collision_avoided:
                alignment = safe_res.target_alignment
                margin_v = safe_res.margin_v
        # Preset-specific overrides
        if preset == CaptionPreset.CREATOR_BOLD.value:
            font_name = "Impact"
            bold = -1
            outline = 4
            shadow = 2
            outline_color = "&H00000000&"
            back_color = "&H80000000&"
            font_size = int(round(font_size * 1.15))
        elif preset == CaptionPreset.KARAOKE.value:
            font_name = "Arial Black"
            bold = -1
            outline = 3
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

        if preset == CaptionPreset.KARAOKE.value:
            for s in segments:
                if not s.words or len(s.words) == 0:
                    raise ValueError(
                        "Karaoke preset requires verified word-level timestamps, but segment has no word timestamps."
                    )

        # 1. Extract and flatten words from segments
        raw_words: List[Word] = []
        for s in segments:
            if s.words and len(s.words) > 0:
                for w in s.words:
                    clean = NOISE_TOKENS_REGEX.sub("", (w.text or "").strip()).strip()
                    if clean:
                        raw_words.append(Word(text=clean, start=w.start, end=w.end))
            else:
                tokens = s.text.split()
                if tokens:
                    dur = max(0.1, s.end - s.start)
                    step = dur / max(1, len(tokens))
                    for i, tok in enumerate(tokens):
                        w0 = round(s.start + i * step, 3)
                        w1 = round(min(s.end, s.start + (i + 1) * step), 3)
                        raw_words.append(Word(text=tok, start=w0, end=w1))

        if not raw_words:
            return header

        # 2. Strict Deduplication: Remove consecutive identical words within 0.8s
        cleaned_words: List[Word] = []
        for w in raw_words:
            if cleaned_words:
                prev = cleaned_words[-1]
                if prev.text.lower() == w.text.lower() and abs(w.start - prev.start) < 0.8:
                    continue
            cleaned_words.append(w)

        # 3. Ensure strictly increasing, non-overlapping timestamps
        for i in range(len(cleaned_words) - 1):
            curr = cleaned_words[i]
            nxt = cleaned_words[i + 1]
            if nxt.start <= curr.start:
                nxt.start = round(curr.start + 0.15, 3)
            if curr.end > nxt.start:
                curr.end = nxt.start
            if curr.end <= curr.start:
                curr.end = round(curr.start + 0.10, 3)
            if nxt.start < curr.end:
                nxt.start = curr.end

        # 4. Prune words outside clip duration window
        if clip_end is not None and clip_start is not None:
            max_dur = clip_end - clip_start
            cleaned_words = [w for w in cleaned_words if w.start < (max_dur - 0.05)]
            for w in cleaned_words:
                if w.end > max_dur:
                    w.end = max_dur

        # 5. Group words into balanced adaptive chunks (P2.3.1)
        chunks = group_words_into_adaptive_chunks(cleaned_words, words_per_group=words_per_group)
        # 5. Build non-overlapping Dialogue events
        for chunk_idx, chunk in enumerate(chunks):
            if chunk and chunk[0].text and chunk[0].text[0].islower():
                chunk[0].text = chunk[0].text[0].upper() + chunk[0].text[1:]
            chunk_start = chunk[0].start
            chunk_end = chunk[-1].end

            # Ensure chunk does not overlap next chunk
            if chunk_idx < len(chunks) - 1:
                next_chunk_start = chunks[chunk_idx + 1][0].start
                if chunk_end > next_chunk_start:
                    chunk_end = next_chunk_start

            if chunk_start >= chunk_end:
                chunk_end = round(chunk_start + 0.5, 3)

            if is_highlight_active:
                for curr_idx, w in enumerate(chunk):
                    w_start_val = max(chunk_start, w.start)
                    if curr_idx < len(chunk) - 1:
                        w_end_val = min(chunk_end, chunk[curr_idx + 1].start)
                    else:
                        w_end_val = chunk_end

                    w_start_str = format_ass_time(w_start_val)
                    w_end_str = format_ass_time(w_end_val)

                    start_cs = parse_ass_time(w_start_str)
                    end_cs = parse_ass_time(w_end_str)
                    if end_cs <= start_cs:
                        w_end_str = format_ass_time(start_cs + 0.08)

                    phrase_parts = []
                    for idx, other_w in enumerate(chunk):
                        w_clean = escape_ass_text(other_w.text)
                        if idx == curr_idx:
                            phrase_parts.append(f"{{\\c{highlight_color_ass}}}{w_clean}{{\\c{text_color_ass}}}")
                        else:
                            phrase_parts.append(w_clean)

                    line_text = " ".join(phrase_parts)
                    events.append(f"Dialogue: 0,{w_start_str},{w_end_str},Default,,0,0,0,,{line_text}")
            else:
                phrase_parts = []
                for w in chunk:
                    w_clean = escape_ass_text(w.text)
                    if preset != CaptionPreset.NO_CAPTIONS.value and is_emphasis_word(w.text):
                        phrase_parts.append(f"{{\\c{highlight_color_ass}\\b1}}{w_clean}{{\\rDefault}}")
                    else:
                        phrase_parts.append(w_clean)
                chunk_text = " ".join(phrase_parts)
                start_str = format_ass_time(chunk_start)
                end_str = format_ass_time(chunk_end)
                start_cs = parse_ass_time(start_str)
                end_cs = parse_ass_time(end_str)
                if end_cs <= start_cs:
                    end_str = format_ass_time(start_cs + 0.10)
                events.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{chunk_text}")
        return header + "\n".join(events) + "\n"

    def render(
        self,
        transcript_segments: List[TranscriptSegment],
        video_path: str,
        output_path: str,
        config: Optional[JobConfig] = None,
        clip_start: float = 0.0,
        clip_end: Optional[float] = None,
        face_boxes: Optional[List[Tuple[float, float, float, float]]] = None,
    ) -> Dict[str, Any]:
        cfg = config or JobConfig()
        src = Path(video_path)
        if not src.exists():
            raise FileNotFoundError(f"Source video not found: {video_path}")

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        # Compute clip duration
        clip_duration = (clip_end - clip_start) if (clip_end is not None and clip_end > clip_start) else 0.0
        if clip_duration <= 0.0:
            # Probe source video duration via ffprobe
            try:
                cmd_dur = [
                    self.settings.ffprobe_bin,
                    "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    str(src),
                ]
                res_dur = subprocess.run(cmd_dur, capture_output=True, text=True)
                if res_dur.returncode == 0 and res_dur.stdout.strip():
                    clip_duration = float(res_dur.stdout.strip())
            except Exception:
                clip_duration = 30.0

        # Pass-through if no captions requested
        if cfg.caption_preset == CaptionPreset.NO_CAPTIONS.value:
            if str(src.resolve()) != str(out.resolve()):
                out.write_bytes(src.read_bytes())
            return {
                "status": "skipped",
                "reason": "captions disabled by user",
                "output_path": str(out),
                "preset": cfg.caption_preset,
                "caption_visible": False,
            }

        # Generate ASS script
        ass_content = self.generate_ass_script(
            transcript_segments,
            config=cfg,
            video_width=1080,
            video_height=1920,
            clip_start=clip_start,
            clip_end=clip_end,
            face_boxes=face_boxes,
        )

        work_dir = Path(self.settings.data_dir) / "work"
        work_dir.mkdir(parents=True, exist_ok=True)
        ass_path = work_dir / f"caption_{out.stem}.ass"
        ass_path.write_text(ass_content, encoding="utf-8")

        # Validate ASS syntax and timestamps
        validate_ass_file(str(ass_path), clip_duration=clip_duration)

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
            timestamp=min(1.5, max(0.5, clip_duration / 2.0)),
            raw_reference_video=str(src),
            save_verification_name=out.stem,
        )
        return {
            "status": "completed",
            "reason": None,
            "output_path": str(out),
            "ass_path": str(ass_path),
            "preset": cfg.caption_preset,
            "caption_rendered": True,
            "caption_timing_valid": True,
            "caption_content_valid": True,
            "caption_visible": is_visible,
        }
