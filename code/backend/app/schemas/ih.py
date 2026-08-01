"""互联网医院模块 Schema（技术架构第11.2章）。"""
from datetime import date, datetime, time
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.common import BaseOut


# ---------------- 用户 ----------------
class UserLoginWxIn(BaseModel):
    code: str  # 微信 wx.login code；未配置 appid 时作为开发模式标识
    phone_mask: Optional[str] = None
    real_name_mask: Optional[str] = None


class UserCreate(BaseModel):
    openid: str
    phone_mask: Optional[str] = None
    real_name_mask: Optional[str] = None
    id_card_mask: Optional[str] = None
    user_type: Optional[str] = None


class UserOut(BaseOut):
    openid: str
    real_name_mask: Optional[str] = None
    phone_mask: Optional[str] = None
    id_card_mask: Optional[str] = None
    user_type: Optional[str] = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------------- 医师 ----------------
class DoctorCreate(BaseModel):
    user_id: int
    license_no: str
    title: Optional[str] = None
    hospital_id: Optional[int] = None
    dept: Optional[str] = None
    good_at: Optional[str] = None
    consult_price: Optional[int] = None
    status: str = "pending"


class DoctorOut(BaseOut):
    user_id: int
    license_no: str
    title: Optional[str] = None
    hospital_id: Optional[int] = None
    dept: Optional[str] = None
    good_at: Optional[str] = None
    consult_price: Optional[int] = None
    status: str


class DoctorAuditIn(BaseModel):
    """医师入驻审核（通过/驳回）。"""
    action: str  # approve / reject
    reviewer_id: int
    note: Optional[str] = None


# ---------------- 处方 ----------------
class PrescriptionItemIn(BaseModel):
    name: str
    drug_id: Optional[int] = None
    spec: Optional[str] = None
    dosage: Optional[str] = None
    freq: Optional[str] = None
    qty: Optional[int] = None
    daily_dose: Optional[float] = None  # 单日用量（mg），合理用药剂量告警
    max_daily_dose: Optional[float] = None  # 单日安全上限（mg）


class PrescriptionCreate(BaseModel):
    patient_id: int
    doctor_id: int
    diagnose: Optional[str] = None
    items: list[PrescriptionItemIn] = []
    patient_pregnancy: bool = False  # 是否妊娠（禁忌校验）
    patient_allergies: list[str] = []  # 过敏药物/成分
    syndrug_check: bool = False
    signature_url: Optional[str] = None


class PrescriptionAuditIn(BaseModel):
    action: str  # approve | reject
    reviewer_id: int
    note: Optional[str] = None


class PrescriptionOut(BaseOut):
    prescription_no: str
    patient_id: int
    doctor_id: int
    pharmacist_id: Optional[int] = None
    diagnose: Optional[str] = None
    items_json: Any = None
    status: str
    signature_url: Optional[str] = None
    audit_at: Optional[datetime] = None
    rx_check_json: Optional[dict] = None


# ---------------- 订单 ----------------
class OrderCreate(BaseModel):
    user_id: int
    type: str = "otc"  # rx | otc
    amount: int = 0
    prescription_id: Optional[int] = None  # 处方药凭方购买：rx 类型必传


class OrderPayIn(BaseModel):
    channel: str = "wechat"


class OrderOut(BaseOut):
    order_no: str
    user_id: int
    type: str
    amount: int
    pay_status: str
    prescription_id: Optional[int] = None  # 处方药凭方购买关联处方


# ---------------- 在线复诊（会话 + 消息） ----------------
class ConsultationCreate(BaseModel):
    patient_id: int
    doctor_id: int
    order_id: Optional[int] = None
    chief_complaint: Optional[str] = None


class ConsultationMessageCreate(BaseModel):
    sender_role: str  # patient / doctor / platform
    sender_id: int
    msg_type: str = "text"  # text / image / voice
    content: str


class ConsultationMessageOut(BaseOut):
    consultation_id: int
    sender_role: str
    sender_id: int
    msg_type: str
    content: str


class ConsultationOut(BaseOut):
    consultation_no: str
    patient_id: int
    doctor_id: int
    order_id: Optional[int] = None
    chief_complaint: Optional[str] = None
    status: str
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None


# ---------------- P6: 医生排班 ----------------
class DoctorScheduleCreate(BaseModel):
    doctor_id: Optional[int] = None  # doctor 角色留空，由服务端解析本人
    work_date: date
    am_pm: str = "morning"  # morning/afternoon/evening
    start_time: time
    end_time: time
    capacity: int = 1
    remark: Optional[str] = None


class DoctorScheduleUpdate(BaseModel):
    work_date: Optional[date] = None
    am_pm: Optional[str] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    status: Optional[str] = None  # open/closed
    capacity: Optional[int] = None
    remark: Optional[str] = None


class DoctorScheduleOut(BaseOut):
    doctor_id: int
    work_date: date
    am_pm: str
    start_time: time
    end_time: time
    status: str
    capacity: int
    remark: Optional[str] = None


# ---------------- P6: 药品目录 ----------------
class DrugCreate(BaseModel):
    name: str
    spec: Optional[str] = None
    manufacturer: Optional[str] = None
    otc_type: str = "otc"  # otc/rx
    category: Optional[str] = None
    unit: Optional[str] = None
    price: Optional[int] = None  # 分
    status: str = "on"  # on/off


class DrugUpdate(BaseModel):
    name: Optional[str] = None
    spec: Optional[str] = None
    manufacturer: Optional[str] = None
    otc_type: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    price: Optional[int] = None
    status: Optional[str] = None


class DrugOut(BaseOut):
    name: str
    spec: Optional[str] = None
    manufacturer: Optional[str] = None
    otc_type: str
    category: Optional[str] = None
    unit: Optional[str] = None
    price: Optional[int] = None
    status: str
