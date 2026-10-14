from typing import Dict
from services.render.models import ExportPresetConfig, RenderPreset

PRESETS: Dict[str, ExportPresetConfig] = {
    RenderPreset.TIKTOK.value: ExportPresetConfig(
        name="tiktok",
        width=1080,
        height=1920,
        fps=30,
        video_bitrate="4500k",
        audio_bitrate="192k",
        crf=20,
        ffmpeg_preset="fast",
        audio_normalize=True,
    ),
    RenderPreset.HIGH_QUALITY.value: ExportPresetConfig(
        name="high_quality",
        width=1080,
        height=1920,
        fps=30,
        video_bitrate="8000k",
        audio_bitrate="256k",
        crf=18,
        ffmpeg_preset="medium",
        audio_normalize=True,
    ),
    RenderPreset.DRAFT.value: ExportPresetConfig(
        name="draft",
        width=720,
        height=1280,
        fps=30,
        video_bitrate="2000k",
        audio_bitrate="128k",
        crf=24,
        ffmpeg_preset="veryfast",
        audio_normalize=False,
    ),
    RenderPreset.PREVIEW.value: ExportPresetConfig(
        name="preview",
        width=720,
        height=1280,
        fps=24,
        video_bitrate="1200k",
        audio_bitrate="96k",
        crf=28,
        ffmpeg_preset="ultrafast",
        audio_normalize=False,
    ),
}


def get_preset_config(preset_name: str) -> ExportPresetConfig:
    key = (preset_name or "tiktok").lower().strip()
    if key not in PRESETS:
        raise ValueError(f"Unknown export preset '{preset_name}'. Allowed presets: {list(PRESETS.keys())}")
    cfg = PRESETS[key]
    cfg.validate()
    return cfg
