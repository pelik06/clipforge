from typing import List
from services.editor.models import AudioConfig, CropConfig, EditorState

MIN_CLIP_DURATION = 3.0


class EditorValidator:
    """Enforces strict invariants on EditorState before operations, persistence, and rendering."""

    @staticmethod
    def validate_timeline(state: EditorState) -> List[str]:
        errors = []
        if state.source_start < 0.0:
            errors.append(f"Invalid source_start {state.source_start:.2f}: must be non-negative")
        if state.source_end <= state.source_start:
            errors.append(f"Invalid timeline range: start {state.source_start:.2f} >= end {state.source_end:.2f}")
        if state.source_duration > 0.0 and state.source_end > (state.source_duration + 0.2):
            errors.append(f"source_end {state.source_end:.2f} exceeds source_duration {state.source_duration:.2f}")
        dur = state.clip_duration
        if dur < MIN_CLIP_DURATION:
            errors.append(f"Clip duration {dur:.2f}s is less than minimum allowed ({MIN_CLIP_DURATION}s)")
        return errors

    @staticmethod
    def validate_captions(state: EditorState) -> List[str]:
        errors = []
        clip_dur = state.clip_duration
        sorted_caps = sorted(state.captions, key=lambda c: c.start)

        for i, cap in enumerate(sorted_caps):
            if cap.start < 0.0:
                errors.append(f"Caption {cap.id} start {cap.start} cannot be negative")
            if cap.end <= cap.start:
                errors.append(f"Caption {cap.id} has non-positive duration (start={cap.start}, end={cap.end})")
            if clip_dur > 0 and cap.end > (clip_dur + 0.15):
                errors.append(f"Caption {cap.id} end {cap.end:.2f}s exceeds clip duration {clip_dur:.2f}s")
            if not cap.text or not cap.text.strip():
                errors.append(f"Caption {cap.id} text cannot be empty")

            # Check overlap with previous
            if i > 0:
                prev = sorted_caps[i - 1]
                if cap.start < (prev.end - 0.01):
                    errors.append(f"Caption overlap detected between '{prev.id}' (end={prev.end}) and '{cap.id}' (start={cap.start})")

        return errors

    @staticmethod
    def validate_crop(crop: CropConfig) -> List[str]:
        errors = []
        if not (0.0 <= crop.x <= 1.0):
            errors.append(f"Crop x {crop.x} out of normalized bounds [0.0, 1.0]")
        if not (0.0 <= crop.y <= 1.0):
            errors.append(f"Crop y {crop.y} out of normalized bounds [0.0, 1.0]")
        if not (0.0 < crop.width <= 1.0):
            errors.append(f"Crop width {crop.width} out of normalized bounds (0.0, 1.0]")
        if not (0.0 < crop.height <= 1.0):
            errors.append(f"Crop height {crop.height} out of normalized bounds (0.0, 1.0]")
        if crop.scale <= 0.0:
            errors.append(f"Crop scale {crop.scale} must be strictly positive")
        if crop.mode not in {"auto", "manual"}:
            errors.append(f"Invalid crop mode '{crop.mode}'; must be 'auto' or 'manual'")
        return errors

    @staticmethod
    def validate_audio(audio: AudioConfig) -> List[str]:
        errors = []
        if not (0.0 <= audio.volume <= 2.0):
            errors.append(f"Audio volume {audio.volume} out of range [0.0, 2.0]")
        return errors

    @staticmethod
    def validate_layout(layout: str) -> List[str]:
        errors = []
        if layout not in {"AUTO", "TRACK", "SPLIT"}:
            errors.append(f"Invalid layout mode '{layout}'; must be AUTO, TRACK, or SPLIT")
        return errors

    @classmethod
    def validate_all(cls, state: EditorState):
        all_errors = []
        all_errors.extend(cls.validate_timeline(state))
        all_errors.extend(cls.validate_captions(state))
        all_errors.extend(cls.validate_crop(state.crop))
        all_errors.extend(cls.validate_audio(state.audio))
        all_errors.extend(cls.validate_layout(state.layout))

        if all_errors:
            raise ValueError(f"EditorState validation failed: {'; '.join(all_errors)}")
