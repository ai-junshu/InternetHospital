"""KMS 抽象与信封加密（落库加密，等保三级增强）。

设计：
- 可插拔 KmsClient 接口：encrypt(plaintext: bytes) -> str / decrypt(token: str) -> bytes。
- LocalKmsClient（默认）：本地 KMS 信封加密。主密钥(KEK)经环境变量注入，每值随机生成
  数据密钥(DEK)，AES-256-GCM(DEK) 加密明文，AES-256-GCM(KEK) 包裹 DEK；
  token = base64(JSON{v, kn, wd, dn, ct}) 落库。完整性由 GCM tag 保证，密钥错误即解密失败。
- AwsKmsClient（可选）：生产真实云 KMS 路径，用 generate_data_key / decrypt 实现同接口；
  切 kms_provider=aws 并配置 kms_aws_key_id 即可启用（懒导入 boto3，默认不依赖）。

主密钥不落库、不硬编码（经 KMS_MASTER_KEY 环境变量注入，第14.5章）。
"""
import base64
import hashlib
import json
import os
from typing import Protocol, runtime_checkable

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings

TOKEN_VERSION = 1


def _derive_kek(master_key: str) -> bytes:
    """任意长度主密钥经 SHA-256 派生为 32 字节 KEK（AES-256）。"""
    return hashlib.sha256(master_key.encode("utf-8")).digest()


def looks_encrypted(token: str | None) -> bool:
    """判定 token 是否本 KMS 密文（供迁移幂等跳过已加密行）。"""
    if not token:
        return False
    try:
        payload = json.loads(base64.b64decode(token))
    except Exception:
        return False
    return (
        isinstance(payload, dict)
        and payload.get("v") == TOKEN_VERSION
        and "ct" in payload
    )


@runtime_checkable
class KmsClient(Protocol):
    def encrypt(self, plaintext: bytes) -> str: ...
    def decrypt(self, token: str) -> bytes: ...


class LocalKmsClient:
    """本地 KMS：信封加密（每值随机 DEK，KEK 包裹 DEK）。"""

    def __init__(self, master_key: str | None = None):
        key = master_key or settings.kms_master_key
        self._kek = _derive_kek(key)

    def encrypt(self, plaintext: bytes) -> str:
        dek = os.urandom(32)
        dek_nonce = os.urandom(12)
        ct = AESGCM(dek).encrypt(dek_nonce, plaintext, None)
        kek_nonce = os.urandom(12)
        wrapped_dek = AESGCM(self._kek).encrypt(kek_nonce, dek, None)
        payload = {
            "v": TOKEN_VERSION,
            "kn": base64.b64encode(kek_nonce).decode(),
            "wd": base64.b64encode(wrapped_dek).decode(),
            "dn": base64.b64encode(dek_nonce).decode(),
            "ct": base64.b64encode(ct).decode(),
        }
        return base64.b64encode(json.dumps(payload).encode()).decode()

    def decrypt(self, token: str) -> bytes:
        payload = json.loads(base64.b64decode(token))
        kek_nonce = base64.b64decode(payload["kn"])
        wrapped_dek = base64.b64decode(payload["wd"])
        dek_nonce = base64.b64decode(payload["dn"])
        ct = base64.b64decode(payload["ct"])
        dek = AESGCM(self._kek).decrypt(kek_nonce, wrapped_dek, None)
        return AESGCM(dek).decrypt(dek_nonce, ct, None)


class AwsKmsClient:
    """AWS KMS 适配器（生产路径）：DEK 由 KMS generate_data_key 生成并托管。

    仅当 settings.kms_provider=="aws" 时启用；boto3 懒导入，默认不引入该依赖。
    """

    def __init__(self, key_id: str):
        import boto3  # 懒导入：非 aws 模式无需安装

        self._kms = boto3.client("kms")
        self._key_id = key_id

    def encrypt(self, plaintext: bytes) -> str:
        resp = self._kms.generate_data_key(KeyId=self._key_id, KeySpec="AES_256")
        dek = resp["Plaintext"]
        wrapped = resp["CiphertextBlob"]
        dek_nonce = os.urandom(12)
        ct = AESGCM(dek).encrypt(dek_nonce, plaintext, None)
        payload = {
            "v": TOKEN_VERSION,
            "wd": base64.b64encode(wrapped).decode(),
            "dn": base64.b64encode(dek_nonce).decode(),
            "ct": base64.b64encode(ct).decode(),
        }
        return base64.b64encode(json.dumps(payload).encode()).decode()

    def decrypt(self, token: str) -> bytes:
        payload = json.loads(base64.b64decode(token))
        wrapped = base64.b64decode(payload["wd"])
        dek = self._kms.decrypt(CiphertextBlob=wrapped)["Plaintext"]
        dek_nonce = base64.b64decode(payload["dn"])
        ct = base64.b64decode(payload["ct"])
        return AESGCM(dek).decrypt(dek_nonce, ct, None)


_KMS: KmsClient | None = None


def get_kms() -> KmsClient:
    """按配置返回 KMS 单例（默认本地 KMS）。"""
    global _KMS
    if _KMS is None:
        if settings.kms_provider == "aws":
            _KMS = AwsKmsClient(settings.kms_aws_key_id)
        else:
            _KMS = LocalKmsClient()
    return _KMS


def reset_kms() -> None:
    """测试用：清除单例缓存。"""
    global _KMS
    _KMS = None
