"""请求 ID 注入中间件（技术架构第15.5章链路追踪前置）。

为每个请求分配 request_id，注入 request.state 并回写响应头 X-Request-ID；
后续 OpenTelemetry TraceID 与日志 Loki 均以此为锚点关联。
"""
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response
