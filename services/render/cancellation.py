from pathlib import Path
import subprocess
from typing import Dict, Optional


class RenderCancellationManager:
    """Manages cooperative and hard cancellation of active render jobs and cleans up partial files."""

    def __init__(self):
        self._active_processes: Dict[str, subprocess.Popen] = {}
        self._cancelled_jobs: set = set()

    def register_process(self, job_id: str, proc: subprocess.Popen):
        self._active_processes[job_id] = proc

    def unregister_process(self, job_id: str):
        self._active_processes.pop(job_id, None)

    def is_cancelled(self, job_id: str) -> bool:
        return job_id in self._cancelled_jobs

    def cancel_job(self, job_id: str, partial_output_path: Optional[str] = None) -> bool:
        self._cancelled_jobs.add(job_id)

        # 1. Terminate running FFmpeg subprocess if active
        proc = self._active_processes.get(job_id)
        if proc:
            try:
                proc.terminate()
                proc.wait(timeout=2.0)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
            finally:
                self._active_processes.pop(job_id, None)

        # 2. Clean up partial/corrupt artifact file
        if partial_output_path:
            p = Path(partial_output_path)
            if p.exists() and p.is_file():
                try:
                    p.unlink()
                except Exception:
                    pass

        return True
