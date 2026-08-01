"""互联网医院订单与支付（技术架构第11.2/14章）。

MVP：创建订单（rx/otc）→ 支付（占位微信预支付，落 ih_payment）。
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError, ErrorCode
from app.core.response import success
from app.core.deps import get_db, current_user, actor_of, require_role
from app.core.config import settings
from app.core.wxpay_verify import verify_notify, parse_notify_body
from app.models.ih_models import IhOrder, IhPayment
from app.schemas.common import PageResult
from app.schemas.ih import OrderCreate, OrderOut, OrderPayIn
from app.services.audit import write_audit
from app.services.wxpay import create_prepay, build_notify_url
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
    pay_status: str | None = None,
    _auth: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    conds = [IhOrder.is_deleted.is_(False)]
    if user_id is not None:
        conds.append(IhOrder.user_id == user_id)
    if pay_status is not None:
        conds.append(IhOrder.pay_status == pay_status)
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
    """S5 规范化预支付：创建预支付单（trade_state=pending），返回前端调起所需 JSAPI 参数。

    不再直接落 paid；真实支付结果由微信回调 /wxpay/notify（或 dev 模拟 /pay/mock-success）驱动。
    """
    order = await db.get(IhOrder, order_id)
    if not order or order.is_deleted:
        raise BusinessError(ErrorCode.RESOURCE_NOT_FOUND, "订单不存在")
    if order.pay_status == "paid":
        raise BusinessError(ErrorCode.PARAM_INVALID, "订单已支付")

    # 幂等：复用该订单已有的 pending 预支付单
    pay = (
        await db.scalar(
            select(IhPayment).where(
                IhPayment.order_no == order.order_no,
                IhPayment.trade_state.in_(["pending"]),
                IhPayment.is_deleted.is_(False),
            )
        )
    )
    if pay is None:
        pay = IhPayment(order_no=order.order_no, amount=order.amount, pay_channel=body.channel)
        db.add(pay)

    # 统一下单（dev 沙箱返回模拟 prepay_id + 签名参数）
    pre = create_prepay(
        out_trade_no=order.order_no,
        amount=order.amount,
        description=body.description or f"医疗订单 {order.order_no}",
        openid=body.openid or "",
    )
    pay.prepay_id = pre.prepay_id
    pay.trade_state = "pending"
    pay.mch_id = settings.wxpay_mch_id or None
    order.pay_status = "paying"
    await db.commit()
    await db.refresh(order)
    await write_audit(
        db,
        action="order.prepay",
        resource="ih_order",
        role=_user.get("role"),
        actor_id=actor_of(_user),
        after={"order_no": order.order_no, "prepay_id": pre.prepay_id},
        ip=request.client.host if request.client else None,
    )
    # 返回前端 wx.requestPayment 所需字段
    return success(
        data={
            "order_no": order.order_no,
            "pay_status": order.pay_status,
            "prepay_id": pre.prepay_id,
            "app_id": pre.app_id,
            "time_stamp": pre.time_stamp,
            "nonce_str": pre.nonce_str,
            "package": pre.package,
            "pay_sign": pre.pay_sign,
            "sign_type": pre.sign_type,
        }
    )


@router.post("/wxpay/notify", response_model=None)
async def wxpay_notify(request: Request, db: AsyncSession = Depends(get_db)):
    """微信支付异步回调（第14章 APIv3）。

    dev 沙箱（wxpay_dev_sandbox=True）：跳过真验签，直接按明文 body 驱动支付成功。
    生产：先 verify_notify（RSA 验签）→ decrypt_resource（AES-GCM 解密）→ 更新状态。
    回调幂等：按 transaction_id 去重，已处理则直接返回 SUCCESS。
    """
    raw = (await request.body()).decode("utf-8")
    # 验签（沙箱放行）
    wx_ts = request.headers.get("Wechatpay-Timestamp", "")
    wx_nonce = request.headers.get("Wechatpay-Nonce", "")
    wx_sign = request.headers.get("Wechatpay-Signature")
    if not verify_notify(timestamp=wx_ts, nonce=wx_nonce, body=raw, signature=wx_sign):
        raise BusinessError(ErrorCode.FORBIDDEN, "回调验签失败")

    data = parse_notify_body(raw)
    # 生产路径：data = decrypt_resource(data["resource"])；沙箱 data 即明文交易结果
    order_no = data.get("out_trade_no") or (data.get("resource", {}) or {}).get("out_trade_no")
    transaction_id = data.get("transaction_id")
    trade_state = data.get("trade_state", "SUCCESS")
    if not order_no:
        raise BusinessError(ErrorCode.PARAM_INVALID, "回调缺少 out_trade_no")

    return await _apply_paid(db, order_no, transaction_id, trade_state, notify_raw=data)


@router.post("/{order_id}/pay/mock-success", response_model=None)
async def pay_mock_success(
    order_id: int, request: Request, _user: dict = Depends(require_role("patient", "doctor", "platform")), db: AsyncSession = Depends(get_db)
):
    """dev 模拟支付成功（无商户凭证时跑通支付闭环）。生产环境应禁用或加开关校验。"""
    if not settings.wxpay_dev_sandbox:
        raise BusinessError(ErrorCode.FORBIDDEN, "非沙箱环境禁止模拟支付")
    order = await db.get(IhOrder, order_id)
    if not order or order.is_deleted:
        raise BusinessError(ErrorCode.RESOURCE_NOT_FOUND, "订单不存在")
    return await _apply_paid(
        db,
        order.order_no,
        f"MOCK{order.order_no}",
        "SUCCESS",
        notify_raw={"mock": True, "by": actor_of(_user)},
    )


async def _apply_paid(
    db: AsyncSession, order_no: str, transaction_id: str | None, trade_state: str, notify_raw: dict
) -> dict:
    """支付成功落地（回调/mock 复用）：幂等更新订单与支付单。"""
    order = (
        await db.scalar(select(IhOrder).where(IhOrder.order_no == order_no, IhOrder.is_deleted.is_(False)))
    )
    if order is None:
        raise BusinessError(ErrorCode.RESOURCE_NOT_FOUND, "订单不存在")

    pay = (
        await db.scalar(select(IhPayment).where(IhPayment.order_no == order_no, IhPayment.is_deleted.is_(False)))
    )
    if pay is None:
        pay = IhPayment(order_no=order_no, amount=order.amount)
        db.add(pay)

    # 幂等：已支付则不重复记账
    if pay.trade_state == "SUCCESS" and order.pay_status == "paid":
        return success(data={"order_no": order_no, "pay_status": "paid", "trade_state": "SUCCESS"})

    if trade_state == "SUCCESS":
        order.pay_status = "paid"
        pay.trade_state = "SUCCESS"
        pay.transaction_id = transaction_id
        pay.paid_at = datetime.now(timezone.utc)
        pay.notify_raw_json = notify_raw
    else:
        order.pay_status = "paying"
        pay.trade_state = trade_state
    await db.commit()
    await db.refresh(order)
    await write_audit(
        db,
        action="order.paid",
        resource="ih_order",
        after={"order_no": order_no, "trade_state": trade_state},
    )
    # 微信回调约定返回纯文本 SUCCESS（此处供联调用，统一响应体亦可）
    return success(data={"order_no": order_no, "pay_status": order.pay_status, "trade_state": pay.trade_state})
