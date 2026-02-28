import json
import logging
import shutil
import subprocess
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session_dep
from app.core.config import get_settings
from app.db.redis import redis_client
from app.models.finding import Finding
from app.models.job import Job
from app.schemas.health import HealthStatus
from app.schemas.job import JobResponse
from app.schemas.upload import UploadResponse
from app.services.job_service import JobService
from app.workers.job_queue import JobTask, job_queue

router = APIRouter()
settings = get_settings()
logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory="app/templates")


@router.post("/upload", response_model=UploadResponse)
async def upload_repository(file: UploadFile = File(...), session: AsyncSession = Depends(db_session_dep)) -> UploadResponse:
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only ZIP files are allowed")

    job = await JobService.create(session)
    zip_path = settings.upload_dir / f"job_{job.id}.zip"
    with zip_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    await job_queue.enqueue(JobTask(job_id=job.id, zip_path=zip_path))
    return UploadResponse(job_id=job.id, status="queued", message="Repository uploaded and queued")


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def job_status(job_id: int, session: AsyncSession = Depends(db_session_dep)) -> JobResponse:
    job = await JobService.by_id(session, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse.model_validate(job)


@router.get("/health", response_model=HealthStatus)
async def health(session: AsyncSession = Depends(db_session_dep)) -> HealthStatus:
    db = "ok"
    redis = "ok"
    ollama = "ok"
    semgrep = "ok"

    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        db = "error"

    try:
        await redis_client.ping()
    except Exception:
        redis = "error"

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{settings.ollama_url}/api/tags")
            response.raise_for_status()
    except Exception:
        ollama = "error"

    try:
        result = subprocess.run([settings.semgrep_bin, "--version"], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            semgrep = "error"
    except Exception:
        semgrep = "error"

    return HealthStatus(db=db, redis=redis, ollama=ollama, semgrep=semgrep)


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, session: AsyncSession = Depends(db_session_dep)) -> HTMLResponse:
    health_data = await health(session)
    total_jobs = (await session.execute(select(func.count(Job.id)))).scalar_one()
    total_findings = (await session.execute(select(func.count(Finding.id)))).scalar_one()
    total_cached = (await session.execute(select(func.coalesce(func.sum(Job.cached_hits), 0)))).scalar_one()
    cache_hit_rate = (total_cached / total_findings * 100) if total_findings else 0
    avg_llm_time = (await session.execute(select(func.avg(Job.duration)))).scalar_one() or 0
    recent_jobs = (await session.execute(select(Job).order_by(Job.created_at.desc()).limit(10))).scalars().all()

    db_size = "n/a"
    try:
        db_size = str((await session.execute(text("SELECT pg_size_pretty(pg_database_size(current_database()))"))).scalar_one())
    except Exception:
        pass

    redis_mem = "n/a"
    try:
        redis_info = await redis_client.info("memory")
        redis_mem = redis_info.get("used_memory_human", "n/a")
    except Exception:
        pass

    return templates.TemplateResponse(
        "dashboard/index.html",
        {
            "request": request,
            "health": health_data.model_dump(),
            "metrics": {
                "total_jobs": total_jobs,
                "total_findings": total_findings,
                "cache_hit_rate": round(cache_hit_rate, 2),
                "avg_llm_time": round(float(avg_llm_time), 2),
            },
            "storage": {"db_size": db_size, "redis_memory": redis_mem},
            "jobs": recent_jobs,
            "debug": settings.debug,
        },
    )


@router.get("/dashboard/logs", response_class=HTMLResponse)
async def dashboard_logs(
    request: Request,
    level: str | None = None,
    job_id: str | None = None,
) -> HTMLResponse:
    log_path = Path(settings.log_dir / settings.log_file)
    lines: list[str] = []
    if log_path.exists():
        lines = log_path.read_text(encoding="utf-8").splitlines()[-200:]

    def include(line: str) -> bool:
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            return True
        if level and parsed.get("level") != level.upper():
            return False
        if job_id and str(parsed.get("job_id")) != job_id:
            return False
        return True

    filtered = [line for line in lines if include(line)]
    return templates.TemplateResponse(
        "dashboard/logs.html",
        {"request": request, "lines": filtered, "level": level or "", "job_id": job_id or "", "debug": settings.debug},
    )
