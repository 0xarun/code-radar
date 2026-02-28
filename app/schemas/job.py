from datetime import datetime

from pydantic import BaseModel

from app.models.job import JobStatus


class JobResponse(BaseModel):
    id: int
    status: JobStatus
    created_at: datetime
    completed_at: datetime | None = None
    total_findings: int
    cached_hits: int
    duration: float | None = None

    class Config:
        from_attributes = True
