"""幂等中间件（技术架构第10.2章 Idempotency-Key）。

支付、开方等写操作须传 Idempotency-Key 防重复提交。

实现：对 WRITE_METHODS（POST/PUT/PATCH/DELETE）且带 `Idempotency-Key`
的请求，先查 Redis 是否已缓存首次响应：
- 命中且已处理完成 -> 直接返回首次缓存的响应（含状态码与 body），业务不重复执行；
- 未命中 -> 执行业务，将成功响应（2xx）缓存（TTL 24h），重复提交返回首次结果。
- 4xx/5xx 不缓存，允许客户端换 Key 或修正参数后重试。

Key 命名：`idem:{method}:{path}:{key}`，仅按方法+路径+Key 维度去重
（不绑定请求体，符合"同一业务动作重复提交"语义）。
"""
import json
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.db.redis_client import redis_client

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
IDEM_TTL = 24 * 3600  # 24h
IDEM_REDIS_PREFIX = "idem:"


class IdempotencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        method = request.method
        key = request.headers.get("Idempotency-Key")
        # 仅写方法 + 带 Key 才进入幂等保护；否则透传。
        if method not in WRITE_METHODS or not key:
            return await call_next(request)

        redis_key = f"{IDEM_REDIS_PREFIX}{method}:{request.url.path}:{key}"
        request.state.idempotency_key = key

        cached = await redis_client.get(redis_key)
        if cached:
            try:
                payload = json.loads(cached)
                return JSONResponse(
                    status_code=payload.get("status_code", 200),
                    content=payload.get("body"),
                    headers={"Idempotency-Replay": "true"},
                )
            except (json.JSONDecodeError, TypeError):
                # 缓存损坏则忽略，重新执行。
                pass

        response = await call_next(request)

        # 仅缓存"业务成功"响应：本项目统一错误模型下业务失败也是 HTTP 200，
        # 需以响应体 code==0 判定成功；4xx/5xx 与业务失败均不缓存，允许重试。
        if 200 <= response.status_code < 300:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk if isinstance(chunk, bytes) else chunk.encode()
            try:
                cached_body = json.loads(body.decode("utf-8"))
            except (json.JSONDecodeError, TypeError):
                cached_body = None
            is_success = isinstance(cached_body, dict) and cached_body.get("code") == 0
            if is_success:
                await redis_client.set(
                    redis_key, json.dumps({"status_code": response.status_code, "body": cached_body}), ex=IDEM_TTL
                )
                new_resp = JSONResponse(
                    status_code=response.status_code,
                    content=cached_body,
                    headers=dict(response.headers),
                )
                return new_resp
            # 业务失败：重建原始响应（body 已被消费），不缓存。
            return JSONResponse(
                status_code=response.status_code,
                content=cached_body if cached_body is not None else {},
                headers=dict(response.headers),
            )
        return response
