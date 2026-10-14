import heapq
import threading
from typing import Any, Dict, List, Optional
from services.render.models import RenderJob, RenderJobState


class RenderQueue:
    """In-memory priority queue for render jobs backed by thread-safe synchronization."""

    def __init__(self):
        self._lock = threading.Lock()
        self._items: List[RenderJob] = []

    def enqueue(self, job: RenderJob) -> RenderJob:
        with self._lock:
            job.status = RenderJobState.QUEUED
            job.stage = "Queued in render queue"
            job.progress = 0.0
            self._items.append(job)
            # Sort by priority DESC, created_at ASC
            self._items.sort(key=lambda j: (-j.priority, j.created_at or ""))
            return job

    def dequeue(self) -> Optional[RenderJob]:
        with self._lock:
            # Pop highest priority queued job
            for i, job in enumerate(self._items):
                if job.status in {RenderJobState.QUEUED, RenderJobState.RETRYING}:
                    return self._items.pop(i)
            return None

    def peek(self) -> Optional[RenderJob]:
        with self._lock:
            for job in self._items:
                if job.status in {RenderJobState.QUEUED, RenderJobState.RETRYING}:
                    return job
            return None

    def cancel(self, job_id: str) -> bool:
        with self._lock:
            for job in self._items:
                if job.id == job_id:
                    job.status = RenderJobState.CANCELLED
                    job.stage = "Cancelled before execution"
                    return True
            return False

    def size(self) -> int:
        with self._lock:
            return sum(1 for j in self._items if j.status in {RenderJobState.QUEUED, RenderJobState.RETRYING})

    def list_all(self) -> List[RenderJob]:
        with self._lock:
            return list(self._items)
