import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from core.storage import (
    delete_render_job,
    get_render_job,
    list_render_jobs,
    save_render_job,
)
from services.render.cancellation import RenderCancellationManager
from services.render.models import RenderJob, RenderJobState
from services.render.queue import RenderQueue
from services.render.recovery import recover_stale_jobs
from services.render.worker import RenderWorker


class RenderJobManager:
    """Central orchestrator managing job lifecycles, prioritization, worker concurrency, and recovery."""

    def __init__(self, concurrency: int = 1, renders_dir: str = "data/renders"):
        self.concurrency = max(1, concurrency)
        self.queue = RenderQueue()
        self.cancellation_manager = RenderCancellationManager()
        self.worker = RenderWorker(
            cancellation_manager=self.cancellation_manager,
            renders_dir=renders_dir,
        )
        # Automatic crash recovery on initialization
        self.recover_on_startup()

    def recover_on_startup(self) -> List[Dict[str, Any]]:
        return recover_stale_jobs()

    def submit_job(
        self,
        clip_id: str,
        source_id: str,
        preset: str = "tiktok",
        render_type: str = "final",
        priority: int = 10,
        config: Optional[Dict[str, Any]] = None,
    ) -> RenderJob:
        from services.render.presets import get_preset_config
        get_preset_config(preset)
        j_id = f"rjob_{uuid.uuid4().hex[:8]}"
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        job = RenderJob(
            id=j_id,
            clip_id=clip_id,
            source_id=source_id,
            status=RenderJobState.QUEUED,
            stage="Queued in render queue",
            progress=0.0,
            preset=preset,
            render_type=render_type,
            priority=priority,
            config=config or {},
            created_at=now,
        )
        save_render_job(job.to_dict())
        self.queue.enqueue(job)
        return job

    def cancel_job(self, job_id: str) -> bool:
        job_data = get_render_job(job_id)
        if not job_data:
            return False

        # Queue cancellation
        self.queue.cancel(job_id)

        # Worker subprocess cancellation and partial cleanup
        out_path = job_data.get("output_path")
        self.cancellation_manager.cancel_job(job_id, partial_output_path=out_path)

        job_data["status"] = RenderJobState.CANCELLED.value
        job_data["stage"] = "Cancelled by operator"
        save_render_job(job_data)
        return True

    def retry_job(self, job_id: str) -> Optional[RenderJob]:
        job_data = get_render_job(job_id)
        if not job_data:
            return None

        job = RenderJob(
            id=job_data["id"],
            clip_id=job_data["clip_id"],
            source_id=job_data["source_id"],
            status=RenderJobState.QUEUED,
            stage="Queued for retry",
            progress=0.0,
            preset=job_data["preset"],
            render_type=job_data["render_type"],
            priority=job_data["priority"] + 2, # Priority boost for retries
            config=job_data.get("config", {}),
            created_at=job_data["created_at"],
            retry_count=job_data.get("retry_count", 0) + 1,
        )
        save_render_job(job.to_dict())
        self.queue.enqueue(job)
        return job

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return get_render_job(job_id)

    def list_jobs(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        return list_render_jobs(status=status)

    def process_queue_sync(self, max_jobs: Optional[int] = None) -> List[RenderJob]:
        """Synchronously execute queued jobs up to max_jobs or until queue empty."""
        processed = []
        count = 0

        while True:
            if max_jobs is not None and count >= max_jobs:
                break

            job = self.queue.dequeue()
            if not job:
                break

            # Skip if cancelled while in queue
            if self.cancellation_manager.is_cancelled(job.id):
                job.status = RenderJobState.CANCELLED
                job.stage = "Cancelled before execution"
                save_render_job(job.to_dict())
                processed.append(job)
                count += 1
                continue

            res_job = self.worker.execute_job(job)
            processed.append(res_job)
            count += 1

        return processed
