"""微信支付回调验签骨架（第14章 APIv3，迭代 A · S5）。

微信支付回调（/v3/pay/transactions/jsapi 的异步通知）为：
- 请求头 Wechatpay-Signature（Base64(RSA-SHA256)）、Wechatpay-Timestamp、Wechatpay-Nonce、Wechatpay-Serial
- 请求体 JSON 的 resource 用 APIv3 key 做 AES-256-GCM 解密，得到真实交易结果

本模块提供：
- `verify_notify(...)`：dev 沙箱直接放行（跳过真验签）；生产据商户证书/AES-GCM 解密骨架实现。
- `decrypt_resource(...)`：AES-GCM 解密 resource 的骨架（生产补全）。

敏感信息（APIv3 key、证书）不打印日志（等保三级）。
"""
from __future__ import annotations

import base64
import json
from typing import Any

from app.core.config import settings


def verify_notify(*, timestamp: str, nonce: str, body: str, signature: str | None) -> bool:
    """校验回调签名。dev 沙箱跳过真验签直接返回 True（仅用于本地联调）。

    生产实现：
    1. 用商户平台下载的平台证书公钥，对 `f"{timestamp}\n{nonce}\n{body}\n"` 做 RSA-SHA256 验签。
    2. 比对微信回传的 Wechatpay-Signature（Base64）与本地计算值。
    """
    if settings.wxpay_dev_sandbox:
        return True
    # TODO(生产): 接入平台证书公钥验证 Wechatpay-Signature
    raise NotImplementedError("生产环境微信支付回调验签需配置平台证书公钥（S5 当前仅交付沙箱+骨架）。")


def decrypt_resource(resource: dict[str, Any], *, api_v3_key: str | None = None) -> dict[str, Any]:
    """AES-256-GCM 解密回调 resource。

    resource = { "algorithm": "AEAD_AES_256_GCM", "ciphertext": ..., "nonce": ..., "associated_data": ... }
    生产用 APIv3 key 解密；dev 沙箱不调用（由模拟回调直接给明文）。
    """
    key = api_v3_key or settings.wxpay_api_v3_key
    if not key:
        raise ValueError("缺少 APIv3 key，无法解密回调 resource")
    # TODO(生产): 用 cryptography 库实现 AESGCM(key).decrypt(nonce, b64(ciphertext), aad)
    raise NotImplementedError("生产环境需引入 cryptography 库实现 AES-256-GCM 解密（S5 当前仅交付骨架）。")


def parse_notify_body(body: str) -> dict[str, Any]:
    """解析回调 JSON（dev 沙箱直接 json.loads；生产先 verify_notify 再 decrypt_resource）。"""
    return json.loads(body)
