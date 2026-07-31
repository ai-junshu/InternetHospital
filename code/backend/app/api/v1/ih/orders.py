"""互联网医院订单与支付（技术架构第11.2/14章）。

MVP：创建订单（rx/otc）→ 支付（占位微信预支付，落 ih_payment）。
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError, ErrorCode
from app.core.response import success
from app.core.deps import get_db, current_user, actor_of
from app.models.ih_models import IhOrder, IhPayment
from app.schemas.common import PageResult
from app.schemas.ih import OrderCreate, OrderOut, OrderPayIn
from app.services.audit import write_audit
from app.utils.idgen import gen_no

router = APIRouter(prefix="/orders", tags=["ih-订单"])


@router.post("", response_model=None)
async def create_order(
    body: OrderCreate, request: Request, _user: dict = Depends(current_user), db: AsyncSession = Depends(get_db)
):
    if body.type == "rx" and not body.prescription_id:
        raise BusinessError(ErrorCode.PARAM_INVALID, "处方药下单必须关联处方（凭方购买）")
    no = gen_no("ORD")
    order = IhOrder(
        order_no=no,
        user_id=body.user_id,
        type=body.type,
        amount=body.amount,
        prescription_id=body.prescription_id,
        pay_status="unpaid",
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)
    await write_audit(
        db,
        action="order.create",
        resource="ih_order",
        role=_user.get("role"),
        actor_id=actor_of(_user),
        after={"order_no": no, "amount": body.amount},
        ip=request.client.host if request.client else None,
    )
    return success(data=OrderOut.model_validate(order))


@router.get("", response_model=None)
async def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: int | None = None,
    _auth: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    conds = [IhOrder.is_deleted.is_(False)]
    if user_id is not None:
        conds.append(IhOrder.user_id == user_id)
    total = await db.scalar(select(func.count()).select_from(IhOrder).where(*conds)) or 0
    rows = (
        await db.execute(
            select(IhOrder)
            .where(*conds)
            .order_by(IhOrder.id.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    ).scalars().all()
    return success(
        data=PageResult(
            total=total,
            page=page,
            page_size=page_size,
            items=[OrderOut.model_validate(r) for r in rows],
        )
    )


@router.post("/{order_id}/pay", response_model=None)
async def pay_order(
    order_id: int, body: OrderPayIn, request: Request, _user: dict = Depends(current_user), db: AsyncSession = Depends(get_db)
):
    order = await db.get(IhOrder, order_id)
    if not order or order.is_deleted:
        raise BusinessError(ErrorCode.RESOURCE_NOT_FOUND, "订单不存在")
    if order.pay_status == "paid":
        raise BusinessError(ErrorCode.PARAM_INVALID, "订单已支付")
    # 占位：真实环境调用微信 unifiedorder 拿 prepay_id（第14章）
    prepay_id = gen_no("PRE")
    order.pay_status = "paid"
    pay = IhPayment(
        order_no=order.order_no,
        amount=order.amount,
        pay_channel=body.channel,
        trade_state="SUCCESS",
        prepay_id=prepay_id,
        paid_at=datetime.now(timezone.utc),
    )
    db.add(pay)
    await db.commit()
    await db.refresh(order)
    await write_audit(
        db,
        action="order.pay",
        resource="ih_order",
        role=_user.get("role"),
        actor_id=actor_of(_user),
        after={"order_no": order.order_no, "prepay_id": prepay_id},
        ip=request.client.host if request.client else None,
    )
    return success(
        data={"order_no": order.order_no, "pay_status": order.pay_status, "prepay_id": prepay_id}
    )
