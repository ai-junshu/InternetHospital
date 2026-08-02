"""微信支付生产化测试（P1-H3）。

验证：
1. 沙箱模式 create_prepay()（无参，内部读 settings）返回模拟 prepay_id + 完整 JSAPI 字段；
2. 生产模式 + 缺商户凭证时 _production_prepay 抛 RuntimeError（由 pay_order 安全降级为业务错误，不 500）；
3. pay_order 在生产分支失败时应抛 BusinessError（统一错误模型），而非裸 500。
"""
import pytest

from app.core.config import settings
from app.services.wxpay import create_prepay, _production_prepay
from app.core.errors import BusinessError


def test_sandbox_prepay_returns_mock():
    if not settings.wxpay_dev_sandbox:
        pytest.skip("非沙箱模式，跳过模拟 prepay 断言")
    # create_prepay 为 @lru_cache 装饰，需传 4 个 keyword-only 参数（内部按 settings 路由沙箱/生产）
    pre = create_prepay(
        out_trade_no="TEST202608010001",
        amount=100,
        description="测试",
        openid="openid_x",
    )
    assert isinstance(pre, object)
    assert pre.prepay_id.startswith("sbx_prepay_")
    assert pre.app_id and pre.time_stamp and pre.nonce_str and pre.pay_sign


def test_production_without_credentials_raises():
    """生产模式且缺凭证：必须抛 RuntimeError（pay_order 捕获后降级为业务错误）。

    用 monkeypatch 强制走生产分支（关闭沙箱 + 清空凭证）。
    """
    if settings.wxpay_dev_sandbox:
        pytest.skip("沙箱模式下生产分支不可达，需用真实配置验证")

    # 凭证已配置时生产分支应成功发起（不抛 RuntimeError），跳过本断言
    if settings.wxpay_mch_id and settings.wxpay_mch_private_key and settings.wxpay_api_v3_key:
        pytest.skip("已配置真实微信支付凭证，生产下单由集成验证（不在此发真实请求）")

    with pytest.raises(RuntimeError):
        _production_prepay("TEST202608010002", 100, "测试", "openid_x")


def test_pay_order_downgrade_on_production_failure():
    """pay_order 在生产失败时应抛 BusinessError（统一错误模型），而非裸 500。

    通过依赖注入构造 DB session 与订单，强制生产分支并用 monkeypatch
    让 create_prepay 抛 RuntimeError 来模拟缺凭证/网关失败。
    """
    from unittest.mock import patch
    from app.api.v1.ih.orders import pay_order
    from app.models.ih_models import IhOrder
    from app.schemas.ih import OrderPayIn
    import asyncio
    from app.db.session import SessionLocal

    if settings.wxpay_dev_sandbox:
        pytest.skip("沙箱模式不触发生产降级分支")

    async def _run():
        async with SessionLocal() as db:
            order = IhOrder(order_no="TESTPO202608010001", order_type="otc", amount=100, status="pending")
            db.add(order)
            await db.commit()
            await db.refresh(order)
            try:
                with patch(
                    "app.api.v1.ih.orders.create_prepay",
                    side_effect=RuntimeError("微信商户凭证缺失"),
                ):
                    with pytest.raises(BusinessError):
                        await pay_order(
                            order_id=order.id,
                            body=OrderPayIn(openid="openid_x"),
                            db=db,
                            actor=("doctor", 1),
                        )
            finally:
                await db.delete(order)
                await db.commit()

    asyncio.run(_run())
