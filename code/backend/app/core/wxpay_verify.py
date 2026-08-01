"""微信支付回调验签与解密（第14章 APIv3，生产骨架补全）。

微信支付回调（/v3/pay/transactions/jsapi 的异步通知）为：
- 请求头 Wechatpay-Signature（Base64(RSA-SHA256)）、Wechatpay-Timestamp、Wechatpay-Nonce、Wechatpay-Serial
- 请求体 JSON 的 resource 用 APIv3 key 做 AES-256-GCM 解密，得到真实交易结果

本模块提供：
- `PlatformCertStore`：平台证书自动下载（GET /v3/certificates，用 APIv3 key 解密后按 serial 缓存到文件）。
- `verify_notify(...)`：dev 沙箱直接放行；生产据平台证书公钥 RSA 验签。
- `decrypt_resource(...)`：cryptography AES-256-GCM 解密 resource.ciphertext。

敏感信息（APIv3 key、证书）不打印日志（等保三级）。
"""
from __future__ import annotations

import base64
import json
import os
import threading
from pathlib import Path
from typing import Any

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings

# 微信支付平台证书下载网关（APIv3）
_WXPAY_CERT_DOWNLOAD_PATH = "/v3/certificates"


def decrypt_resource(resource: dict[str, Any], *, api_v3_key: str | None = None) -> dict[str, Any]:
    """AES-256-GCM 解密回调 resource。

    resource = { "algorithm": "AEAD_AES_256_GCM", "ciphertext": ..., "nonce": ..., "associated_data": ... }
    生产用 APIv3 key 解密；dev 沙箱不调用（由模拟回调直接给明文）。
    """
    key = api_v3_key or settings.wxpay_api_v3_key
    if not key:
        raise ValueError("缺少 APIv3 key，无法解密回调 resource")

    algorithm = resource.get("algorithm")
    if algorithm != "AEAD_AES_256_GCM":
        raise ValueError(f"不支持的回调 resource 加密算法: {algorithm}")
    ciphertext = base64.b64decode(resource["ciphertext"])
    nonce = base64.b64decode(resource["nonce"])
    aad = resource.get("associated_data") or ""
    if isinstance(aad, str):
        aad = aad.encode("utf-8")

    # AES-256-GCM：key 必须为 32 字节；ciphertext 末尾 16 字节为认证标签。
    aesgcm = AESGCM(key.encode("utf-8") if isinstance(key, str) else key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, aad)
    return json.loads(plaintext.decode("utf-8"))


class PlatformCertStore:
    """微信支付平台证书管理：按 serial 缓存公钥，支持按需自动下载。

    平台证书用于验证回调 Wechatpay-Signature。证书随微信轮换，故需按 serial 动态获取。
    下载接口 GET /v3/certificates 本身也需商户签名（用商户私钥），返回的证书用 APIv3 key 解密。
    """

    def __init__(self) -> None:
        self._cache_dir = Path(settings.wxpay_cert_cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._memory: dict[str, Any] = {}

    # ---- 商户私钥签名（用于下载证书接口的 Authorization 头） ----
    def _merchant_sign(self, method: str, url_path: str, body: str, *, timestamp: str, nonce: str) -> str:
        from app.services.wxpay import _auth_header  # 复用既有签名构造

        return _auth_header(method, url_path, body, timestamp=timestamp, nonce=nonce)

    def _cache_file(self, serial: str) -> Path:
        return self._cache_dir / f"{serial}.pem"

    def get_public_key(self, serial: str) -> Any:
        """按 serial 取平台证书公钥（内存→文件→下载）。"""
        with self._lock:
            if serial in self._memory:
                return self._memory[serial]
            f = self._cache_file(serial)
            if f.exists():
                pub = serialization.load_pem_public_key(f.read_bytes())
                self._memory[serial] = pub
                return pub
            # 未知 serial：触发一次全量下载并刷新缓存
            self._download_certs()
            if serial in self._memory:
                return self._memory[serial]
            raise RuntimeError(f"无法获取 serial={serial} 的微信平台证书（已尝试下载）。")

    def _download_certs(self) -> None:
        """调用 GET /v3/certificates，解密后写入文件+内存缓存。"""
        url_path = _WXPAY_CERT_DOWNLOAD_PATH
        timestamp = str(int(__import__("time").time()))
        nonce = os.urandom(8).hex()
        auth = self._merchant_sign("GET", url_path, "", timestamp=timestamp, nonce=nonce)
        try:
            resp = httpx.get(
                f"https://api.mch.weixin.qq.com{url_path}",
                headers={"Authorization": auth, "Accept": "application/json", "User-Agent": "ihm-backend/1.0"},
                timeout=10.0,
            )
        except httpx.TransportError as exc:
            raise RuntimeError(f"微信平台证书下载失败: {exc}") from exc
        if resp.status_code != 200:
            raise RuntimeError(f"微信平台证书下载失败 HTTP {resp.status_code}")
        for item in resp.json().get("data", []):
            serial = item["serial_no"]
            cert = item["encrypt_certificate"]
            pem_text = cert_decrypt_to_pem(cert)
            self._memory[serial] = serialization.load_pem_public_key(pem_text.encode("utf-8"))
            self._cache_file(serial).write_text(pem_text, encoding="utf-8")


def cert_decrypt_to_pem(encrypt_certificate: dict[str, Any]) -> str:
    """将微信返回的 encrypt_certificate 用 APIv3 key 解密为证书 PEM 文本。"""
    key = settings.wxpay_api_v3_key
    if not key:
        raise ValueError("缺少 APIv3 key，无法解密平台证书")
    ciphertext = base64.b64decode(encrypt_certificate["ciphertext"])
    nonce = base64.b64decode(encrypt_certificate["nonce"])
    aad = encrypt_certificate.get("associated_data") or b""
    if isinstance(aad, str):
        aad = aad.encode("utf-8")
    aesgcm = AESGCM(key.encode("utf-8") if isinstance(key, str) else key)
    return aesgcm.decrypt(nonce, ciphertext, aad).decode("utf-8")


def verify_notify(
    *,
    timestamp: str,
    nonce: str,
    body: str,
    signature: str | None,
    serial: str | None = None,
) -> bool:
    """校验回调签名。dev 沙箱跳过真验签直接返回 True（仅用于本地联调）。

    生产实现：
    1. 用商户平台下载的平台证书公钥，对 `f"{timestamp}\\n{nonce}\\n{body}\\n"` 做 RSA-SHA256 验签。
    2. 比对微信回传的 Wechatpay-Signature（Base64）与本地计算值。
    """
    if settings.wxpay_dev_sandbox:
        return True
    if not signature or not serial:
        return False
    try:
        pub = PlatformCertStore().get_public_key(serial)
    except RuntimeError:
        return False
    message = f"{timestamp}\n{nonce}\n{body}\n".encode("utf-8")
    try:
        pub.verify(
            base64.b64decode(signature),
            message,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False


def parse_notify_body(body: str) -> dict[str, Any]:
    """解析回调 JSON（dev 沙箱直接 json.loads；生产先 verify_notify 再 decrypt_resource）。"""
    return json.loads(body)
