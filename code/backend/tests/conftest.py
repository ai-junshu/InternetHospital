"""pytest 夹具。

注意：避免在模块顶层 import app.main（其导入链会在 pytest 主进程创建
全局 Redis 异步连接池，进程退出时 event loop 已关闭会抛
'Event loop is closed' / 'NoneType' object has no attribute 'send'）。
改为延迟导入，并在 session 结束时显式关闭 Redis 连接池。
"""
import asyncio

import pytest


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app.main import app

    return TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def _close_redis():
    yield
    # session 结束后关闭全局 Redis 连接池，避免主进程退出时的 event loop 报错。
    try:
        from app.db.redis_client import redis_client

        asyncio.get_event_loop().run_until_complete(redis_client.aclose())
    except Exception:
        pass
