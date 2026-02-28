import asyncio

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.workers.job_queue import job_queue


async def main() -> None:
    settings = get_settings()
    setup_logging(settings.log_dir / settings.log_file, "DEBUG" if settings.debug else "INFO")
    await job_queue.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
