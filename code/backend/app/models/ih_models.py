"""互联网医院模块表（ih_*，技术架构第11.2章）。"""
from datetime import date, datetime, time

from sqlalchemy import JSON, BigInteger, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class IhUser(Base, TimestampMixin):
    __tablename__ = "ih_user"
    openid: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    real_name_mask: Mapped[str | None] = mapped_column(String(32))  # 脱敏存储
    phone_mask: Mapped[str | None] = mapped_column(String(32))
    id_card_mask: Mapped[str | None] = mapped_column(String(32))
    user_type: Mapped[str | None] = mapped_column(String(16))


class IhDoctor(Base, TimestampMixin):
    __tablename__ = "ih_doctor"
    user_id: Mapped[int] = mapped_column(ForeignKey("ih_user.id"), index=True)
    license_no: Mapped[str] = mapped_column(String(64), unique=True)  # 执业证书编号
    title: Mapped[str | None] = mapped_column(String(32))
    hospital_id: Mapped[int | None] = mapped_column(Integer)
    dept: Mapped[str | None] = mapped_column(String(32))
    good_at: Mapped[str | None] = mapped_column(String(255))
    consult_price: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="pending")


class IhPrescription(Base, TimestampMixin):
    __tablename__ = "ih_prescription"
    prescription_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("ih_user.id"), index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("ih_doctor.id"), index=True)
    pharmacist_id: Mapped[int | None] = mapped_column(Integer)
    diagnose: Mapped[str | None] = mapped_column(String(255))
    items_json: Mapped[dict] = mapped_column(JSON)  # 处方清单
    status: Mapped[str] = mapped_column(String(16), default="pending_audit")  # 待审核/通过/驳回
    signature_url: Mapped[str | None] = mapped_column(String(255))  # 电子签名
    audit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rx_check_json: Mapped[dict | None] = mapped_column(JSON)  # 合理用药引擎前置校验结果


class IhPrescriptionItem(Base, TimestampMixin):
    __tablename__ = "ih_prescription_item"
    prescription_id: Mapped[int] = mapped_column(
        ForeignKey("ih_prescription.id"), index=True
    )
    drug_id: Mapped[int | None] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(64))
    spec: Mapped[str | None] = mapped_column(String(64))
    dosage: Mapped[str | None] = mapped_column(String(64))
    freq: Mapped[str | None] = mapped_column(String(64))
    qty: Mapped[int | None] = mapped_column(Integer)
    daily_dose: Mapped[float | None] = mapped_column(Float, nullable=True)  # 单日用量（mg）
    max_daily_dose: Mapped[float | None] = mapped_column(Float, nullable=True)  # 单日安全上限（mg）


class IhOrder(Base, TimestampMixin):
    __tablename__ = "ih_order"
    order_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("ih_user.id"), index=True)
    type: Mapped[str] = mapped_column(String(16))  # rx / otc
    amount: Mapped[int] = mapped_column(Integer)
    pay_status: Mapped[str] = mapped_column(String(16), default="unpaid")


class IhPayment(Base, TimestampMixin):
    __tablename__ = "ih_payment"
    order_no: Mapped[str] = mapped_column(String(64), index=True)
    transaction_id: Mapped[str | None] = mapped_column(String(64))
    mch_id: Mapped[str | None] = mapped_column(String(64))
    amount: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(8), default="CNY")
    pay_channel: Mapped[str] = mapped_column(String(16), default="wechat")
    trade_state: Mapped[str | None] = mapped_column(String(16))
    refund_status: Mapped[str | None] = mapped_column(String(16))
    prepay_id: Mapped[str | None] = mapped_column(String(64))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notify_raw_json: Mapped[dict | None] = mapped_column(JSON)


class IhSmsLog(Base, TimestampMixin):
    __tablename__ = "ih_sms_log"
    phone_mask: Mapped[str | None] = mapped_column(String(32))
    scene: Mapped[str] = mapped_column(String(32))  # 验证码/订单/复诊/营销
    template_code: Mapped[str | None] = mapped_column(String(64))
    content_mask: Mapped[str | None] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(16), default="sending")  # sending/success/failed
    provider: Mapped[str | None] = mapped_column(String(32))
    send_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    receipt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_msg: Mapped[str | None] = mapped_column(String(255))


class IhConsultation(Base, TimestampMixin):
    """在线复诊会话（技术架构第11.2章 / PRD 3.1.3-3.1.4）。

    闭环：患者支付复诊/咨询费(ih_order.type=consult) → 创建会话(open) →
    医师接诊(start, ongoing) → 图文沟通 → 医师开方(见 ih_prescription) → 结束(end)。
    """

    __tablename__ = "ih_consultation"
    consultation_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("ih_user.id"), index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("ih_doctor.id"), index=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("ih_order.id"), nullable=True)
    chief_complaint: Mapped[str | None] = mapped_column(String(512))  # 主诉
    status: Mapped[str] = mapped_column(String(16), default="open")  # open/ongoing/ended
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IhConsultationMessage(Base, TimestampMixin):
    """在线复诊会话消息（图文/语音，PRD 3.1.3 图文问诊）。"""

    __tablename__ = "ih_consultation_message"
    consultation_id: Mapped[int] = mapped_column(
        ForeignKey("ih_consultation.id"), index=True
    )
    sender_role: Mapped[str] = mapped_column(String(16))  # patient/doctor/platform
    sender_id: Mapped[int] = mapped_column(Integer)
    msg_type: Mapped[str] = mapped_column(String(16), default="text")  # text/image/voice
    content: Mapped[str] = mapped_column(String(2048))


# ===================== P6: 医生排班 / 药品目录 =====================
class IhDoctorSchedule(Base, TimestampMixin):
    """医生排班（互联网医院在线复诊产能，技术架构 11.2 / PRD 3.1.4）。"""

    __tablename__ = "ih_doctor_schedule"
    doctor_id: Mapped[int] = mapped_column(ForeignKey("ih_doctor.id"), index=True)
    work_date: Mapped[date] = mapped_column(Date, index=True)
    am_pm: Mapped[str] = mapped_column(String(16), default="morning")  # morning/afternoon/evening
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    status: Mapped[str] = mapped_column(String(16), default="open")  # open/closed
    capacity: Mapped[int] = mapped_column(Integer, default=1)
    remark: Mapped[str | None] = mapped_column(String(255))


class IhDrug(Base, TimestampMixin):
    """药品目录（电子处方可开方药品，PRD 3.1.3）。"""

    __tablename__ = "ih_drug"
    name: Mapped[str] = mapped_column(String(128), index=True)
    spec: Mapped[str | None] = mapped_column(String(128))
    manufacturer: Mapped[str | None] = mapped_column(String(128))
    otc_type: Mapped[str] = mapped_column(String(16), default="otc")  # otc/rx
    category: Mapped[str | None] = mapped_column(String(64))
    unit: Mapped[str | None] = mapped_column(String(16))
    price: Mapped[int | None] = mapped_column(Integer)  # 单位：分
    status: Mapped[str] = mapped_column(String(16), default="on")  # on/off
