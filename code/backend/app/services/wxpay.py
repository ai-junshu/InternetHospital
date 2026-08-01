"""微信支付统一下单服务（第14章 APIv3 JSAPI，迭代 A · S5）。

职责：封装「预支付统一下单」与「JSAPI 调起参数签名」。
- 生产：调用微信 APIv3 `/v3/pay/transactions/jsapi`，返回真实 prepay_id 与签名参数。
- dev 沙箱（settings.wxpay_dev_sandbox=True）：不直连微信，返回模拟 prepay_id + 本地签名参数，
  使「预支付→前端调起→回调/模拟成功」状态机在无商户凭证下可完整联调。

敏感信息（mch_id / APIv3 key / 证书）不打印日志（等保三级）。
"""
from __future__ import annotations

import hashlib
import time
import urllib.parse
from dataclasses import dataclass

from app.core.config import settings


@dataclass
class PrepayResult:
    prepay_id: str
    # JSAPI 调起所需字段（wx.requestPayment）
    app_id: str
    time_stamp: str
    nonce_str: str
    package: str          # "prepay_id=xxx"
    pay_sign: str         # 签名
    sign_type: str = "RSA"


def _sandbox_prepay(out_trade_no: str, amount: int, description: str, openid: str) -> PrepayResult:
    """dev 沙箱：构造模拟预支付结果（不调微信）。"""
    prepay_id = f"sbx_prepay_{out_trade_no}"
    app_id = settings.wxpay_appid or settings.wx_appid or "wx_sandbox_appid"
    ts = str(int(time.time()))
    nonce = hashlib.md5(f"{out_trade_no}{ts}".encode()).hexdigest()[:16]
    package = f"prepay_id={prepay_id}"
    # 沙箱用简易签名占位（生产为 RSA 签名，见 _production_sign）
    sign = hashlib.sha256(f"{app_id}{ts}{nonce}{package}".encode()).hexdigest()
    return PrepayResult(
        prepay_id=prepay_id,
        app_id=app_id,
        time_stamp=ts,
        nonce_str=nonce,
        package=package,
        pay_sign=sign,
    )


def _production_prepay(out_trade_no: str, amount: int, description: str, openid: str) -> PrepayResult:
    """生产：调用微信 APIv3 统一下单（占位实现，待注入真实商户凭证后补全 HTTP 调用）。

    此处保留接口契约与签名骨架；真实实现需：
    1. POST https://api.mch.weixin.qq.com/v3/pay/transactions/jsapi
       带 Authorization: WECHATPAY2-SHA256-RSA2048 商户签名头
    2. 解析返回 prepay_id
    3. 按 JSAPI 规则用商户私钥对 appId/timeStamp/nonceStr/package 做 RSA 签名
    """
    raise NotImplementedError(
        "生产微信支付需配置 wxpay_mch_id/wxpay_api_v3_key/wxpay_cert_serial 等凭证并补全 HTTP 调用（S5 当前仅交付沙箱+骨架）。"
    )


def create_prepay(
    *,
    out_trade_no: str,
    amount: int,          # 单位：分
    description: str,
    openid: str,
) -> PrepayResult:
    """统一下单入口：按开关路由沙箱/生产。"""
    if settings.wxpay_dev_sandbox:
        return _sandbox_prepay(out_trade_no, amount, description, openid)
    return _production_prepay(out_trade_no, amount, description, openid)


def build_notify_url() -> str:
    """构造支付回调地址（微信服务器回调用）。"""
    base = (settings.wxpay_notify_base_url or "").rstrip("/")
    return f"{base}/api/v1/ih/orders/wxpay/notify"
