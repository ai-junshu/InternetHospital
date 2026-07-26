"""接口限流中间件（P5 性能容灾：防滥用 / 防雪崩）。

基于 Redis 固定窗口计数器，支持两档：
  - per_ip：按客户端 IP（默认 120/窗口）
  - per_user：解析 Bearer JWT 取 sub（默认 300/窗口）
超限返回 429 + Retry-After（剩余窗口秒）+ 统一错误体。

设计要点：
  - 用 Lua 脚本保证 INCR + 首次 EXPIRE 的原子性。
  - best-effort：Redis 不可用时放行，不阻断主流程（容灾优先）。
  - 白名单路径（/health、/docs 等）直接放行。
  - 复用 audit.py 的 JWT 解析范式做 per-user 识别。
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.errors import ErrorCode
from app.core.response import error
from app.core.security import decode_access_token
from app.db.redis_client import redis_client

# 固定窗口原子自增（仅新建 key 时置过期）
_INCR_LUA = """
local cur = redis.call('incr', KEYS[1])
if cur == 1 then
  redis.call('expire', KEYS[1], ARGV[1])
end
return cur
"""


def _client_ip(request: Request) -> str:
    # 优先取 X-Forwarded-For 首段（经反代时），否则取直连 IP。
    fwd = request.headers.get("X-Forwarded-For")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _jwt_sub(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    try:
        payload = decode_access_token(auth[7:])
    except Exception:
        return None
    sub = payload.get("sub")
    return str(sub) if sub is not None else None


def _is_whitelisted(path: str) -> bool:
    return any(path.startswith(p) for p in settings.rate_limit_whitelist_list)


async def _incr_window(key: str, window: int) -> int:
    return await redis_client.eval(_INCR_LUA, 1, key, window)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not settings.rate_limit_enabled or _is_whitelisted(request.url.path):
            return await call_next(request)

        window = settings.rate_limit_window_seconds
        ip = _client_ip(request)
        sub = _jwt_sub(request)

        try:
            # per_ip 档
            ip_count = await _incr_window(f"rl:ip:{ip}", window)
            if ip_count > settings.rate_limit_per_ip_per_min:
                return await self._deny(settings.rate_limit_per_ip_per_min, window, f"rl:ip:{ip}")

            # per_user 档（已登录才计）
            if sub is not None:
                u_count = await _incr_window(f"rl:user:{sub}", window)
                if u_count > settings.rate_limit_per_user_per_min:
                    return await self._deny(settings.rate_limit_per_user_per_min, window, f"rl:user:{sub}")
        except Exception:
            # Redis 故障：放行，保障可用性（best-effort 限流）。
            return await call_next(request)

        return await call_next(request)

    async def _deny(self, limit: int, window: int, key: str) -> JSONResponse:
        try:
            ttl = await redis_client.ttl(key)
            retry_after = ttl if isinstance(ttl, int) and ttl > 0 else window
        except Exception:
            retry_after = window
        body = error(
            ErrorCode.RATE_LIMITED,
            "请求过于频繁，请稍后再试",
            data={"limit": limit, "window_seconds": window},
        ).model_dump()
        resp = JSONResponse(status_code=429, content=body)
        resp.headers["Retry-After"] = str(retry_after)
        resp.headers["X-RateLimit-Limit"] = str(limit)
        return resp
