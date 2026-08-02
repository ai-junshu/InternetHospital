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
    # H6：科室外键化。dept_id 关联 ih_department（nullable，平滑迁移）。
    # dept 字符串保留作冗余过渡，便于历史数据与新结构并存。
    dept_id: Mapped[int | None] = mapped_column(
        ForeignKey("ih_department.id"), nullable=True, index=True
    )
    dept: Mapped[str | None] = mapped_column(String(32))
    good_at: Mapped[str | None] = mapped_column(String(255))
    consult_price: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="pending")


class IhPharmacist(Base, TimestampMixin):
    """药师档案（互联网医院审方主体，技术架构第11.2章）。

    与 IhDoctor 同构：药师身份持久化，使 role=pharmacist 的 JWT 能关联到真实档案，
    符合等保三级"身份可追溯、审方责任到人"要求。
    """

    __tablename__ = "ih_pharmacist"
    user_id: Mapped[int] = mapped_column(ForeignKey("ih_user.id"), index=True)
    license_no: Mapped[str] = mapped_column(String(64), unique=True)  # 执业药师证书编号
    title: Mapped[str | None] = mapped_column(String(32))
    pharmacy_id: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="active")  # active/pending/disabled


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
    prescription_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
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


class IhPharmacy(Base, TimestampMixin):
    """合作药房（互联网医院处方药履约节点，PRD 3.3.2 药房管理）。

    作为药品库存、药师归属的实体承接方；IhPharmacist.pharmacy_id 关联本表。
    """

    __tablename__ = "ih_pharmacy"
    name: Mapped[str] = mapped_column(String(128), index=True)
    region: Mapped[str | None] = mapped_column(String(64))  # 区域/城市
    license_no: Mapped[str | None] = mapped_column(String(64))  # 药品经营许可证号
    contact: Mapped[str | None] = mapped_column(String(64))  # 联系人/电话（脱敏）
    status: Mapped[str] = mapped_column(String(16), default="active")  # active/disabled


class IhDrugStock(Base, TimestampMixin):
    """药品库存（按 药房×药品 维度，PRD 3.3.2 药房库存管理）。

    与 ih_drug 解耦，库存频繁变动不污染药品目录；联合唯一约束（drug_id, pharmacy_id）。
    """

    __tablename__ = "ih_drug_stock"
    drug_id: Mapped[int] = mapped_column(ForeignKey("ih_drug.id"), index=True)
    pharmacy_id: Mapped[int] = mapped_column(ForeignKey("ih_pharmacy.id"), index=True)
    stock: Mapped[int] = mapped_column(Integer, default=0)  # 当前库存
    safety_stock: Mapped[int] = mapped_column(Integer, default=0)  # 安全库存阈值


class IhComplaint(Base, TimestampMixin):
    """投诉与售后（PRD 3.3.4 投诉与售后，患者权益闭环）。

    order_id 关联 IhOrder（含 prescription_id/type），user_id 关联 IhUser（脱敏展示）。
    状态机：pending → processing → resolved/closed。
    """

    __tablename__ = "ih_complaint"
    order_id: Mapped[int | None] = mapped_column(Integer, index=True)  # 关联 ih_order.id
    user_id: Mapped[int | None] = mapped_column(Integer, index=True)  # 关联 ih_user.id（脱敏）
    type: Mapped[str] = mapped_column(String(16), default="service")  # quality/service/refund
    content: Mapped[str] = mapped_column(String(1024))
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending/processing/resolved/closed
    reply: Mapped[str | None] = mapped_column(String(1024))  # 处理回复


class IhDepartment(Base, TimestampMixin):
    """科室结构（PRD 3.3 医院管理，组织管理维度）。

    本次仅建表 + CRUD；IhDoctor.dept 保持 String 命名冗余，不在本次外键化（避免波及医师链路）。
    """

    __tablename__ = "ih_department"
    name: Mapped[str] = mapped_column(String(64), index=True)
    head: Mapped[str | None] = mapped_column(String(64))  # 科室主任
    remark: Mapped[str | None] = mapped_column(String(255))
