"""接口限流单元测试（P5）。

直接驱动 RateLimitMiddleware.dispatch，避开 TestClient 的异步 Redis 线程问题；
走真实 Redis 验证固定窗口计数：超过每 IP / 每用户阈值返回 429 + Retry-After，
白名单路径 /health 不受限。
"""
import asyncio

from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.response import success
from app.core.security import create_access_token
from app.db.redis_client import redis_client
from app.middleware.rate_limit import RateLimitMiddleware


def _make_request(path: str, ip: str = "127.0.0.1", auth: str | None = None) -> Request:
    headers = [(b"authorization", auth.encode())] if auth else []
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": headers,
        "client": (ip, 1234),
        "query_string": b"",
    }
    return Request(scope)


async def _run():
    settings.rate_limit_enabled = True

    # 用假 app 构造中间件（dispatch 不依赖 app）
    mw = RateLimitMiddleware(app=None)
    calls = {"n": 0}

    async def call_next(request: Request) -> JSONResponse:
        calls["n"] += 1
        return JSONResponse(success(data={}).model_dump())

    # ---- 每 IP 档：阈值 3 ----
    settings.rate_limit_per_ip_per_min = 3
    settings.rate_limit_per_user_per_min = 10_000
    ip_key = "rl:ip:127.0.0.1"
    await redis_client.delete(ip_key)
    for _ in range(3):
        resp = await mw.dispatch(_make_request("/__probe"), call_next)
        assert resp.status_code == 200, "阈值内应放行"
    resp = await mw.dispatch(_make_request("/__probe"), call_next)
    assert resp.status_code == 429, "超过阈值应被拦截"
    assert "Retry-After" in resp.headers, "429 应带 Retry-After"
    assert resp.headers["X-RateLimit-Limit"] == "3"
    assert calls["n"] == 3, "超阈值后不应再进入 handler"
    await redis_client.delete(ip_key)

    # ---- 白名单 /health 不受限 ----
    settings.rate_limit_per_ip_per_min = 1
    for _ in range(5):
        resp = await mw.dispatch(_make_request("/health"), call_next)
        assert resp.status_code == 200
    assert calls["n"] == 8  # 5 次白名单均进入 handler

    # ---- 每用户档：阈值 2 ----
    settings.rate_limit_per_ip_per_min = 10_000
    settings.rate_limit_per_user_per_min = 2
    token = create_access_token("u1", "patient")
    user_key = "rl:user:u1"
    await redis_client.delete(user_key)
    hdr = f"Bearer {token}"
    for _ in range(2):
        resp = await mw.dispatch(_make_request("/x", auth=hdr), call_next)
        assert resp.status_code == 200, "用户阈值内应放行"
    resp = await mw.dispatch(_make_request("/x", auth=hdr), call_next)
    assert resp.status_code == 429, "用户超过阈值应被拦截"
    await redis_client.delete(user_key)
    await redis_client.aclose()  # 重置连接池，避免跨 asyncio.run 事件循环污染


def test_rate_limit():
    asyncio.run(_run())
