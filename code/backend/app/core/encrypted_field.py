"""透明字段级加密类型（落库加密，等保三级增强）。

基于 SQLAlchemy TypeDecorator，在 ORM 读写时自动加解密，调用点（auth.py / seed.py /
schema）零改动：
- EncryptedString：底层 Text，适用于 totp_secret 等字符串字段。
- EncryptedJSON：底层 Text，json.dumps/loads 包裹，适用于 health_tags 等 JSON 字段。

明文仅在内存短暂出现，落库全为密文；加解密经由 KMS（app.core.kms.get_kms）。
"""
import json

from sqlalchemy import Text, TypeDecorator

from app.core.kms import get_kms


class EncryptedString(TypeDecorator):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return get_kms().encrypt(value.encode("utf-8"))

    def process_result_value(self, value, dialect):
        if value is None or value == "":
            return value
        return get_kms().decrypt(value).decode("utf-8")


class EncryptedJSON(TypeDecorator):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        blob = json.dumps(value, ensure_ascii=False).encode("utf-8")
        return get_kms().encrypt(blob)

    def process_result_value(self, value, dialect):
        if value is None or value == "":
            return value
        return json.loads(get_kms().decrypt(value).decode("utf-8"))
