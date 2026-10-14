from typing import Optional
from services.render.models import RenderJobState


class RenderProgressTracker:
    """Calculates strictly monotonic 0 -> 100 progress tied to concrete render pipeline stages."""

    STAGE_RANGES = {
        RenderJobState.QUEUED: (0.0, 0.0),
        RenderJobState.PREPARING: (0.0, 5.0),
        RenderJobState.RENDERING: (5.0, 90.0),
        RenderJobState.VALIDATING: (90.0, 99.0),
        RenderJobState.COMPLETED: (100.0, 100.0),
        RenderJobState.FAILED: (0.0, 100.0),
        RenderJobState.CANCELLED: (0.0, 100.0),
        RenderJobState.RETRYING: (0.0, 5.0),
    }

    def __init__(self, initial_progress: float = 0.0):
        self._current_progress = float(initial_progress)

    @property
    def progress(self) -> float:
        return self._current_progress

    def update(self, state: RenderJobState, fraction: float = 0.0) -> float:
        """Update progress within stage range, ensuring monotonic non-decreasing output."""
        low, high = self.STAGE_RANGES.get(state, (0.0, 100.0))
        computed = low + max(0.0, min(1.0, fraction)) * (high - low)
        if computed > self._current_progress:
            self._current_progress = round(computed, 1)
        return self._current_progress

    def complete(self) -> float:
        self._current_progress = 100.0
        return 100.0
