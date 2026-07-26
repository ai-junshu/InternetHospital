"""鉴权与防重放（技术架构第10.2章）。

- JWT 编解码：小程序 code2session 换 openid 后签发；后台账号密码登录签发。
- 防重放：timestamp + nonce + sign(HMAC)，5 分钟窗口。
- 双因子（P4）：TOTP / RFC 6238，标准库实现（hmac/time/struct），零外部依赖。
真实密钥经环境变量注入（第14.5章），此处仅用 settings。
"""
import base64
import hashlib
import hmac
import os
import struct
import time
from typing import Any

import jwt

from app.core.config import settings

# 密码落库强加密（等保三级）：PBKDF2-HMAC-SHA256 + 随机盐，标准库实现，无外部依赖
PBKDF2_ITER = 100_000
PBKDF2_HASH = "sha256"

# TOTP（RFC 6238）参数
TOTP_DIGITS = 6
TOTP_PERIOD = 30


def create_access_token(
    subject: str,
    role: str,
    expires_minutes: int | None = None,
    store_id: int | None = None,
) -> str:
    now = int(time.time())
    exp = now + (expires_minutes or settings.jwt_expire_minutes) * 60
    payload: dict[str, Any] = {"sub": subject, "role": role, "iat": now, "exp": exp}
    if store_id is not None:
        payload["store_id"] = store_id
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    # 校验失败抛 jwt.PyJWTError，由 deps.current_user 转为 BusinessError
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def verify_replay(timestamp: str, nonce: str, sign: str, body: bytes = b"") -> bool:
    try:
        ts = int(timestamp)
    except (TypeError, ValueError):
        return False
    if abs(int(time.time()) - ts) > settings.replay_window_seconds:
        return False
    raw = f"{timestamp}{nonce}".encode() + body
    expected = hmac.new(settings.jwt_secret.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sign)


def hash_password(password: str) -> tuple[str, str]:
    """PBKDF2-HMAC-SHA256 加盐哈希（密码落库强加密，等保三级要求）。

    返回 (hash_hex, salt_hex)，依赖标准库，无需 bcrypt/passlib 外部依赖。
    迭代次数 PBKDF2_ITER=100_000，盐 16 字节随机。
    """
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac(PBKDF2_HASH, password.encode("utf-8"), salt, PBKDF2_ITER)
    return dk.hex(), salt.hex()


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """校验明文密码与落库哈希/salt 是否匹配；盐非法直接返回 False。"""
    try:
        dk = hashlib.pbkdf2_hmac(
            PBKDF2_HASH, password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITER
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(dk.hex(), password_hash)


# ---------------- 双因子 TOTP（RFC 6238，P4 安全增强） ----------------

def gen_totp_secret() -> str:
    """生成 160-bit（20 字节）随机 Base32 密钥（RFC 4226 标准长度）。"""
    return base64.b32encode(os.urandom(20)).decode("ascii").rstrip("=")


def _b32_decode(secret: str) -> bytes:
    pad = "=" * ((8 - len(secret) % 8) % 8)
    return base64.b32decode(secret + pad)


def _totp_at(secret: str, for_time: int) -> str:
    key = _b32_decode(secret)
    counter = for_time // TOTP_PERIOD
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    o = digest[-1] & 0x0F
    code = (struct.unpack(">I", digest[o : o + 4])[0] & 0x7FFFFFFF) % (10**TOTP_DIGITS)
    return str(code).zfill(TOTP_DIGITS)


def verify_totp(secret: str, code: str, window: int = 1) -> bool:
    """校验动态码；允许 ±window 个时间步漂移（默认 ±30s）。"""
    try:
        code_norm = str(code).strip().replace(" ", "")
        if not code_norm.isdigit():
            return False
    except (TypeError, ValueError):
        return False
    now = int(time.time())
    for w in range(-window, window + 1):
        if _totp_at(secret, now + w * TOTP_PERIOD) == code_norm:
            return True
    return False


def totp_provisioning_uri(secret: str, account: str, issuer: str | None = None) -> str:
    """生成 otpauth:// URI，供 Google Authenticator / 微信令牌 扫码绑定。"""
    issuer = issuer or settings.totp_issuer
    return (
        f"otpauth://totp/{issuer}:{account}?secret={secret}"
        f"&issuer={issuer}&algorithm=SHA1&digits={TOTP_DIGITS}&period={TOTP_PERIOD}"
    )
