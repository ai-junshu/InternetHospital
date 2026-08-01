"""Milvus 向量检索惰性客户端骨架（P3，技术架构第6/13章）。

仅暴露连接工厂；依赖（pymilvus）未安装时惰性 import 容错，不影响主流程启动。
用于健康画像 / 方案推荐等向量的相似检索。
"""
from typing import Optional

import logging

from app.core.config import settings

logger = logging.getLogger("ihm.milvus")


def get_milvus_client():
    """返回 MilvusClient 实例；依赖缺失时返回 None 并打印告警。"""
    try:
        from pymilvus import MilvusClient
    except ImportError:
        logger.warning("pymilvus 未安装，Milvus 客户端不可用（配置已就绪，依赖为 optional）")
        return None
    return MilvusClient(uri=settings.milvus_uri)


async def ensure_health_vector_collection(collection: str = "mt_health_profile") -> Optional[object]:
    """示例：确保健康画像向量集合存在。依赖缺失返回 None。"""
    client = get_milvus_client()
    if client is None:
        return None
    if not client.has_collection(collection):
        client.create_collection(collection, dimension=128)
    return client
