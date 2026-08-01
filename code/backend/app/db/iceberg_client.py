"""Iceberg 数据湖惰性客户端（P3 基础设施编排 · 真实建表）。

技术架构第6章：连续结构化治疗效果数据落 Iceberg 数据湖，支撑数据资产估值与
联邦训练样本供给。本客户端为「惰性」——仅在安装了 pyiceberg 且配置了 iceberg
rest 目录服务时才真正建表；缺失依赖时安全降级（返回 available=False），不影响
主链路启动（配置化，非运行时强制依赖，见 pyproject datalake 可选组）。
"""
from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger("ihm.iceberg")

# 资产估值宽表（落数据湖）的列定义：与 plat_data_asset 关键估值字段对齐，
# 用于离线聚合融资估值 / 联邦训练样本切片。
ASSET_TABLE_NAME = "plat_data_asset"
ASSET_TABLE_SCHEMA = {
    "id": "long",
    "name": "string",
    "owner": "string",
    "sensitivity_level": "string",
    "usage_scope": "string",
    "quality_score": "double",
    "update_freq": "string",
    "lifecycle_status": "string",
    "data_volume": "long",
    "estimated_value": "double",
    "snapshotted_at": "timestamp",
}


def _build_catalog() -> Any | None:
    """惰性构造 Iceberg Catalog（仅在依赖可用时）。"""
    try:
        from pyiceberg.catalog import load_catalog
    except Exception as e:  # 未安装 pyiceberg（datalake 可选组）
        logger.warning("[iceberg] pyiceberg 不可用，跳过数据湖建表：%s", e)
        return None
    try:
        catalog = load_catalog(
            "ihm",
            **{
                "type": "rest",
                "uri": settings.iceberg_rest_uri,
                "warehouse": settings.iceberg_warehouse,
            },
        )
        return catalog
    except Exception as e:
        logger.warning("[iceberg] 目录服务不可达，跳过：%s", e)
        return None


async def ensure_asset_table() -> dict:
    """确保数据资产估值表存在（幂等）。

    返回：
        {"available": bool, "exists": bool, "table": str, "detail": str}
    """
    catalog = _build_catalog()
    if catalog is None:
        return {
            "available": False,
            "exists": False,
            "table": ASSET_TABLE_NAME,
            "detail": "pyiceberg 或目录服务不可用",
        }
    try:
        from pyiceberg.schema import Schema
        from pyiceberg.types import (
            DoubleType,
            LongType,
            StringType,
            TimestampType,
        )

        identifier = f"{settings.iceberg_namespace}.{ASSET_TABLE_NAME}"
        if catalog.table_exists(identifier):
            return {
                "available": True,
                "exists": True,
                "table": identifier,
                "detail": "已存在",
            }
        # 按字段顺序构造 schema（id 从 1 递增）
        type_map = {
            "long": LongType,
            "double": DoubleType,
            "string": StringType,
            "timestamp": TimestampType,
        }
        fields = [
            type_map[dt].as_required()(i + 1, name)
            for i, (name, dt) in enumerate(ASSET_TABLE_SCHEMA.items())
        ]
        schema = Schema(*fields)
        catalog.create_table(identifier, schema)
        logger.info("[iceberg] 已建表 %s", identifier)
        return {
            "available": True,
            "exists": True,
            "table": identifier,
            "detail": "已新建",
        }
    except Exception as e:
        logger.warning("[iceberg] 建表失败：%s", e)
        return {
            "available": True,
            "exists": False,
            "table": ASSET_TABLE_NAME,
            "detail": f"建表异常：{e}",
        }


async def get_status() -> dict:
    """探测 Iceberg 目录可达性（供管理端点）。"""
    catalog = _build_catalog()
    return {
        "available": catalog is not None,
        "rest_uri": settings.iceberg_rest_uri,
        "namespace": settings.iceberg_namespace,
        "warehouse": settings.iceberg_warehouse,
    }
