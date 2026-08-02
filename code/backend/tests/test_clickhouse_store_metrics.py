"""ClickHouse 门店经营宽表端到端验证（P2-CH 验证）。

仅当本地 ClickHouse 可达时运行；不可达自动 skip，不阻塞主链路。
测试内自清理（DELETE 测试行），不污染数据。
与项目约定一致，使用 asyncio.run 包裹异步逻辑（无 pytest-asyncio）。

注意：本测试只验证 CH 写入/查询链路（ensure_table + 直写 + 读回），
不调用依赖共享 PG async engine 的 aggregate_store_metrics（其在 asyncio.run 跨事件循环会触发
asyncpg 'NoneType' has no attribute 'send' 陷阱）。PG 聚合链路由 store_metrics 单测覆盖。
"""
import asyncio
from datetime import date, timedelta

import pytest

from app.db.clickhouse_client import ch_available, ensure_store_metrics_table, ch_client
from app.services.store_metrics import compute_metrics_row

pytestmark = pytest.mark.skipif(
    not ch_available(),
    reason="ClickHouse 不可达（docker ihm-clickhouse 未运行），跳过端到端验证",
)

# 用极端 store_id 避免与真实门店冲突
_TEST_STORE_ID = 991234
_COLUMNS = [
    "date", "store_id", "store_name", "region", "appointment_cnt", "arrival_cnt",
    "deal_customers", "deal_amount", "deal_orders", "repurchase_customers", "nps_avg",
]


@pytest.fixture(scope="module", autouse=True)
def _ensure_table():
    assert ensure_store_metrics_table() is True
    yield
    # 清理测试可能残留的行
    try:
        ch_client.execute(
            "ALTER TABLE mt_store_metrics DELETE WHERE store_id=%(s)s",
            {"s": _TEST_STORE_ID},
        )
    except Exception:  # noqa: BLE001
        pass


def _clean_test_rows(target):
    ch_client.execute(
        "ALTER TABLE mt_store_metrics DELETE WHERE date=%(d)s AND store_id=%(s)s",
        {"d": target, "s": _TEST_STORE_ID},
    )


def test_ensure_table_and_columns():
    existing = {r[0] for r in ch_client.execute("DESCRIBE TABLE mt_store_metrics")}
    for col in _COLUMNS:
        assert col in existing, f"mt_store_metrics 缺失列: {col}"


def test_write_and_query_roundtrip():
    target = date.today() - timedelta(days=1)
    _clean_test_rows(target)

    # 直写一条测试行验证写入+读回链路（绕过 PG，避免共享 engine 跨事件循环陷阱）
    row = compute_metrics_row(target, _TEST_STORE_ID, "CH验证门店", "测试区", 5, 3, 8.0, 2)
    _clean_test_rows(target)
    ch_client.execute(
        f"INSERT INTO mt_store_metrics ({', '.join(_COLUMNS)}) VALUES", [row]
    )

    rows = ch_client.execute(
        "SELECT store_name, appointment_cnt, nps_avg FROM mt_store_metrics WHERE date=%(d)s AND store_id=%(s)s",
        {"d": target, "s": _TEST_STORE_ID},
    )
    assert len(rows) >= 1
    r = rows[0]
    # 按列名读取，避免依赖 SELECT * 的列序（历史旧表列序可能不同）
    assert r[0] == "CH验证门店"
    assert r[1] == 5
    assert r[2] == 8.0

    _clean_test_rows(target)
