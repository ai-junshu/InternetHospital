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
