import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.job_service import JobService
from app.services.scan_pipeline import ScanPipeline

logger = logging.getLogger(__name__)


@dataclass
class JobTask:
    job_id: int
    zip_path: Path


class JobQueue:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.queue: asyncio.Queue[JobTask] = asyncio.Queue()
        self.pipeline = ScanPipeline()

    async def enqueue(self, task: JobTask) -> None:
        await self.queue.put(task)

    async def run_forever(self) -> None:
        while True:
            task = await self.queue.get()
            await self._handle(task)
            self.queue.task_done()

    async def _handle(self, task: JobTask) -> None:
        async with SessionLocal() as session:
            job = await JobService.by_id(session, task.job_id)
            if not job:
                logger.error("Missing job for task", extra={"job_id": task.job_id})
                return
            await JobService.set_running(session, job)
            extract_path = self.settings.extraction_dir / f"job_{task.job_id}"
            try:
                total, cached, duration = await self.pipeline.execute(
                    session,
                    task.job_id,
                    task.zip_path,
                    extract_path,
                    self.settings.max_llm_concurrency,
                )
                await JobService.complete(session, job, total, cached, duration, failed=False)
            except Exception:
                logger.exception("Job failed", extra={"job_id": task.job_id})
                await JobService.complete(session, job, 0, 0, 0.0, failed=True)


job_queue = JobQueue()
