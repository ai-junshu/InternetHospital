"""Redis 缓存层（P5 性能容灾：cache-aside）。

仅缓存脱敏 / 聚合 / 参考类只读数据；绝不缓存 PII 与密文（totp_secret / health_tags）。
所有函数 best-effort：Redis 不可用时静默降级，不阻断主流程。

约定：
  - value 统一 JSON 序列化（非敏感）。
  - `cached(...)` 装饰器包裹 FastAPI 读端点，命中直接返回缓存 data，未命中回源写回。
  - 写操作后调用 `cache_delete` / `cache_invalidate` 失效相关 key。
"""
import functools
import json
from typing import Any, Callable, Optional

from app.core.config import settings
from app.core.response import success
from app.db.redis_client import redis_client


def build_key(*parts: Any) -> str:
    return "cache:" + ":".join(str(p) for p in parts)


async def cache_get(key: str) -> Any | None:
    try:
        raw = await redis_client.get(key)
    except Exception:
        return None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


async def cache_set(key: str, value: Any, ttl: int | None = None) -> None:
    ttl = ttl or settings.cache_default_ttl
    try:
        await redis_client.set(key, json.dumps(value, default=str), ex=ttl)
    except Exception:
        pass


async def cache_delete(key: str) -> None:
    try:
        await redis_client.delete(key)
    except Exception:
        pass


async def cache_delete_prefix(prefix: str) -> int:
    """按前缀批量失效（如聚合列表多页）。返回删除数量。best-effort。"""
    try:
        count = 0
        async for k in redis_client.scan_iter(match=f"{prefix}*"):
            await redis_client.delete(k)
            count += 1
        return count
    except Exception:
        return 0


def cached(ttl: int | None = None, key_builder: Optional[Callable[..., str]] = None):
    """cache-aside 装饰器：包裹读端点。命中返回缓存 data；未命中回源并写回。

    key_builder 接收与端点相同的参数（含 Depends 注入值），返回缓存 key 片段。
    缺省 key 由模块/函数名 + 参数拼接（覆盖性较弱，建议显式提供）。
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if key_builder is not None:
                key = build_key(key_builder(*args, **kwargs))
            else:
                key = build_key(func.__module__, func.__qualname__, args, tuple(kwargs.values()))
            try:
                hit = await cache_get(key)
            except Exception:
                hit = None
            if hit is not None:
                return success(data=hit, message="cached")
            result = await func(*args, **kwargs)
            data = getattr(result, "data", None)
            if data is not None:
                try:
                    # pydantic 模型先转 dict 再序列化，保证缓存命中后结构一致。
                    payload = data.model_dump(mode="json") if hasattr(data, "model_dump") else data
                    await cache_set(key, payload, ttl)
                except Exception:
                    pass
            return result

        return wrapper

    return decorator
