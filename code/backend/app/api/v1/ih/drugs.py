"""互联网医院：药品目录（PRD 3.1.3 电子处方可开方药品）。

- 列表接口只读、带分页/关键字/类型筛选，并经 Redis 缓存（P5 cache-aside）。
- 写操作（增改删）由 platform 角色执行，并失效相关缓存。
"""
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import build_key, cache_delete_prefix, cached
from app.core.config import settings
from app.core.deps import actor_of, get_db, require_role
from app.core.errors import BusinessError, ErrorCode
from app.core.response import success
from app.models.ih_models import IhDrug
from app.schemas.common import PageResult
from app.schemas.ih import DrugCreate, DrugOut, DrugUpdate
from app.services.audit import write_audit

router = APIRouter(prefix="/drugs", tags=["ih-药品目录"])


def _drugs_cache_key(*args, **kwargs) -> str:
    return "drugs:{k}:{o}:{c}:{s}:{p}:{ps}".format(
        k=kwargs.get("keyword"),
        o=kwargs.get("otc_type"),
        c=kwargs.get("category"),
        s=kwargs.get("status"),
        p=kwargs.get("page"),
        ps=kwargs.get("page_size"),
    )


@router.get("", response_model=None)
@cached(ttl=settings.cache_default_ttl, key_builder=_drugs_cache_key)
async def list_drugs(
    keyword: str | None = None,
    otc_type: str | None = None,
    category: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    conds = [IhDrug.is_deleted.is_(False)]
    if keyword:
        conds.append(or_(IhDrug.name.ilike(f"%{keyword}%"), IhDrug.spec.ilike(f"%{keyword}%")))
    if otc_type:
        conds.append(IhDrug.otc_type == otc_type)
    if category:
        conds.append(IhDrug.category == category)
    if status:
        conds.append(IhDrug.status == status)
    total = (await db.execute(select(func.count()).select_from(IhDrug).where(*conds))).scalar() or 0
    rows = (
        await db.execute(
            select(IhDrug).where(*conds).order_by(IhDrug.id.desc()).limit(page_size).offset((page - 1) * page_size)
        )
    ).scalars().all()
    return success(
        data=PageResult[DrugOut](
            total=total, page=page, page_size=page_size, items=[DrugOut.model_validate(r) for r in rows]
        )
    )


@router.get("/{drug_id}", response_model=None)
async def get_drug(drug_id: int, db: AsyncSession = Depends(get_db)):
    drug = await db.get(IhDrug, drug_id)
    if not drug or drug.is_deleted:
        raise BusinessError(ErrorCode.NOT_FOUND, "药品不存在")
    return success(data=DrugOut.model_validate(drug))


@router.post("", response_model=None)
async def create_drug(
    body: DrugCreate,
    request: Request,
    user: dict = Depends(require_role("platform")),
    db: AsyncSession = Depends(get_db),
):
    drug = IhDrug(**body.model_dump())
    db.add(drug)
    await db.commit()
    await db.refresh(drug)
    await cache_delete_prefix(build_key("drugs"))
    await write_audit(
        db,
        action="drug.create",
        resource="ih_drug",
        role=user.get("role"),
        actor_id=actor_of(user),
        after=DrugOut.model_validate(drug).model_dump(mode="json"),
        ip=request.client.host if request.client else None,
    )
    return success(data=DrugOut.model_validate(drug))


@router.patch("/{drug_id}", response_model=None)
async def update_drug(
    drug_id: int,
    body: DrugUpdate,
    request: Request,
    user: dict = Depends(require_role("platform")),
    db: AsyncSession = Depends(get_db),
):
    drug = await db.get(IhDrug, drug_id)
    if not drug or drug.is_deleted:
        raise BusinessError(ErrorCode.NOT_FOUND, "药品不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(drug, k, v)
    await db.commit()
    await db.refresh(drug)
    await cache_delete_prefix(build_key("drugs"))
    await write_audit(
        db,
        action="drug.update",
        resource="ih_drug",

        role=user.get("role"),
        actor_id=actor_of(user),
        after=DrugOut.model_validate(drug).model_dump(mode="json"),
        ip=request.client.host if request.client else None,
    )
    return success(data=DrugOut.model_validate(drug))


@router.delete("/{drug_id}", response_model=None)
async def delete_drug(
    drug_id: int,
    request: Request,
    user: dict = Depends(require_role("platform")),
    db: AsyncSession = Depends(get_db),
):
    drug = await db.get(IhDrug, drug_id)
    if not drug or drug.is_deleted:
        raise BusinessError(ErrorCode.NOT_FOUND, "药品不存在")
    drug.is_deleted = True
    await db.commit()
    await cache_delete_prefix(build_key("drugs"))
    await write_audit(
        db,
        action="drug.delete",
        resource="ih_drug",

        role=user.get("role"),
        actor_id=actor_of(user),
        ip=request.client.host if request.client else None,
    )
    return success(message="已删除")
