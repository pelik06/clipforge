import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class FramingMode(str, Enum):
    TRACK = "track"
    AUTO_FOLLOW_SPEAKER = "auto_follow_speaker"
    GENERAL = "general"
    CENTER_CROP = "center_crop"
    SPLIT = "split"
    MANUAL_POSITION = "manual_position"


class CaptionPreset(str, Enum):
    CLEAN = "clean"
    CREATOR_BOLD = "creator_bold"
    KARAOKE = "karaoke"
    VIRAL_BEAST = "viral_beast"
    NEON_CYAN = "neon_cyan"
    MINIMAL = "minimal"
    NO_CAPTIONS = "no_captions"
    HYPERFRAMES = "hyperframes"

class CaptionLanguage(str, Enum):
    AUTO = "auto"
    ID = "id"
    EN = "en"


class CaptionSize(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    EXTRA_LARGE = "extra_large"


class CaptionPosition(str, Enum):
    BOTTOM_SAFE = "bottom_safe"
    CENTER = "center"
    TOP_SAFE = "top_safe"


class MomentDetectionMode(str, Enum):
    AI = "ai"
    HEURISTIC = "heuristic"


class MomentDetectionProvider(str, Enum):
    GEMINI = "gemini"
    OPENAI = "openai"
    LOCAL = "local"
    HEURISTIC = "heuristic"


HEX_COLOR_PATTERN = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def validate_hex_color(color: str, field_name: str = "color") -> str:
    clean = (color or "").strip()
    if not HEX_COLOR_PATTERN.match(clean):
        raise ValueError(f"Invalid {field_name} format: '{color}'. Must be hex format like #FFFFFF or #FFFF00.")
    return clean.upper()


@dataclass
class JobConfig:
    framing_mode: str = FramingMode.AUTO_FOLLOW_SPEAKER.value
    caption_preset: str = CaptionPreset.CLEAN.value
    caption_language: str = CaptionLanguage.AUTO.value
    caption_size: str = CaptionSize.MEDIUM.value
    caption_position: str = CaptionPosition.BOTTOM_SAFE.value
    caption_text_color: str = "#FFFFFF"
    caption_highlight_color: str = "#FFFF00"
    caption_word_highlight: bool = False
    caption_words_per_group: int = 4
    scene_cut_snap: bool = True
    moment_detection_mode: str = MomentDetectionMode.HEURISTIC.value
    moment_detection_provider: str = MomentDetectionProvider.HEURISTIC.value
    min_clips: int = 1
    max_clips: int = 5
    min_clip_duration: float = 45.0
    max_clip_duration: float = 120.0
    enable_scene_detection: bool = True
    moment_threshold: float = 0.45

    def validate(self) -> None:
        if self.framing_mode not in [m.value for m in FramingMode]:
            raise ValueError(f"Invalid framing_mode: '{self.framing_mode}'. Allowed: {[m.value for m in FramingMode]}")

        if self.caption_preset not in [p.value for p in CaptionPreset]:
            raise ValueError(f"Invalid caption_preset: '{self.caption_preset}'. Allowed: {[p.value for p in CaptionPreset]}")

        if self.caption_language not in [l.value for l in CaptionLanguage]:
            raise ValueError(f"Invalid caption_language: '{self.caption_language}'. Allowed: {[l.value for l in CaptionLanguage]}")

        if self.caption_size not in [s.value for s in CaptionSize]:
            raise ValueError(f"Invalid caption_size: '{self.caption_size}'. Allowed: {[s.value for s in CaptionSize]}")

        if self.caption_position not in [pos.value for pos in CaptionPosition]:
            raise ValueError(f"Invalid caption_position: '{self.caption_position}'. Allowed: {[pos.value for pos in CaptionPosition]}")

        self.caption_text_color = validate_hex_color(self.caption_text_color, "caption_text_color")
        self.caption_highlight_color = validate_hex_color(self.caption_highlight_color, "caption_highlight_color")

        if self.caption_preset in (CaptionPreset.KARAOKE.value, CaptionPreset.VIRAL_BEAST.value):
            self.caption_word_highlight = True
        if self.moment_detection_mode not in [m.value for m in MomentDetectionMode]:
            raise ValueError(f"Invalid moment_detection_mode: '{self.moment_detection_mode}'. Allowed: {[m.value for m in MomentDetectionMode]}")

        if self.moment_detection_provider not in [p.value for p in MomentDetectionProvider]:
            raise ValueError(f"Invalid moment_detection_provider: '{self.moment_detection_provider}'. Allowed: {[p.value for p in MomentDetectionProvider]}")

        if not (1 <= int(self.max_clips) <= 15):
            raise ValueError(f"max_clips must be between 1 and 15, got {self.max_clips}")

        if int(self.min_clips) < 1:
            raise ValueError(f"min_clips must be at least 1, got {self.min_clips}")

        if int(self.caption_words_per_group) < 1:
            raise ValueError(f"caption_words_per_group must be at least 1, got {self.caption_words_per_group}")

        if float(self.min_clip_duration) < 3.0:
            raise ValueError(f"min_clip_duration must be at least 3.0 seconds, got {self.min_clip_duration}")

        if float(self.max_clip_duration) < float(self.min_clip_duration):
            raise ValueError(f"max_clip_duration ({self.max_clip_duration}) cannot be smaller than min_clip_duration ({self.min_clip_duration})")
