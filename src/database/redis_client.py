"""Redis client connection management."""
import redis.asyncio as aioredis
from typing import Optional
import structlog

from src.config import settings

logger = structlog.get_logger()


class RedisClient:
    """Async Redis client wrapper."""
    
    def __init__(self):
        """Initialize Redis client."""
        self._client: Optional[aioredis.Redis] = None
    
    async def connect(self) -> None:
        """Establish connection to Redis."""
        try:
            self._client = await aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=10
            )
            # Test connection
            await self._client.ping()
            logger.info("redis_connected", url=settings.redis_url)
        except Exception as e:
            logger.error("redis_connection_failed", error=str(e))
            raise
    
    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            logger.info("redis_disconnected")
    
    @property
    def client(self) -> aioredis.Redis:
        """Get Redis client instance."""
        if self._client is None:
            raise RuntimeError("Redis client not connected. Call connect() first.")
        return self._client
    
    async def health_check(self) -> bool:
        """Check if Redis is healthy."""
        try:
            await self.client.ping()
            return True
        except Exception as e:
            logger.error("redis_health_check_failed", error=str(e))
            return False


# Global Redis client instance
redis_client = RedisClient()
