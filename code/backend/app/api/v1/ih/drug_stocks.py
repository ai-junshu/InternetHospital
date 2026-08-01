"""互联网医院：药品库存（按 药房×药品 维度，PRD 3.3.2 药房库存管理）。

- 列表按 pharmacy_id / drug_id 筛选，标记 is_low（低于安全库存）。
- 调整库存（出入库）仅 platform/pharmacist 角色，记录审计。
"""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import actor_of, get_db, require_role
from app.core.errors import BusinessError, ErrorCode
from app.core.response import success
from app.models.ih_models import IhDrugStock
from app.schemas.common import PageResult
from app.schemas.ih import DrugStockCreate, DrugStockOut, DrugStockUpdate
from app.services.audit import write_audit

router = APIRouter(prefix="/drug-stocks", tags=["ih-药品库存"])


def _to_out(s: IhDrugStock) -> DrugStockOut:
    return DrugStockOut(
        id=s.id,
        created_at=s.created_at,
        updated_at=s.updated_at,
        drug_id=s.drug_id,
        pharmacy_id=s.pharmacy_id,
        stock=s.stock,
        safety_stock=s.safety_stock,
        is_low=s.safety_stock > 0 and s.stock < s.safety_stock,
    )


@router.get("", response_model=None)
async def list_drug_stocks(
    pharmacy_id: int | None = None,
    drug_id: int | None = None,
    low_only: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    conds = [IhDrugStock.is_deleted.is_(False)]
    if pharmacy_id:
        conds.append(IhDrugStock.pharmacy_id == pharmacy_id)
    if drug_id:
        conds.append(IhDrugStock.drug_id == drug_id)
    total = (await db.execute(select(func.count()).select_from(IhDrugStock).where(*conds))).scalar() or 0
    rows = (
        await db.execute(
            select(IhDrugStock).where(*conds).order_by(IhDrugStock.id.desc()).limit(page_size).offset((page - 1) * page_size)
        )
    ).scalars().all()
    items = [_to_out(r) for r in rows]
    if low_only:
        items = [i for i in items if i.is_low]
    return success(
        data=PageResult[DrugStockOut](total=total, page=page, page_size=page_size, items=items)
    )


@router.post("", response_model=None)
async def upsert_drug_stock(
    body: DrugStockCreate,
    request: Request,
    user: dict = Depends(require_role("platform", "pharmacist")),
    db: AsyncSession = Depends(get_db),
):
    existing = (
        await db.execute(
            select(IhDrugStock).where(
                IhDrugStock.drug_id == body.drug_id,
                IhDrugStock.pharmacy_id == body.pharmacy_id,
                IhDrugStock.is_deleted.is_(False),
            )
        )
    ).scalars().first()
    if existing:
        existing.stock = body.stock
        existing.safety_stock = body.safety_stock
        await db.commit()
        await db.refresh(existing)
        s = existing
        action = "drug_stock.update"
    else:
        s = IhDrugStock(**body.model_dump())
        db.add(s)
        await db.commit()
        await db.refresh(s)
        action = "drug_stock.create"
    await write_audit(
        db,
        action=action,
        resource="ih_drug_stock",
        role=user.get("role"),
        actor_id=actor_of(user),
        after=DrugStockOut.model_validate(s).model_dump(mode="json"),
        ip=request.client.host if request.client else None,
    )
    return success(data=_to_out(s))


@router.patch("/{stock_id}", response_model=None)
async def adjust_drug_stock(
    stock_id: int,
    body: DrugStockUpdate,
    request: Request,
    user: dict = Depends(require_role("platform", "pharmacist")),
    db: AsyncSession = Depends(get_db),
):
    s = await db.get(IhDrugStock, stock_id)
    if not s or s.is_deleted:
        raise BusinessError(ErrorCode.NOT_FOUND, "库存记录不存在")
    if body.stock is not None:
        if body.stock < 0:
            raise BusinessError(ErrorCode.BAD_REQUEST, "库存不能为负")
        s.stock = body.stock
    if body.safety_stock is not None:
        s.safety_stock = body.safety_stock
    await db.commit()
    await db.refresh(s)
    await write_audit(
        db,
        action="drug_stock.adjust",
        resource="ih_drug_stock",
        role=user.get("role"),
        actor_id=actor_of(user),
        after=DrugStockOut.model_validate(s).model_dump(mode="json"),
        ip=request.client.host if request.client else None,
    )
    return success(data=_to_out(s))
