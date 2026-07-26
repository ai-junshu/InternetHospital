"""SQLAlchemy 异步会话工厂（技术架构第5/11章）。

使用异步引擎 + 连接池；session 生命周期由 FastAPI 依赖注入管理，防止泄露。
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# pool_pre_ping=True：连接取出前探活，自动剔除断连（P5 容灾韧性）。
engine = create_async_engine(settings.postgres_uri, pool_pre_ping=True, echo=False)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
