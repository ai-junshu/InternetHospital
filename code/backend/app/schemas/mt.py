"""健康数据中台模块 Schema（技术架构第11.2章）。"""
from datetime import date, datetime, time
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.common import BaseOut


# ---------------- 客户 ----------------
class CustomerCreate(BaseModel):
    name_mask: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[datetime] = None
    phone_mask: Optional[str] = None
    source_store_id: Optional[int] = None
    health_tags: Optional[dict] = None
    auth_status: str = "unauthorized"
    auth_file_url: Optional[str] = None


class CustomerAuthorizeIn(BaseModel):
    auth_file_url: Optional[str] = None


class CustomerOut(BaseOut):
    name_mask: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[datetime] = None
    phone_mask: Optional[str] = None
    source_store_id: Optional[int] = None
    health_tags: Optional[dict] = None
    auth_status: str


# ---------------- 疼痛评估 ----------------
class PainAssessmentCreate(BaseModel):
    customer_id: int
    assess_time: Optional[datetime] = None
    scale_type: Optional[str] = None
    answers_json: Optional[dict] = None
    score: Optional[float] = None
    pain_site: Optional[str] = None
    pain_nature: Optional[str] = None
    therapist_id: Optional[int] = None


class PainAssessmentOut(BaseOut):
    customer_id: int
    assess_time: Optional[datetime] = None
    scale_type: Optional[str] = None
    answers_json: Optional[dict] = None
    score: Optional[float] = None
    pain_site: Optional[str] = None
    pain_nature: Optional[str] = None
    therapist_id: Optional[int] = None


# ---------------- 调理方案 ----------------
class CarePlanCreate(BaseModel):
    customer_id: int
    source_store_id: Optional[int] = None
    created_by: Optional[int] = None
    doctor_advice_id: int  # 强制关联执业医师出具的方案建议/处方 ID（合规强规则1）
    pain_type: Optional[str] = None
    goal: Optional[str] = None
    cycle: Optional[str] = None
    age: Optional[int] = None
    pain_score: Optional[int] = None
    chronic_count: Optional[int] = None


class CarePlanOut(BaseOut):
    customer_id: int
    doctor_advice_id: Optional[int] = None
    pain_type: Optional[str] = None
    goal: Optional[str] = None
    cycle: Optional[str] = None
    items_json: Any = None
    product_combo_json: Any = None
    reeval_nodes: Any = None
    status: str


# ---------------- 治疗记录 ----------------
class TreatmentRecordCreate(BaseModel):
    customer_id: int
    store_id: int
    therapist_id: Optional[int] = None
    plan_id: Optional[int] = None
    service_time: Optional[datetime] = None
    products_json: Optional[dict] = None
    oper_sites_json: Optional[dict] = None
    nps: Optional[int] = None
    images_json: Optional[dict] = None
    remark: Optional[str] = None


class TreatmentRecordOut(BaseOut):
    customer_id: int
    store_id: int
    therapist_id: Optional[int] = None
    plan_id: Optional[int] = None
    service_time: Optional[datetime] = None
    products_json: Optional[dict] = None
    oper_sites_json: Optional[dict] = None
    nps: Optional[int] = None
    images_json: Optional[dict] = None
    remark: Optional[str] = None


class TreatmentRecordReviseIn(BaseModel):
    """治疗记录更正（合规强规则2：不可删，仅可更正留痕）。"""
    products_json: Optional[dict] = None
    oper_sites_json: Optional[dict] = None
    nps: Optional[int] = None
    images_json: Optional[dict] = None
    remark: Optional[str] = None
    reason: Optional[str] = None  # 更正事由，留痕必填建议


class TreatmentRecordRevisionOut(BaseOut):
    record_id: int
    revised_by: Optional[int] = None
    revised_by_role: Optional[str] = None
    before_json: Any = None
    after_json: Any = None
    reason: Optional[str] = None


# ---------------- 门店 / 调理师 ----------------
class StoreOut(BaseOut):
    name: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    type: Optional[str] = None
    status: str


class TherapistOut(BaseOut):
    name: Optional[str] = None
    license_no: Optional[str] = None
    store_id: int
    skill_tags: Optional[dict] = None
    status: str


# ---------------- 复购预测（AI 反馈闭环，第15.4章） ----------------
class RepurchasePredictIn(BaseModel):
    customer_id: int
    age: int = 40
    visit_freq: float = 3.0
    last_gap_days: float = 30.0


class RepurchasePredictionOut(BaseOut):
    customer_id: int
    predict_time: Optional[datetime] = None
    next_visit_prob: Optional[float] = None
    repurchase_prob: Optional[float] = None
    risk_level: Optional[str] = None
    model_version: Optional[str] = None


# ---------------- 风险画像（AI 反馈闭环，第15.4章） ----------------
class RiskProfileIn(BaseModel):
    customer_id: int
    age: int = 45
    bmi: float = 24.0
    comorbidity_count: int = 0


class RiskProfileOut(BaseOut):
    customer_id: int
    predict_time: Optional[datetime] = None
    pain_risk: Optional[str] = None
    comorbidity_risk: Optional[str] = None
    model_version: Optional[str] = None


# ---------------- 门店经营宽表（第11.3章） ----------------
class StoreMetricsOut(BaseOut):
    date: Optional[str] = None
    store_id: Optional[int] = None
    store_name: Optional[str] = None
    region: Optional[str] = None
    appointment_cnt: int = 0
    arrival_cnt: int = 0
    deal_customers: int = 0
    deal_amount: float = 0.0
    deal_orders: int = 0
    repurchase_customers: int = 0
    nps_avg: float = 0.0


class AggregateMetricsIn(BaseModel):
    target_date: date
    store_id: Optional[int] = None


# ---------------- P6: 调理师排班 ----------------
class TherapistScheduleCreate(BaseModel):
    therapist_id: int
    work_date: date
    am_pm: str = "morning"  # morning/afternoon/evening
    start_time: time
    end_time: time
    capacity: int = 1
    remark: Optional[str] = None


class TherapistScheduleUpdate(BaseModel):
    work_date: Optional[date] = None
    am_pm: Optional[str] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    status: Optional[str] = None  # open/closed
    capacity: Optional[int] = None
    remark: Optional[str] = None


class TherapistScheduleOut(BaseOut):
    therapist_id: int
    store_id: int
    work_date: date
    am_pm: str
    start_time: time
    end_time: time
    status: str
    capacity: int
    remark: Optional[str] = None


# ---------------- P6: 调理师标签 ----------------
class TherapistTagCreate(BaseModel):
    name: str
    category: Optional[str] = None  # skill/health/service
    description: Optional[str] = None


class TherapistTagOut(BaseOut):
    name: str
    category: Optional[str] = None
    description: Optional[str] = None


class TherapistTagRelOut(BaseModel):
    therapist_id: int
    tag_id: int
    tag_name: Optional[str] = None
    category: Optional[str] = None
    assigned_by: Optional[int] = None
    created_at: Optional[datetime] = None


# ---------------- 效果四档判定（合规强规则3，第11.2章） ----------------
class EffectTrackingCreate(BaseModel):
    customer_id: int
    plan_id: Optional[int] = None
    baseline_pain: Optional[float] = None  # 基线疼痛评分（方案开始时）
    latest_pain: Optional[float] = None    # 最近一次疼痛评分
    nps: Optional[int] = None
    repurchase_count: Optional[int] = None


class EffectTrackingOut(BaseOut):
    customer_id: int
    plan_id: Optional[int] = None
    effect_level: Optional[str] = None  # significant/effective/ineffective/worsened
    assess_seq_json: Any = None
    generated_at: Optional[datetime] = None
