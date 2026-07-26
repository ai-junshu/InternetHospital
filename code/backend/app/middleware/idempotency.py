"""幂等中间件骨架（技术架构第10.2章 Idempotency-Key）。

支付、开方等写操作须传 Idempotency-Key 防重复提交。脚手架阶段仅校验并透传，
真实去重入账（Redis 缓存首次响应，重复 Key 直接返回）待业务逻辑实现。
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class IdempotencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        key = request.headers.get("Idempotency-Key")
        request.state.idempotency_key = key
        response = await call_next(request)
        if key:
            response.headers["Idempotency-Key"] = key
        return response
