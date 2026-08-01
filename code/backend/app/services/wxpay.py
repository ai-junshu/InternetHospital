"""微信支付统一下单服务（第14章 APIv3 JSAPI，迭代 A · S5）。

职责：封装「预支付统一下单」与「JSAPI 调起参数签名」。
- 生产：调用微信 APIv3 `/v3/pay/transactions/jsapi`，返回真实 prepay_id 与签名参数。
- dev 沙箱（settings.wxpay_dev_sandbox=True）：不直连微信，返回模拟 prepay_id + 本地签名参数，
  使「预支付→前端调起→回调/模拟成功」状态机在无商户凭证下可完整联调。

敏感信息（mch_id / APIv3 key / 证书）不打印日志（等保三级）。
"""
from __future__ import annotations

import base64
import hashlib
import json
import time
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from app.core.config import settings
from app.core.wxpay_verify import PlatformCertStore

# 微信支付 APIv3 生产网关
_WXPAY_API_BASE = "https://api.mch.weixin.qq.com"


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


def _load_private_key():
    """读取商户 API 私钥（pem，PKCS#8），缓存避免重复磁盘 IO。"""
    if not settings.wxpay_private_key_path:
        raise RuntimeError("生产微信支付未配置 wxpay_private_key_path（商户 API 私钥 pem 路径）。")
    pem = Path(settings.wxpay_private_key_path).read_bytes()
    return serialization.load_pem_private_key(pem, password=None)


# 模块级缓存私钥对象
_private_key_cache = None


def _get_private_key():
    global _private_key_cache
    if _private_key_cache is None:
        _private_key_cache = _load_private_key()
    return _private_key_cache


def _rsa_sign(message: str) -> str:
    """对字符串做 RSA-SHA256 签名并返回 Base64。"""
    key = _get_private_key()
    signature = key.sign(message.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())
    return base64.b64encode(signature).decode("ascii")


def _auth_header(method: str, url_path: str, body: str, *, timestamp: str, nonce: str) -> str:
    """构造 Authorization: WECHATPAY2-SHA256-RSA2048 头。

    签名串 = HTTP方法\\nURL路径(含query)\\n时间戳\\n随机串\\n请求体\\n
    """
    message = f"{method}\n{url_path}\n{timestamp}\n{nonce}\n{body}\n"
    signature = _rsa_sign(message)
    mch_id = settings.wxpay_mch_id
    serial = settings.wxpay_cert_serial
    if not mch_id or not serial:
        raise RuntimeError("生产微信支付未配置 wxpay_mch_id / wxpay_cert_serial。")
    return (
        f'WECHATPAY2-SHA256-RSA2048 mchid="{mch_id}",'
        f'nonce_str="{nonce}",signature="{signature}",timestamp="{timestamp}",serial_no="{serial}"'
    )


def _production_prepay(out_trade_no: str, amount: int, description: str, openid: str) -> PrepayResult:
    """生产：调用微信 APIv3 JSAPI 统一下单，返回真实 prepay_id 与 JSAPI 调起签名。

    流程：
    1. POST /v3/pay/transactions/jsapi，带 Authorization 商户签名头。
    2. 解析响应取 prepay_id。
    3. 按 JSAPI 规则用商户私钥对 appId/timeStamp/nonceStr/package 做 RSA 签名（paySign）。
    """
    app_id = settings.wxpay_appid or settings.wx_appid
    if not app_id:
        raise RuntimeError("生产微信支付未配置 wxpay_appid。")
    if not settings.wxpay_mch_id:
        raise RuntimeError("生产微信支付未配置 wxpay_mch_id。")
    if amount <= 0:
        raise ValueError("支付金额(amount)必须为正整数（单位：分）。")

    url_path = "/v3/pay/transactions/jsapi"
    timestamp = str(int(time.time()))
    nonce = hashlib.md5(f"{out_trade_no}{timestamp}".encode()).hexdigest()
    body = json.dumps(
        {
            "appid": app_id,
            "mchid": settings.wxpay_mch_id,
            "description": description,
            "out_trade_no": out_trade_no,
            "notify_url": build_notify_url(),
            "amount": {"total": amount, "currency": "CNY"},
            "payer": {"openid": openid},
        },
        ensure_ascii=False,
    )
    auth = _auth_header("POST", url_path, body, timestamp=timestamp, nonce=nonce)

    try:
        resp = httpx.post(
            f"{_WXPAY_API_BASE}{url_path}",
            content=body.encode("utf-8"),
            headers={
                "Authorization": auth,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "ihm-backend/1.0",
            },
            timeout=10.0,
        )
    except httpx.TransportError as exc:  # 网络/连接层失败，向上抛由调用方降级
        raise RuntimeError(f"微信支付网关请求失败: {exc}") from exc

    if resp.status_code != 200:
        # 微信错误响应体含 code/message，不打印敏感信息（等保三级）
        raise RuntimeError(f"微信支付下单失败 HTTP {resp.status_code}")

    prepay_id = resp.json().get("prepay_id")
    if not prepay_id:
        raise RuntimeError("微信支付下单响应缺少 prepay_id")

    # JSAPI 调起签名（小程序 wx.requestPayment）
    pay_ts = str(int(time.time()))
    pay_nonce = hashlib.md5(f"{prepay_id}{pay_ts}".encode()).hexdigest()
    package = f"prepay_id={prepay_id}"
    pay_message = f"{app_id}\n{pay_ts}\n{pay_nonce}\n{package}\n"
    pay_sign = _rsa_sign(pay_message)

    return PrepayResult(
        prepay_id=prepay_id,
        app_id=app_id,
        time_stamp=pay_ts,
        nonce_str=pay_nonce,
        package=package,
        pay_sign=pay_sign,
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
