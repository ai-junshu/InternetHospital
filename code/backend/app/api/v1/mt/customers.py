"""健康数据中台：客户管理（授权激活，技术架构第11.2章）。"""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError, ErrorCode
from app.core.response import success
from app.core.deps import get_db, require_role, actor_of, store_scope
from app.models.mt_models import MtCustomer
from app.schemas.common import PageResult
from app.schemas.mt import CustomerAuthorizeIn, CustomerCreate, CustomerOut
from app.services.audit import write_audit

router = APIRouter(prefix="/customers", tags=["mt-客户"])


@router.post("", response_model=None)
async def create_customer(
    body: CustomerCreate, request: Request, _user: dict = Depends(require_role("store", "therapist", "platform", "xingyao")), db: AsyncSession = Depends(get_db)
):
    cust = MtCustomer(**body.model_dump())
    db.add(cust)
    await db.commit()
    await db.refresh(cust)
    await write_audit(
        db,
        action="customer.create",
        resource="mt_customer",
        role=_user.get("role"),
        actor_id=actor_of(_user),
        after=CustomerOut.model_validate(cust).model_dump(mode="json"),
        ip=request.client.host if request.client else None,
    )
    return success(data=CustomerOut.model_validate(cust))


@router.get("", response_model=None)
async def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    auth_status: str | None = None,
    scope: int | None = Depends(store_scope),
    _auth: dict = Depends(require_role("store", "therapist", "platform", "xingyao")),
    db: AsyncSession = Depends(get_db),
):
    conds = [MtCustomer.is_deleted.is_(False)]
    if scope is not None:
        conds.append(MtCustomer.source_store_id == scope)
    if auth_status:
        conds.append(MtCustomer.auth_status == auth_status)
    total = (
        await db.scalar(select(func.count()).select_from(MtCustomer).where(*conds)) or 0
    )
    rows = (
        await db.execute(
            select(MtCustomer)
            .where(*conds)
            .order_by(MtCustomer.id.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    ).scalars().all()
    return success(
        data=PageResult(
            total=total,
            page=page,
            page_size=page_size,
            items=[CustomerOut.model_validate(r) for r in rows],
        )
    )


@router.get("/{customer_id}", response_model=None)
async def get_customer(customer_id: int, scope: int | None = Depends(store_scope), _auth: dict = Depends(require_role("store", "therapist", "platform", "xingyao")), db: AsyncSession = Depends(get_db)):
    cust = await db.get(MtCustomer, customer_id)
    if not cust or cust.is_deleted:
        raise BusinessError(ErrorCode.RESOURCE_NOT_FOUND, "客户不存在")
    if scope is not None and cust.source_store_id != scope:
        raise BusinessError(ErrorCode.FORBIDDEN, "无权访问其他门店客户")
    return success(data=CustomerOut.model_validate(cust))


@router.patch("/{customer_id}/authorize", response_model=None)
async def authorize_customer(
    customer_id: int, body: CustomerAuthorizeIn, request: Request, scope: int | None = Depends(store_scope), _user: dict = Depends(require_role("store", "therapist", "platform", "xingyao")), db: AsyncSession = Depends(get_db)
):
    cust = await db.get(MtCustomer, customer_id)
    if not cust or cust.is_deleted:
        raise BusinessError(ErrorCode.RESOURCE_NOT_FOUND, "客户不存在")
    if scope is not None and cust.source_store_id != scope:
        raise BusinessError(ErrorCode.FORBIDDEN, "无权操作其他门店客户")
    cust.auth_status = "authorized"
    cust.auth_file_url = body.auth_file_url
    await db.commit()
    await db.refresh(cust)
    await write_audit(
        db,
        action="customer.authorize",
        resource="mt_customer",
        role=_user.get("role"),
        actor_id=actor_of(_user),
        after={"auth_status": "authorized"},
        ip=request.client.host if request.client else None,
    )
    return success(data=CustomerOut.model_validate(cust))
