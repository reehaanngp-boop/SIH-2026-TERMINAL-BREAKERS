"""In-memory job queue for long-running analyses.

A small ``ThreadPoolExecutor`` runs at most ``max_concurrent_jobs`` analyses at
once; clients poll ``GET /api/v1/analyze/jobs/{id}`` for progress. Completed
results are kept until the process exits, so the queue is intentionally
ephemeral — durable history lives in the SQLite ``scans`` table.

Contract: a submitted callable receives a ``progress(percent, message)``
callback as its only argument.
"""

from __future__ import annotations

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

ProgressCallback = Callable[[float, str | None], None]


class Job:
    def __init__(self, job_id: str, description: str = ""):
        self.job_id = job_id
        self.description = description
        self.state = "queued"  # queued | running | completed | failed
        self.progress = 0.0
        self.message: str | None = None
        self.result: Any = None
        self.error: str | None = None
        self._lock = threading.Lock()

    def set_progress(self, progress: float, message: str | None = None) -> None:
        with self._lock:
            self.progress = max(0.0, min(1.0, progress))
            if message:
                self.message = message

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "job_id": self.job_id,
                "status": self.state,
                "progress": self.progress,
                "message": self.message,
                "error": self.error,
            }


class JobManager:
    def __init__(self, max_workers: int = 2):
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="analysis")
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def submit(self, fn: Callable[[ProgressCallback], Any], description: str = "") -> str:
        """Schedule ``fn(progress_callback)``. Returns the new job id."""
        job_id = uuid.uuid4().hex
        job = Job(job_id, description)
        with self._lock:
            self._jobs[job_id] = job
        self._executor.submit(self._run, job, fn)
        return job_id

    def _run(self, job: Job, fn: Callable[[ProgressCallback], Any]) -> None:
        job.state = "running"
        job.set_progress(0.05, "started")
        try:
            result = fn(job.set_progress)
            job.result = result
            job.state = "completed"
            job.set_progress(1.0, "completed")
        except Exception as exc:  # noqa: BLE001 - surface any failure to the client
            job.error = str(exc)
            job.state = "failed"

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)


def get_job_manager() -> JobManager:
    """Module-level singleton so routes share one queue."""
    global _JOB_MANAGER
    if _JOB_MANAGER is None:
        _JOB_MANAGER = JobManager()
    return _JOB_MANAGER


_JOB_MANAGER: JobManager | None = None
