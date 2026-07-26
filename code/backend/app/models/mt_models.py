"""健康数据中台模块表（mt_*，技术架构第11.2章）。

注：mt_treatment_record / mt_customer / mt_store_metrics 均带 store_id（第15.2章 RLS 行级隔离）。
"""
from datetime import date, datetime, time

from sqlalchemy import JSON, BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.core.encrypted_field import EncryptedJSON
from app.models.base import Base, TimestampMixin


class MtCustomer(Base, TimestampMixin):
    __tablename__ = "mt_customer"
    name_mask: Mapped[str | None] = mapped_column(String(32))  # 脱敏
    gender: Mapped[str | None] = mapped_column(String(8))
    birth_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    phone_mask: Mapped[str | None] = mapped_column(String(32))
    source_store_id: Mapped[int | None] = mapped_column(Integer, index=True)
    # 健康档案核心字段：经字段级加密落库（等保三级增强，本次）。底层 Text，透明加解密。
    health_tags: Mapped[dict | None] = mapped_column(EncryptedJSON)
    auth_status: Mapped[str] = mapped_column(String(16), default="unauthorized")
    auth_file_url: Mapped[str | None] = mapped_column(String(255))


class MtPainAssessment(Base, TimestampMixin):
    __tablename__ = "mt_pain_assessment"
    customer_id: Mapped[int] = mapped_column(ForeignKey("mt_customer.id"), index=True)
    assess_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scale_type: Mapped[str | None] = mapped_column(String(16))  # VAS/NRS/McGill
    answers_json: Mapped[dict | None] = mapped_column(JSON)  # 原始答案
    score: Mapped[float | None] = mapped_column()
    pain_site: Mapped[str | None] = mapped_column(String(64))
    pain_nature: Mapped[str | None] = mapped_column(String(64))
    therapist_id: Mapped[int | None] = mapped_column(Integer)


class MtCarePlan(Base, TimestampMixin):
    __tablename__ = "mt_care_plan"
    customer_id: Mapped[int] = mapped_column(ForeignKey("mt_customer.id"), index=True)
    doctor_advice_id: Mapped[int | None] = mapped_column(Integer)
    pain_type: Mapped[str | None] = mapped_column(String(64))
    goal: Mapped[str | None] = mapped_column(String(255))
    cycle: Mapped[str | None] = mapped_column(String(64))
    items_json: Mapped[dict | None] = mapped_column(JSON)
    product_combo_json: Mapped[dict | None] = mapped_column(JSON)
    reeval_nodes: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(16), default="active")


class MtTreatmentRecord(Base, TimestampMixin):
    __tablename__ = "mt_treatment_record"
    customer_id: Mapped[int] = mapped_column(ForeignKey("mt_customer.id"), index=True)
    store_id: Mapped[int] = mapped_column(Integer, index=True)  # RLS 行级隔离键
    therapist_id: Mapped[int | None] = mapped_column(Integer)
    plan_id: Mapped[int | None] = mapped_column(Integer)
    service_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    products_json: Mapped[dict | None] = mapped_column(JSON)
    oper_sites_json: Mapped[dict | None] = mapped_column(JSON)
    nps: Mapped[int | None] = mapped_column(Integer)  # 满意度
    images_json: Mapped[dict | None] = mapped_column(JSON)
    remark: Mapped[str | None] = mapped_column(String(512))
    # 不可删仅可更正留痕（第11.2章）


class MtEffectTracking(Base, TimestampMixin):
    __tablename__ = "mt_effect_tracking"
    customer_id: Mapped[int] = mapped_column(ForeignKey("mt_customer.id"), index=True)
    plan_id: Mapped[int | None] = mapped_column(Integer)
    assess_seq_json: Mapped[dict | None] = mapped_column(JSON)
    effect_level: Mapped[str | None] = mapped_column(String(16))  # significant/effective/ineffective/worsened
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MtRepurchasePrediction(Base, TimestampMixin):
    __tablename__ = "mt_repurchase_prediction"
    customer_id: Mapped[int] = mapped_column(ForeignKey("mt_customer.id"), index=True)
    predict_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_visit_prob: Mapped[float | None] = mapped_column()
    repurchase_prob: Mapped[float | None] = mapped_column()
    risk_level: Mapped[str | None] = mapped_column(String(16))  # high/medium/low
    model_version: Mapped[str | None] = mapped_column(String(32))


class MtRiskProfile(Base, TimestampMixin):
    __tablename__ = "mt_risk_profile"
    customer_id: Mapped[int] = mapped_column(ForeignKey("mt_customer.id"), index=True)
    predict_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pain_risk: Mapped[str | None] = mapped_column(String(16))  # high/medium/low
    comorbidity_risk: Mapped[str | None] = mapped_column(String(16))
    model_version: Mapped[str | None] = mapped_column(String(32))


class MtStore(Base, TimestampMixin):
    __tablename__ = "mt_store"
    name: Mapped[str | None] = mapped_column(String(64))
    region: Mapped[str | None] = mapped_column(String(64))
    city: Mapped[str | None] = mapped_column(String(64))
    type: Mapped[str | None] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="active")


class MtTherapist(Base, TimestampMixin):
    __tablename__ = "mt_therapist"
    name: Mapped[str | None] = mapped_column(String(32))
    license_no: Mapped[str | None] = mapped_column(String(64))
    store_id: Mapped[int] = mapped_column(Integer, index=True)
    skill_tags: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(16), default="active")


# ===================== P6: 调理师排班 / 标签 =====================
class MtTherapistSchedule(Base, TimestampMixin):
    """调理师排班（门店到店产能，健康数据中台）。"""

    __tablename__ = "mt_therapist_schedule"
    therapist_id: Mapped[int] = mapped_column(ForeignKey("mt_therapist.id"), index=True)
    store_id: Mapped[int] = mapped_column(Integer, index=True)
    work_date: Mapped[date] = mapped_column(Date, index=True)
    am_pm: Mapped[str] = mapped_column(String(16), default="morning")  # morning/afternoon/evening
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    status: Mapped[str] = mapped_column(String(16), default="open")  # open/closed
    capacity: Mapped[int] = mapped_column(Integer, default=1)
    remark: Mapped[str | None] = mapped_column(String(255))


class MtTherapistTag(Base, TimestampMixin):
    """调理师标签目录（技能 / 健康 / 服务标签）。"""

    __tablename__ = "mt_therapist_tag"
    name: Mapped[str] = mapped_column(String(64), unique=True)
    category: Mapped[str | None] = mapped_column(String(32))  # skill/health/service
    description: Mapped[str | None] = mapped_column(String(255))


class MtTherapistTagRel(Base, TimestampMixin):
    """调理师-标签关联（分配标签）。"""

    __tablename__ = "mt_therapist_tag_rel"
    therapist_id: Mapped[int] = mapped_column(ForeignKey("mt_therapist.id"), index=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("mt_therapist_tag.id"), index=True)
    assigned_by: Mapped[int | None] = mapped_column(Integer)
