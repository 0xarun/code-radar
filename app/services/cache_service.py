import logging

from app.core.config import get_settings
from app.db.redis import redis_client

logger = logging.getLogger(__name__)


class CacheService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def get(self, finding_hash: str) -> str | None:
        key = f"llm:{finding_hash}"
        value = await redis_client.get(key)
        if value:
            logger.info("Cache hit", extra={"event": "cache.hit"})
        return value

    async def set(self, finding_hash: str, analysis: str) -> None:
        key = f"llm:{finding_hash}"
        await redis_client.setex(key, self.settings.redis_ttl_seconds, analysis)
