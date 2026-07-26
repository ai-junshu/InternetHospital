"""门店经营宽表接口（第11.3章）。

- GET    /store-metrics        查询 ClickHouse 经营宽表（门店/平台/星耀）
- POST   /store-metrics/aggregate  手动触发按日聚合（平台/星耀/门店）
"""
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_role, store_scope
from app.core.response import success
from app.schemas.common import PageResult
from app.schemas.mt import AggregateMetricsIn, StoreMetricsOut
from app.services.store_metrics import aggregate_store_metrics, query_store_metrics

router = APIRouter(prefix="/store-metrics", tags=["mt-经营宽表"])


@router.get("", response_model=None)
async def get_store_metrics(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    store_id: int | None = None,
    region: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    scope: int | None = Depends(store_scope),
    _auth: dict = Depends(require_role("store", "therapist", "platform", "xingyao")),
):
    # store/therapist 角色强制只看本门店（RLS）；platform/xingyao 可用查询参数下钻
    eff_store = scope if scope is not None else store_id
    rows, total = await query_store_metrics(page, page_size, eff_store, region, date_from, date_to)
    return success(
        data=PageResult(
            total=total,
            page=page,
            page_size=page_size,
            items=[StoreMetricsOut.model_validate(r) for r in rows],
        )
    )


@router.post("/aggregate", response_model=None)
async def aggregate(
    body: AggregateMetricsIn,
    scope: int | None = Depends(store_scope),
    _auth: dict = Depends(require_role("platform", "xingyao", "store")),
):
    # store/therapist 角色强制只聚合本门店
    eff_store = scope if scope is not None else body.store_id
    count = await aggregate_store_metrics(body.target_date, eff_store)
    return success(data={"written": count, "target_date": body.target_date.isoformat()})
