"""ClickHouse 客户端（技术架构第5/11.3章：经营宽表 OLAP）。

脚手架阶段使用 clickhouse-driver 同步客户端占位；高吞吐场景建议替换为 aiochclient。
本地 docker-compose 将 native 端口映射为 19000。
"""
from urllib.parse import urlparse

from clickhouse_driver import Client

from app.core.config import settings

_parsed = urlparse(settings.clickhouse_uri)
ch_client = Client(
    host=_parsed.hostname or "localhost",
    port=19000,  # 本地 docker-compose 映射 native 端口
    user=_parsed.username or "ihm",
    password=_parsed.password or "ihm_dev_pwd",
    database=_parsed.path.lstrip("/") or "ihm",
)

# 与 app/services/store_metrics.py 的 _COLUMNS 严格对齐（顺序/类型一致）
_STORE_METRICS_DDL = """
CREATE TABLE IF NOT EXISTS mt_store_metrics (
    date Date,
    store_id UInt32,
    store_name String,
    region String,
    appointment_cnt UInt32,
    arrival_cnt UInt32,
    deal_customers UInt32,
    deal_amount Float64,
    deal_orders UInt32,
    repurchase_customers UInt32,
    nps_avg Float64
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (date, store_id)
"""

# 目标列定义：(列名, 类型)。用于建表后幂等补齐缺失列，兼容历史旧表。
_STORE_METRICS_COLUMNS = [
    ("date", "Date"),
    ("store_id", "UInt32"),
    ("store_name", "String"),
    ("region", "String"),
    ("appointment_cnt", "UInt32"),
    ("arrival_cnt", "UInt32"),
    ("deal_customers", "UInt32"),
    ("deal_amount", "Float64"),
    ("deal_orders", "UInt32"),
    ("repurchase_customers", "UInt32"),
    ("nps_avg", "Float64"),
]


def ch_available() -> bool:
    """探测 ClickHouse 是否可达（供调用方决定降级/跳过）。"""
    try:
        ch_client.execute("SELECT 1")
        return True
    except Exception:  # noqa: BLE001
        return False


def ensure_store_metrics_table() -> bool:
    """确保 mt_store_metrics 宽表存在且列对齐；成功返回 True，失败返回 False（降级）。

    策略：先 CREATE TABLE IF NOT EXISTS，再逐列检查并 ALTER ADD COLUMN 补齐，
    兼容历史上字段不完整（缺 store_name 等）的旧表，避免 IF NOT EXISTS 跳过。
    """
    try:
        ch_client.execute(_STORE_METRICS_DDL)
        existing = {row[0] for row in ch_client.execute("DESCRIBE TABLE mt_store_metrics")}
        for col, col_type in _STORE_METRICS_COLUMNS:
            if col not in existing:
                ch_client.execute(
                    f"ALTER TABLE mt_store_metrics ADD COLUMN IF NOT EXISTS {col} {col_type}"
                )
        return True
    except Exception as e:  # noqa: BLE001
        # 登录失败/网络不通时降级，不阻断主链路
        import logging

        logging.getLogger("clickhouse").warning("确保 mt_store_metrics 表失败: %s", e)
        return False
