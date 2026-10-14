from pathlib import Path
from typing import Dict, List, Optional
from core.storage import list_render_jobs, save_render_job
from services.render.models import RenderJobState

STALE_STATES = {
    RenderJobState.PREPARING.value,
    RenderJobState.RENDERING.value,
    RenderJobState.VALIDATING.value,
}


def recover_stale_jobs(db_path: Optional[Path] = None, max_retries: int = 2) -> List[Dict[str, Any]]:
    """Scan and recover orphaned render jobs that were interrupted by an ungraceful server/worker shutdown."""
    stale_jobs = []
    all_jobs = list_render_jobs(db_path=db_path)

    for job in all_jobs:
        if job.get("status") in STALE_STATES:
            retries = int(job.get("retry_count", 0))
            if retries < max_retries:
                job["status"] = RenderJobState.RETRYING.value
                job["stage"] = "Recovered from server crash; queued for retry"
                job["retry_count"] = retries + 1
            else:
                job["status"] = RenderJobState.FAILED.value
                job["stage"] = "Render failed: interrupted by ungraceful worker termination"
                job["error_message"] = "Worker process terminated during rendering without retries remaining"
            save_render_job(job, db_path=db_path)
            stale_jobs.append(job)

    return stale_jobs
