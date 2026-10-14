from typing import Any, Dict, List, Optional
import uuid

from services.editor.models import CaptionSegment


class CaptionEditorHelper:
    """Provides pure caption manipulation utilities: split, merge, text update, add, delete."""

    @staticmethod
    def update_text(captions: List[CaptionSegment], caption_id: str, new_text: str) -> List[CaptionSegment]:
        updated = []
        for c in captions:
            if c.id == caption_id:
                updated.append(
                    CaptionSegment(
                        id=c.id,
                        start=c.start,
                        end=c.end,
                        text=new_text.strip(),
                        style=dict(c.style),
                        emphasis=c.emphasis,
                    )
                )
            else:
                updated.append(c)
        return updated

    @staticmethod
    def update_timing(
        captions: List[CaptionSegment],
        caption_id: str,
        new_start: float,
        new_end: float,
    ) -> List[CaptionSegment]:
        updated = []
        for c in captions:
            if c.id == caption_id:
                updated.append(
                    CaptionSegment(
                        id=c.id,
                        start=round(new_start, 3),
                        end=round(new_end, 3),
                        text=c.text,
                        style=dict(c.style),
                        emphasis=c.emphasis,
                    )
                )
            else:
                updated.append(c)
        # Sort by start time
        updated.sort(key=lambda x: x.start)
        return updated

    @staticmethod
    def add_caption(
        captions: List[CaptionSegment],
        start: float,
        end: float,
        text: str,
        style: Optional[Dict[str, Any]] = None,
        emphasis: bool = False,
    ) -> List[CaptionSegment]:
        c_id = f"cap_{uuid.uuid4().hex[:6]}"
        new_cap = CaptionSegment(
            id=c_id,
            start=round(start, 3),
            end=round(end, 3),
            text=text.strip(),
            style=dict(style or {}),
            emphasis=emphasis,
        )
        updated = list(captions) + [new_cap]
        updated.sort(key=lambda x: x.start)
        return updated

    @staticmethod
    def delete_caption(captions: List[CaptionSegment], caption_id: str) -> List[CaptionSegment]:
        return [c for c in captions if c.id != caption_id]

    @staticmethod
    def split_caption(
        captions: List[CaptionSegment],
        caption_id: str,
        split_time: float,
    ) -> List[CaptionSegment]:
        updated = []
        for c in captions:
            if c.id == caption_id:
                if not (c.start < split_time < c.end):
                    raise ValueError(f"Split time {split_time:.2f}s must fall between caption start {c.start:.2f}s and end {c.end:.2f}s")

                words = c.text.split()
                if len(words) >= 2:
                    mid = len(words) // 2
                    text_1 = " ".join(words[:mid])
                    text_2 = " ".join(words[mid:])
                else:
                    text_1 = c.text
                    text_2 = c.text

                c1 = CaptionSegment(
                    id=f"{c.id}_a",
                    start=c.start,
                    end=round(split_time, 3),
                    text=text_1,
                    style=dict(c.style),
                    emphasis=c.emphasis,
                )
                c2 = CaptionSegment(
                    id=f"{c.id}_b",
                    start=round(split_time, 3),
                    end=c.end,
                    text=text_2,
                    style=dict(c.style),
                    emphasis=c.emphasis,
                )
                updated.extend([c1, c2])
            else:
                updated.append(c)

        updated.sort(key=lambda x: x.start)
        return updated

    @staticmethod
    def merge_captions(
        captions: List[CaptionSegment],
        caption_id_1: str,
        caption_id_2: str,
    ) -> List[CaptionSegment]:
        c1 = next((c for c in captions if c.id == caption_id_1), None)
        c2 = next((c for c in captions if c.id == caption_id_2), None)
        if not c1 or not c2:
            raise ValueError(f"Cannot merge captions: {caption_id_1} or {caption_id_2} not found")

        merged = CaptionSegment(
            id=f"{c1.id}_{c2.id}",
            start=min(c1.start, c2.start),
            end=max(c1.end, c2.end),
            text=f"{c1.text} {c2.text}".strip(),
            style=dict(c1.style),
            emphasis=c1.emphasis or c2.emphasis,
        )

        remaining = [c for c in captions if c.id not in {caption_id_1, caption_id_2}]
        remaining.append(merged)
        remaining.sort(key=lambda x: x.start)
        return remaining
