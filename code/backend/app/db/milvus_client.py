"""Milvus 向量库惰性客户端（P3 基础设施编排 · 真实建集合）。

技术架构第6章：健康画像 embedding 落 Milvus，支撑相似患者/方案召回、门店
私域画像相似度检索。本客户端为「惰性」——仅在安装 pymilvus 且 Milvus 可达时
真正建集合；缺失依赖时安全降级（返回 available=False），不影响主链路启动
（配置化，非运行时强制依赖，见 pyproject vector 可选组）。
"""
from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger("ihm.milvus")

# 健康画像向量集合（按客户/患者 embedding 检索相似画像）
HEALTH_COLLECTION = "health_profile_vectors"
# embedding 维度（与 ai-service embedding 模型对齐，见 milvus_dimension 配置）
DEFAULT_DIM = 768


def _connect() -> Any | None:
    """惰性连接 Milvus（仅在依赖可用时）。"""
    try:
        from pymilvus import MilvusClient
    except Exception as e:  # 未安装 pymilvus（vector 可选组）
        logger.warning("[milvus] pymilvus 不可用，跳过向量集合初始化：%s", e)
        return None
    try:
        client = MilvusClient(
            uri=settings.milvus_uri,
            token=settings.milvus_token or None,
        )
        return client
    except Exception as e:
        logger.warning("[milvus] 服务不可达，跳过：%s", e)
        return None


async def ensure_health_vector_collection() -> dict:
    """确保健康画像向量集合存在（幂等，IVF_FLAT 索引）。

    返回：
        {"available": bool, "exists": bool, "collection": str, "dim": int, "detail": str}
    """
    dim = settings.milvus_dimension or DEFAULT_DIM
    client = _connect()
    if client is None:
        return {
            "available": False,
            "exists": False,
            "collection": HEALTH_COLLECTION,
            "dim": dim,
            "detail": "pymilvus 或 Milvus 不可用",
        }
    try:
        if client.has_collection(HEALTH_COLLECTION):
            return {
                "available": True,
                "exists": True,
                "collection": HEALTH_COLLECTION,
                "dim": dim,
                "detail": "已存在",
            }
        client.create_collection(
            collection_name=HEALTH_COLLECTION,
            dimension=dim,
            metric_type="COSINE",
            index_type="IVF_FLAT",
            index_params={"nlist": 1024},
        )
        logger.info("[milvus] 已建集合 %s (dim=%d)", HEALTH_COLLECTION, dim)
        return {
            "available": True,
            "exists": True,
            "collection": HEALTH_COLLECTION,
            "dim": dim,
            "detail": "已新建",
        }
    except Exception as e:
        logger.warning("[milvus] 建集合失败：%s", e)
        return {
            "available": True,
            "exists": False,
            "collection": HEALTH_COLLECTION,
            "dim": dim,
            "detail": f"建集合异常：{e}",
        }


async def get_status() -> dict:
    """探测 Milvus 可达性（供管理端点）。"""
    client = _connect()
    return {
        "available": client is not None,
        "uri": settings.milvus_uri,
        "collection": HEALTH_COLLECTION,
        "dim": settings.milvus_dimension or DEFAULT_DIM,
    }
