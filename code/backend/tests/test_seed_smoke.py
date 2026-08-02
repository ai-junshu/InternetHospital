"""H5 种子数据实证冒烟测试（端到端，需 Postgres，不可达自动 skip）。

复用 app.db.verify_seed.verify()（已实证可读、稳定）做关键不变量核对：
- 关键表非空：门店 / 调理师 / 药师 / 后台账号 / AI 模型 / 数据资产
- P3 演示模块非空：药品 / 药房 / 库存 / 科室 / 投诉
- platform_admin 双因子已注入（two_factor_enabled + totp_secret + password_hash）

若种子尚未运行，report.ok 为 False，测试失败并提示先跑 seed。
无 Postgres 时整体 skip（_db_available 为 False）。
"""

import asyncio

import pytest

from app.db.seed import seed_all
from app.db.verify_seed import verify

_DB_AVAILABLE: bool | None = None


def _db_available() -> bool:
    """探测 Postgres 可达性（用临时引擎独立 loop，不污染共享 engine 连接池）。

    避免在 pytest 内对模块级共享 async engine 多次 asyncio.run 导致
    'Event loop is closed' / 'NoneType has no attribute send'。
    """
    global _DB_AVAILABLE
    if _DB_AVAILABLE is None:
        try:
            from sqlalchemy import text
            from sqlalchemy.ext.asyncio import create_async_engine

            from app.core.config import settings

            tmp = create_async_engine(settings.postgres_uri, pool_pre_ping=True)

            async def _c():
                async with tmp.connect() as conn:
                    await conn.execute(text("select 1"))

            asyncio.run(_c())
            _DB_AVAILABLE = True
        except Exception:
            _DB_AVAILABLE = False
    return _DB_AVAILABLE


@pytest.mark.skipif(
    not _db_available(), reason="Postgres 不可达，跳过种子实证端到端测试"
)
def test_seed_verification_passes():
    """种子实证脚本应整体通过（关键实体与双因子均落地）。

    为与其他测试（如 test_data_asset 的 drop_all）解耦，测试前先幂等
    重跑 seed，确保种子数据存在，再做验证。seed 为幂等实现，重跑安全。
    整个流程在单次 asyncio.run 内完成，避免共享 async engine 跨事件循环问题。
    """

    async def _run():
        await seed_all()
        return await verify()

    report = asyncio.run(_run())
    assert report["ok"], (
        "种子实证未通过：\n"
        + "\n".join(
            f"  [{'PASS' if c['passed'] else 'FAIL'}] {c['name']}"
            for c in report["checks"]
        )
    )
    # 明确断言 platform_admin 双因子三项齐备
    two_fa = next(
        (c for c in report["checks"] if c["name"] == "platform_admin_2fa"), None
    )
    assert two_fa is not None and two_fa["passed"], "platform_admin 双因子未完整注入"
