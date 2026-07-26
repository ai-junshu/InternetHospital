"""健康数据中台：门店 / 调理师查询（技术架构第11.2章）。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError, ErrorCode
from app.core.response import success
from app.core.deps import get_db, require_role, store_scope
from app.models.mt_models import MtStore, MtTherapist
from app.schemas.common import PageResult
from app.schemas.mt import StoreOut, TherapistOut

router = APIRouter(prefix="/stores", tags=["mt-门店"])


@router.get("", response_model=None)
async def list_stores(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    region: str | None = None,
    _auth: dict = Depends(require_role("store", "therapist", "platform", "xingyao")),
    db: AsyncSession = Depends(get_db),
):
    conds = [MtStore.is_deleted.is_(False)]
    if region:
        conds.append(MtStore.region == region)
    total = await db.scalar(select(func.count()).select_from(MtStore).where(*conds)) or 0
    rows = (
        await db.execute(
            select(MtStore)
            .where(*conds)
            .order_by(MtStore.id.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    ).scalars().all()
    return success(
        data=PageResult(
            total=total,
            page=page,
            page_size=page_size,
            items=[StoreOut.model_validate(r) for r in rows],
        )
    )


@router.get("/{store_id}", response_model=None)
async def get_store(store_id: int, scope: int | None = Depends(store_scope), _auth: dict = Depends(require_role("store", "therapist", "platform", "xingyao")), db: AsyncSession = Depends(get_db)):
    store = await db.get(MtStore, store_id)
    if not store or store.is_deleted:
        raise BusinessError(ErrorCode.RESOURCE_NOT_FOUND, "门店不存在")
    if scope is not None and store.id != scope:
        raise BusinessError(ErrorCode.FORBIDDEN, "无权访问其他门店")
    return success(data=StoreOut.model_validate(store))


@router.get("/{store_id}/therapists", response_model=None)
async def list_therapists(
    store_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    scope: int | None = Depends(store_scope),
    _auth: dict = Depends(require_role("store", "therapist", "platform", "xingyao")),
    db: AsyncSession = Depends(get_db),
):
    # store/therapist 角色强制只看本门店；platform/xingyao 用 path 门店参数
    eff_store = scope if scope is not None else store_id
    conds = [MtTherapist.is_deleted.is_(False), MtTherapist.store_id == eff_store]
    total = (
        await db.scalar(select(func.count()).select_from(MtTherapist).where(*conds)) or 0
    )
    rows = (
        await db.execute(
            select(MtTherapist)
            .where(*conds)
            .order_by(MtTherapist.id.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    ).scalars().all()
    return success(
        data=PageResult(
            total=total,
            page=page,
            page_size=page_size,
            items=[TherapistOut.model_validate(r) for r in rows],
        )
    )
