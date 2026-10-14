from typing import List
from services.editor.models import CaptionSegment


class TimelineHelper:
    """Provides pure timeline utilities for trimming, duration bounds, and caption rebasing."""

    @staticmethod
    def rebase_captions_after_trim(
        captions: List[CaptionSegment],
        old_source_start: float,
        new_source_start: float,
        new_source_end: float,
    ) -> List[CaptionSegment]:
        rebased: List[CaptionSegment] = []

        for cap in captions:
            # Map back to absolute source timeline
            abs_start = old_source_start + cap.start
            abs_end = old_source_start + cap.end

            # Prune segments completely outside the new trim range
            if abs_end <= new_source_start or abs_start >= new_source_end:
                continue

            # Clamp to new trim boundaries
            clamped_abs_start = max(new_source_start, abs_start)
            clamped_abs_end = min(new_source_end, abs_end)

            # Rebase relative to new_source_start
            rel_start = max(0.0, round(clamped_abs_start - new_source_start, 3))
            rel_end = max(rel_start + 0.05, round(clamped_abs_end - new_source_start, 3))

            rebased.append(
                CaptionSegment(
                    id=cap.id,
                    start=rel_start,
                    end=rel_end,
                    text=cap.text,
                    style=dict(cap.style),
                    emphasis=cap.emphasis,
                )
            )

        return rebased
