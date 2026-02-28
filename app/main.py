import asyncio
import logging

from fastapi import FastAPI

from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.workers.job_queue import job_queue

settings = get_settings()
setup_logging(settings.log_dir / settings.log_file, "DEBUG" if settings.debug else "INFO")
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name, debug=settings.debug)
app.include_router(router)


@app.on_event("startup")
async def startup_event() -> None:
    logger.info("Starting Code Radar AI", extra={"event": "startup"})
    asyncio.create_task(job_queue.run_forever())


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Code Radar AI is running"}
