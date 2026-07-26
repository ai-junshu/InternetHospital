"""落库加密验证（字段级信封加密，等保三级增强）。

- 单测：KMS 信封加解密往返、错误主密钥解密失败（完整性）、EncryptedString/JSON 透明往返。
- 集成：用 SQLite 内存库验证 ORM 写入后 DB 落密文、ORM 读回明文（调用点零改动）。
"""
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.kms import LocalKmsClient, looks_encrypted
from app.core.encrypted_field import EncryptedString, EncryptedJSON
from app.models.plat_models import PlatAccount
from app.models.mt_models import MtCustomer


def test_kms_roundtrip():
    k = LocalKmsClient("master-key-1")
    ct = k.encrypt(b"secret-totp")
    assert ct != "secret-totp"
    assert looks_encrypted(ct)
    assert k.decrypt(ct) == b"secret-totp"


def test_kms_wrong_key_fails():
    k1 = LocalKmsClient("master-key-1")
    k2 = LocalKmsClient("master-key-2")
    ct = k1.encrypt(b"secret-totp")
    with pytest.raises(Exception):
        k2.decrypt(ct)


def test_encrypted_string_roundtrip():
    t = EncryptedString()
    tok = t.process_bind_param("hello", None)
    assert tok != "hello"
    assert t.process_result_value(tok, None) == "hello"
    assert t.process_bind_param(None, None) is None
    assert t.process_result_value(None, None) is None
    assert t.process_result_value("", None) == ""


def test_encrypted_json_roundtrip():
    t = EncryptedJSON()
    data = {"chronic": ["高尿酸"], "tags": ["sleep"]}
    tok = t.process_bind_param(data, None)
    assert t.process_result_value(tok, None) == data
    assert t.process_bind_param(None, None) is None
    assert t.process_result_value("", None) == ""


def test_orm_transparent_encryption_sqlite():
    engine = create_engine("sqlite://")
    PlatAccount.__table__.create(engine, checkfirst=True)
    MtCustomer.__table__.create(engine, checkfirst=True)

    secret = "KRSXG5CTMVRXEZLU"
    with Session(engine) as s:
        acc = PlatAccount(
            id=1,
            username="doc1",
            role="platform",
            password_hash="x",
            password_salt="y",
            totp_secret=secret,
            two_factor_enabled=True,
        )
        cust = MtCustomer(id=1, name_mask="张*", health_tags={"chronic": ["高尿酸"]})
        s.add_all([acc, cust])
        s.commit()

    # 原始读取应为密文（落库全密文）
    with Session(engine) as s:
        raw_secret = s.execute(
            text("SELECT totp_secret FROM plat_account WHERE id=:i"), {"i": 1}
        ).scalar()
        raw_tags = s.execute(
            text("SELECT health_tags FROM mt_customer WHERE id=:i"), {"i": 1}
        ).scalar()
        assert looks_encrypted(raw_secret)
        assert raw_secret != secret
        assert looks_encrypted(raw_tags)

        # ORM 读回应透明解密
        acc2 = s.get(PlatAccount, 1)
        cust2 = s.get(MtCustomer, 1)
        assert acc2.totp_secret == secret
        assert cust2.health_tags == {"chronic": ["高尿酸"]}
