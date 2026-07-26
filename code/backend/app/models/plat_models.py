"""平台 / 数据中台模块表（plat_*，技术架构第11.2/15.4章）。

- plat_model_pred_log 含 adopted 字段，支撑 AI 反馈闭环（human-in-the-loop，第15.4章）。
- plat_audit_log 全量审计留痕 + 哈希链防篡改（第10.2/13章，P4）。
- plat_account 后台账号：双因子 TOTP 密钥落库（P4）。
"""
from datetime import datetime

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.encrypted_field import EncryptedString
from app.models.base import Base, TimestampMixin


class PlatDataAsset(Base, TimestampMixin):
    __tablename__ = "plat_data_asset"
    name: Mapped[str | None] = mapped_column(String(64))
    owner: Mapped[str | None] = mapped_column(String(32))
    sensitivity_level: Mapped[str | None] = mapped_column(String(16))  # L1-L4
    usage_scope: Mapped[str | None] = mapped_column(String(255))
    quality_score: Mapped[float | None] = mapped_column()
    update_freq: Mapped[str | None] = mapped_column(String(32))
    lineage_json: Mapped[dict | None] = mapped_column(JSON)


class PlatAiModel(Base, TimestampMixin):
    __tablename__ = "plat_ai_model"
    name: Mapped[str | None] = mapped_column(String(64))
    version: Mapped[str | None] = mapped_column(String(32))
    train_dataset_id: Mapped[int | None] = mapped_column(Integer)
    algo_type: Mapped[str | None] = mapped_column(String(32))
    metrics_json: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(16), default="offline")
    online_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    offline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PlatModelPredLog(Base, TimestampMixin):
    __tablename__ = "plat_model_pred_log"
    model_id: Mapped[int | None] = mapped_column(ForeignKey("plat_ai_model.id"), index=True, nullable=True)
    version: Mapped[str | None] = mapped_column(String(32))
    input_features_json: Mapped[dict | None] = mapped_column(JSON)
    predict_result_json: Mapped[dict | None] = mapped_column(JSON)
    predict_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_id: Mapped[int | None] = mapped_column(Integer)
    adopted: Mapped[str | None] = mapped_column(String(16), default="pending")  # pending/adopted/rejected（第15.4章）


class PlatAuditLog(Base, TimestampMixin):
    """全量审计留痕（第10.2/13章）。

    P4 防篡改：每条记录携带 seq_no（单调递增序号）、prev_hash（上一条的 hash）、
    hash（本条内容的 SHA-256）。任一记录被篡改，其 hash 或下游 prev_hash 必然失配，
    verify_audit_chain 可定位首个断裂点，作为等保三级"审计记录防篡改"证据。
    """

    __tablename__ = "plat_audit_log"
    actor_id: Mapped[int | None] = mapped_column(Integer)
    role: Mapped[str | None] = mapped_column(String(16))
    action: Mapped[str | None] = mapped_column(String(64))
    resource: Mapped[str | None] = mapped_column(String(128))
    before_json: Mapped[dict | None] = mapped_column(JSON)
    after_json: Mapped[dict | None] = mapped_column(JSON)
    ip: Mapped[str | None] = mapped_column(String(64))
    seq_no: Mapped[int] = mapped_column(Integer, default=0, index=True)
    prev_hash: Mapped[str] = mapped_column(String(64), default="")
    hash: Mapped[str] = mapped_column(String(64), default="", index=True)


class PlatAccount(Base, TimestampMixin):
    """后台账号（P4 安全闭环）：platform/xingyao/store/therapist 密码登录。

    - 密码经 PBKDF2-HMAC-SHA256 加盐哈希落库（core.security.hash_password）。
    - two_factor_enabled + totp_secret：双因子（TOTP）真校验（P4）。
    - dev-token 仅调试态可用，正式登录走 /auth/login。
    """

    __tablename__ = "plat_account"
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(16))  # platform/xingyao/store/therapist
    store_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    password_salt: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="active")  # active/disabled
    two_factor_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    # ⚠️ 高风险字段：经 KMS 信封加密落库（等保三级增强，本次）。
    # 底层 Text，ORM 读写透明加解密；auth.py / seed.py 调用点不变。
    totp_secret: Mapped[str] = mapped_column(EncryptedString, default="")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ===================== P6: 合规采集审核 =====================
class PlatComplianceItem(Base, TimestampMixin):
    """合规采集与审核工单（等保三级 / 执业资质 / 隐私合规，PRD 合规清单）。"""

    __tablename__ = "plat_compliance_item"
    category: Mapped[str] = mapped_column(String(32), index=True)  # qualification/license/privacy/security/...
    subject_type: Mapped[str] = mapped_column(String(32))  # doctor/store/therapist/platform
    subject_id: Mapped[int | None] = mapped_column(Integer, index=True)
    title: Mapped[str] = mapped_column(String(128))
    content_json: Mapped[dict | None] = mapped_column(JSON)
    submitter_id: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending/approved/rejected
    reviewer_id: Mapped[int | None] = mapped_column(Integer)
    review_note: Mapped[str | None] = mapped_column(String(512))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
