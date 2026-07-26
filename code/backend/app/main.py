"""FastAPI 入口（技术架构第10.2章中间件链与路由挂载）。

中间件链顺序：requestId 注入 → 接口限流 → 幂等检查 → 审计记录（外层到内层）。
统一响应、错误码、JWT+RBAC 在 core 与 deps 中落地。
"""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1 import router as v1_router
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.response import success
from app.db.redis_client import redis_client
from app.db.session import SessionLocal, engine
from app.middleware.audit import AuditMiddleware
from app.middleware.idempotency import IdempotencyMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_id import RequestIdMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动钩子：探活依赖（best-effort，失败仅记录不阻断启动）。
    try:
        await redis_client.ping()
    except Exception:
        pass
    try:
        async with SessionLocal() as db:
            await db.execute(text("SELECT 1"))
    except Exception:
        pass
    yield
    # 优雅关闭：释放引擎连接池与 Redis 连接（P5 容灾）。
    try:
        await engine.dispose()
    except Exception:
        pass
    try:
        await redis_client.aclose()
    except Exception:
        pass


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

# 中间件链（技术架构第10.2章）
app.add_middleware(AuditMiddleware)
app.add_middleware(IdempotencyMiddleware)
# 接口限流：先于审计，避免被拦截请求放大审计写量；复用 RequestId 注入的 X-Request-ID。
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(v1_router, prefix=settings.api_v1_prefix)


@app.get("/health")
async def health():
    """真实探活（P5）：返回 Redis / PostgreSQL 连通状态，仍保留总态 ok。"""
    deps: dict[str, str] = {}
    try:
        deps["redis"] = "ok" if await redis_client.ping() else "down"
    except Exception:
        deps["redis"] = "down"
    try:
        async with SessionLocal() as db:
            await db.execute(text("SELECT 1"))
        deps["postgres"] = "ok"
    except Exception:
        deps["postgres"] = "down"
    return success(
        data={"status": "ok", "dependencies": deps},
        message="healthy",
    )
