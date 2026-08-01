"""互联网医院：合作药房管理（PRD 3.3.2 药房管理）。

- 列表只读、带分页/关键字/状态筛选。
- 写操作（增改删）由 platform 角色执行。
"""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import actor_of, get_db, require_role
from app.core.errors import BusinessError, ErrorCode
from app.core.response import success
from app.models.ih_models import IhPharmacy
from app.schemas.common import PageResult
from app.schemas.ih import PharmacyCreate, PharmacyOut, PharmacyUpdate
from app.services.audit import write_audit

router = APIRouter(prefix="/pharmacies", tags=["ih-合作药房"])


@router.get("", response_model=None)
async def list_pharmacies(
    keyword: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    conds = [IhPharmacy.is_deleted.is_(False)]
    if keyword:
        conds.append(or_(IhPharmacy.name.ilike(f"%{keyword}%"), IhPharmacy.license_no.ilike(f"%{keyword}%")))
    if status:
        conds.append(IhPharmacy.status == status)
    total = (await db.execute(select(func.count()).select_from(IhPharmacy).where(*conds))).scalar() or 0
    rows = (
        await db.execute(
            select(IhPharmacy).where(*conds).order_by(IhPharmacy.id.desc()).limit(page_size).offset((page - 1) * page_size)
        )
    ).scalars().all()
    return success(
        data=PageResult[PharmacyOut](
            total=total, page=page, page_size=page_size, items=[PharmacyOut.model_validate(r) for r in rows]
        )
    )


@router.get("/{pharmacy_id}", response_model=None)
async def get_pharmacy(pharmacy_id: int, db: AsyncSession = Depends(get_db)):
    p = await db.get(IhPharmacy, pharmacy_id)
    if not p or p.is_deleted:
        raise BusinessError(ErrorCode.NOT_FOUND, "药房不存在")
    return success(data=PharmacyOut.model_validate(p))


@router.post("", response_model=None)
async def create_pharmacy(
    body: PharmacyCreate,
    request: Request,
    user: dict = Depends(require_role("platform")),
    db: AsyncSession = Depends(get_db),
):
    p = IhPharmacy(**body.model_dump())
    db.add(p)
    await db.commit()
    await db.refresh(p)
    await write_audit(
        db,
        action="pharmacy.create",
        resource="ih_pharmacy",
        role=user.get("role"),
        actor_id=actor_of(user),
        after=PharmacyOut.model_validate(p).model_dump(mode="json"),
        ip=request.client.host if request.client else None,
    )
    return success(data=PharmacyOut.model_validate(p))


@router.patch("/{pharmacy_id}", response_model=None)
async def update_pharmacy(
    pharmacy_id: int,
    body: PharmacyUpdate,
    request: Request,
    user: dict = Depends(require_role("platform")),
    db: AsyncSession = Depends(get_db),
):
    p = await db.get(IhPharmacy, pharmacy_id)
    if not p or p.is_deleted:
        raise BusinessError(ErrorCode.NOT_FOUND, "药房不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    await db.commit()
    await db.refresh(p)
    await write_audit(
        db,
        action="pharmacy.update",
        resource="ih_pharmacy",
        role=user.get("role"),
        actor_id=actor_of(user),
        after=PharmacyOut.model_validate(p).model_dump(mode="json"),
        ip=request.client.host if request.client else None,
    )
    return success(data=PharmacyOut.model_validate(p))


@router.delete("/{pharmacy_id}", response_model=None)
async def delete_pharmacy(
    pharmacy_id: int,
    request: Request,
    user: dict = Depends(require_role("platform")),
    db: AsyncSession = Depends(get_db),
):
    p = await db.get(IhPharmacy, pharmacy_id)
    if not p or p.is_deleted:
        raise BusinessError(ErrorCode.NOT_FOUND, "药房不存在")
    p.is_deleted = True
    await db.commit()
    await write_audit(
        db,
        action="pharmacy.delete",
        resource="ih_pharmacy",
        role=user.get("role"),
        actor_id=actor_of(user),
        ip=request.client.host if request.client else None,
    )
    return success(message="已删除")
