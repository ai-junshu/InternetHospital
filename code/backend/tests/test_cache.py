"""Redis 缓存层测试（P5）。

走真实 Redis（infra docker-compose 已起 redis:7-alpine，端口 6379）。
缓存层 best-effort：Redis 不可用时 cache_get 返回 None，不抛异常。
"""
import asyncio

from app.core.cache import build_key, cache_delete, cache_get, cache_set, cached
from app.core.response import success
from app.db.redis_client import redis_client


async def _roundtrip():
    k = build_key("p5", "cache", "roundtrip")
    await cache_delete(k)
    assert await cache_get(k) is None
    await cache_set(k, {"a": 1, "b": [2, 3]}, 30)
    assert await cache_get(k) == {"a": 1, "b": [2, 3]}
    await cache_delete(k)
    assert await cache_get(k) is None
    await redis_client.aclose()  # 重置连接池，避免跨 asyncio.run 事件循环污染


async def _ttl_expiry():
    k = build_key("p5", "cache", "ttl")
    await cache_delete(k)
    await cache_set(k, "v", 1)
    assert await cache_get(k) == "v"
    await asyncio.sleep(1.2)
    assert await cache_get(k) is None
    await redis_client.aclose()


async def _cached_bypass():
    calls = {"n": 0}

    @cached(ttl=30, key_builder=lambda: "p5:cached:demo")
    async def fetch():
        calls["n"] += 1
        return success(data={"v": 42})

    k = build_key("p5:cached:demo")
    await cache_delete(k)
    r1 = await fetch()
    r2 = await fetch()
    assert r1.data == {"v": 42}
    # 第二次命中缓存，底层函数只执行一次
    assert calls["n"] == 1
    # 缓存命中返回相同 data
    assert r2.data == {"v": 42}
    await cache_delete(k)
    await redis_client.aclose()


def test_cache_roundtrip():
    asyncio.run(_roundtrip())


def test_cache_ttl_expiry():
    asyncio.run(_ttl_expiry())


def test_cached_decorator_bypasses_on_hit():
    asyncio.run(_cached_bypass())
