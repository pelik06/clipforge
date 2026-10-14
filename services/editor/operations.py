import datetime
from typing import Any, Dict, List, Optional

from services.editor.captions import CaptionEditorHelper
from services.editor.models import AudioConfig, CaptionSegment, CropConfig, EditorState
from services.editor.timeline import TimelineHelper
from services.editor.validation import EditorValidator


class EditorOperations:
    """Executes state-transforming operations with strict validation, version incrementing, and override tracking."""

    @staticmethod
    def _prepare_next_state(state: EditorState) -> EditorState:
        nxt = state.clone()
        nxt.editor_version += 1
        nxt.updated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return nxt

    @classmethod
    def trim(cls, state: EditorState, new_start: float, new_end: float) -> EditorState:
        nxt = cls._prepare_next_state(state)
        old_start = nxt.source_start
        nxt.source_start = round(new_start, 3)
        nxt.source_end = round(new_end, 3)

        # Rebase and prune caption segments to fit the new trim range
        nxt.captions = TimelineHelper.rebase_captions_after_trim(
            nxt.captions,
            old_source_start=old_start,
            new_source_start=nxt.source_start,
            new_source_end=nxt.source_end,
        )

        nxt.user_overrides["trim"] = {"start": nxt.source_start, "end": nxt.source_end}
        EditorValidator.validate_all(nxt)
        return nxt

    @classmethod
    def edit_caption_text(cls, state: EditorState, caption_id: str, new_text: str) -> EditorState:
        nxt = cls._prepare_next_state(state)
        nxt.captions = CaptionEditorHelper.update_text(nxt.captions, caption_id, new_text)
        nxt.user_overrides.setdefault("captions_edited", []).append(caption_id)
        EditorValidator.validate_all(nxt)
        return nxt

    @classmethod
    def edit_caption_timing(cls, state: EditorState, caption_id: str, new_start: float, new_end: float) -> EditorState:
        nxt = cls._prepare_next_state(state)
        nxt.captions = CaptionEditorHelper.update_timing(nxt.captions, caption_id, new_start, new_end)
        nxt.user_overrides.setdefault("captions_edited", []).append(caption_id)
        EditorValidator.validate_all(nxt)
        return nxt

    @classmethod
    def add_caption(
        cls,
        state: EditorState,
        start: float,
        end: float,
        text: str,
        style: Optional[Dict[str, Any]] = None,
        emphasis: bool = False,
    ) -> EditorState:
        nxt = cls._prepare_next_state(state)
        nxt.captions = CaptionEditorHelper.add_caption(nxt.captions, start, end, text, style, emphasis)
        nxt.user_overrides["captions_custom_added"] = True
        EditorValidator.validate_all(nxt)
        return nxt

    @classmethod
    def delete_caption(cls, state: EditorState, caption_id: str) -> EditorState:
        nxt = cls._prepare_next_state(state)
        nxt.captions = CaptionEditorHelper.delete_caption(nxt.captions, caption_id)
        nxt.user_overrides.setdefault("captions_deleted", []).append(caption_id)
        EditorValidator.validate_all(nxt)
        return nxt

    @classmethod
    def split_caption(cls, state: EditorState, caption_id: str, split_time: float) -> EditorState:
        nxt = cls._prepare_next_state(state)
        nxt.captions = CaptionEditorHelper.split_caption(nxt.captions, caption_id, split_time)
        nxt.user_overrides.setdefault("captions_split", []).append(caption_id)
        EditorValidator.validate_all(nxt)
        return nxt

    @classmethod
    def merge_captions(cls, state: EditorState, caption_id_1: str, caption_id_2: str) -> EditorState:
        nxt = cls._prepare_next_state(state)
        nxt.captions = CaptionEditorHelper.merge_captions(nxt.captions, caption_id_1, caption_id_2)
        nxt.user_overrides.setdefault("captions_merged", []).append(f"{caption_id_1}+{caption_id_2}")
        EditorValidator.validate_all(nxt)
        return nxt

    @classmethod
    def set_crop(
        cls,
        state: EditorState,
        x: float,
        y: float,
        width: float,
        height: float,
        scale: float = 1.0,
        mode: str = "manual",
    ) -> EditorState:
        nxt = cls._prepare_next_state(state)
        nxt.crop = CropConfig(x=x, y=y, width=width, height=height, scale=scale, mode=mode)
        nxt.user_overrides["crop"] = nxt.crop.to_dict()
        EditorValidator.validate_all(nxt)
        return nxt

    @classmethod
    def set_layout(cls, state: EditorState, layout_mode: str) -> EditorState:
        nxt = cls._prepare_next_state(state)
        nxt.layout = layout_mode.upper()
        nxt.user_overrides["layout"] = nxt.layout
        EditorValidator.validate_all(nxt)
        return nxt

    @classmethod
    def set_audio(
        cls,
        state: EditorState,
        volume: float = 1.0,
        mute: bool = False,
        fade_in: float = 0.0,
        fade_out: float = 0.0,
    ) -> EditorState:
        nxt = cls._prepare_next_state(state)
        nxt.audio = AudioConfig(volume=volume, mute=mute, fade_in=fade_in, fade_out=fade_out)
        nxt.user_overrides["audio"] = nxt.audio.to_dict()
        EditorValidator.validate_all(nxt)
        return nxt
