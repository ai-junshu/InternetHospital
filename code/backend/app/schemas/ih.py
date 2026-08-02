"""互联网医院模块 Schema（技术架构第11.2章）。"""
from datetime import date, datetime, time
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.common import BaseOut


# ---------------- 用户 ----------------
class UserLoginWxIn(BaseModel):
    code: str  # 微信 wx.login code；未配置 appid 时作为开发模式标识
    role: str = "patient"  # 登录身份：patient / doctor / pharmacist（迭代 A · S1 双身份）
    doctor_id: Optional[int] = None  # 医师身份联调时可直接传入档案 id
    pharmacist_id: Optional[int] = None  # 药师身份联调时可直接传入档案 id
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
    role: str = "patient"  # 透传前端路由用


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
    dept_id: Optional[int] = None  # H6：关联科室 id（替代 dept 字符串）
    dept: Optional[str] = None     # 冗余过渡字段，可空
    good_at: Optional[str] = None
    consult_price: Optional[int] = None
    status: str = "pending"


class DoctorOut(BaseOut):
    user_id: int
    license_no: str
    title: Optional[str] = None
    hospital_id: Optional[int] = None
    dept_id: Optional[int] = None   # H6：关联科室 id
    dept: Optional[str] = None      # 冗余过渡字段
    dept_name: Optional[str] = None  # H6：返回时联表填充的科室名称
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
    reviewer_id: Optional[int] = None  # 保留兼容，后端以 JWT 主体为准（等保三级审计链）
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
    description: Optional[str] = None  # 支付单备注（如"医疗订单 ORDxxxx"）
    openid: Optional[str] = None      # 拉起支付的小程序用户 openid


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


# ---------------- 合作药房 ----------------
class PharmacyCreate(BaseModel):
    name: str
    region: Optional[str] = None
    license_no: Optional[str] = None
    contact: Optional[str] = None
    status: str = "active"


class PharmacyUpdate(BaseModel):
    name: Optional[str] = None
    region: Optional[str] = None
    license_no: Optional[str] = None
    contact: Optional[str] = None
    status: Optional[str] = None


class PharmacyOut(BaseOut):
    name: str
    region: Optional[str] = None
    license_no: Optional[str] = None
    contact: Optional[str] = None
    status: str


# ---------------- 药品库存 ----------------
class DrugStockCreate(BaseModel):
    drug_id: int
    pharmacy_id: int
    stock: int = 0
    safety_stock: int = 0


class DrugStockAdjust(BaseModel):
    """库存出入库调整：delta_stock 为增减量（正=入库，负=出库），按当前库存累加。

    direction/in_out 仅作审计语义标记，实际增减以 delta_stock 符号为准。
    """

    delta_stock: int  # 必传，负数为出库，正数为入库
    reason: Optional[str] = None  # 出入库事由（审计留痕）
    safety_stock: Optional[int] = None  # 可选同步调整安全库存阈值（设值语义）


class DrugStockOut(BaseOut):
    drug_id: int
    pharmacy_id: int
    stock: int
    safety_stock: int
    is_low: bool = False  # 低于安全库存阈值（计算字段，审计快照允许默认）


# ---------------- 投诉与售后 ----------------
class ComplaintCreate(BaseModel):
    order_id: int | None = None
    user_id: int | None = None
    type: str = "service"  # quality/service/refund
    content: str


class ComplaintReply(BaseModel):
    status: str  # processing/resolved/closed
    reply: str | None = None


class ComplaintOut(BaseOut):
    order_id: int | None
    user_id: int | None
    type: str
    content: str
    status: str
    reply: str | None


# ---------------- 科室结构 ----------------
class DepartmentCreate(BaseModel):
    name: str
    head: Optional[str] = None
    remark: Optional[str] = None


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    head: Optional[str] = None
    remark: Optional[str] = None


class DepartmentOut(BaseOut):
    name: str
    head: Optional[str] = None
    remark: Optional[str] = None
