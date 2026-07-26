"""Redis 连接池（技术架构第5章：缓存/会话/限流）。"""
import redis.asyncio as aioredis

from app.core.config import settings

redis_client = aioredis.from_url(settings.redis_uri, decode_responses=True)


async def get_redis() -> aioredis.Redis:
    return redis_client
