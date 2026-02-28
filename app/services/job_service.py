from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job, JobStatus


class JobService:
    @staticmethod
    async def create(session: AsyncSession) -> Job:
        job = Job(status=JobStatus.PENDING)
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return job

    @staticmethod
    async def set_running(session: AsyncSession, job: Job) -> None:
        job.status = JobStatus.RUNNING
        await session.commit()

    @staticmethod
    async def complete(
        session: AsyncSession,
        job: Job,
        total_findings: int,
        cached_hits: int,
        duration: float,
        failed: bool = False,
    ) -> None:
        job.status = JobStatus.FAILED if failed else JobStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        job.total_findings = total_findings
        job.cached_hits = cached_hits
        job.duration = duration
        await session.commit()

    @staticmethod
    async def by_id(session: AsyncSession, job_id: int) -> Job | None:
        result = await session.execute(select(Job).where(Job.id == job_id))
        return result.scalar_one_or_none()
