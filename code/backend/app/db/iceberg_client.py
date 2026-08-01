"""Iceberg 数据湖惰性客户端骨架（P3，技术架构第6/13章）。

仅暴露连接工厂与示例函数；依赖（pyiceberg）未安装时惰性 import 容错，
不影响主流程启动。生产由 k8s Helm 编排接入（见 README）。
"""
from typing import Optional

import logging

from app.core.config import settings

logger = logging.getLogger("ihm.iceberg")


def get_iceberg_catalog():
    """返回 Iceberg Catalog 实例；依赖缺失时返回 None 并打印告警。"""
    try:
        from pyiceberg.catalog import load_catalog
    except ImportError:
        logger.warning("pyiceberg 未安装，Iceberg 客户端不可用（配置已就绪，依赖为 optional）")
        return None
    return load_catalog(
        "rest",
        **{
            "uri": settings.iceberg_rest_uri,
            "warehouse": settings.iceberg_warehouse,
            "s3.endpoint": settings.iceberg_s3_endpoint,
            "s3.access-key-id": settings.iceberg_s3_access_key,
            "s3.secret-access-key": settings.iceberg_s3_secret_key,
        },
    )


async def ensure_asset_table(namespace: str = "ihm", table: str = "plat_data_asset") -> Optional[object]:
    """示例：确保数据资产表存在（融资估值资产落湖）。依赖缺失返回 None。"""
    catalog = get_iceberg_catalog()
    if catalog is None:
        return None
    # 实际建表逻辑在依赖就绪后补全；此处仅占位骨架
    return catalog
