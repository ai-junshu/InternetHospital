"""数据湖 / 向量库初始化管理端点（P3 基础设施编排 · 真实建表/建集合）。

仅 platform / xingyao 可调（RBAC，同其他 plat 管理接口）。
- GET  /data-lake/status ：探测 Iceberg / Milvus 可达性（不建资源）。
- POST /data-lake/init   ：真实建 Iceberg 资产表 + Milvus 健康画像集合（幂等）。
依赖缺失时安全降级，返回 available=False，不报错（配置化惰性客户端）。
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_role, actor_of
from app.core.response import success
from app.db.iceberg_client import ensure_asset_table, get_status as iceberg_status
from app.db.milvus_client import (
    ensure_health_vector_collection,
    get_status as milvus_status,
)
from app.services.audit import write_audit

router = APIRouter(prefix="/data-lake", tags=["plat-数据湖编排"])

_ROLES = ("platform", "xingyao")


@router.get("/status", response_model=None)
async def data_lake_status(
    _user: dict = Depends(require_role(*_ROLES)),
):
    return success(
        data={
            "iceberg": await iceberg_status(),
            "milvus": await milvus_status(),
        }
    )


@router.post("/init", response_model=None)
async def data_lake_init(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role(*_ROLES)),
):
    iceberg = await ensure_asset_table()
    milvus = await ensure_health_vector_collection()
    await write_audit(
        db,
        action="data_lake.init",
        resource="infra",
        role=_user.get("role"),
        actor_id=actor_of(_user),
        after={"iceberg": iceberg, "milvus": milvus},
        ip=request.client.host if request.client else None,
    )
    return success(
        data={"iceberg": iceberg, "milvus": milvus},
        message="数据湖编排初始化完成（依赖缺失时安全降级）",
    )
