"""平台模块 Schema（审计日志响应等）。"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.common import BaseOut


class AuditLogOut(BaseOut):
    actor_id: Optional[int] = None
    role: Optional[str] = None
    action: Optional[str] = None
    resource: Optional[str] = None
    before_json: Optional[dict] = None
    after_json: Optional[dict] = None
    ip: Optional[str] = None
    # P4 哈希链防篡改字段
    seq_no: int = 0
    prev_hash: Optional[str] = None
    hash: Optional[str] = None


class PredLogOut(BaseOut):
    """AI 预测日志输出（第15.4章 反馈闭环）。"""

    model_id: Optional[int] = None
    version: Optional[str] = None
    customer_id: Optional[int] = None
    input_features_json: Optional[dict] = None
    predict_result_json: Optional[dict] = None
    predict_time: Optional[datetime] = None
    user_id: Optional[int] = None
    adopted: Optional[str] = None


# ---- AI 模型目录（plat_ai_model，第11.2/12.3章） ----


class AiModelCreate(BaseModel):
    name: str
    version: str
    train_dataset_id: Optional[int] = None
    algo_type: Optional[str] = None
    metrics_json: Optional[dict] = None
    status: str = "offline"


class AiModelUpdate(BaseModel):
    name: Optional[str] = None
    version: Optional[str] = None
    train_dataset_id: Optional[int] = None
    algo_type: Optional[str] = None
    metrics_json: Optional[dict] = None
    status: Optional[str] = None


class AiModelOut(BaseOut):
    name: Optional[str] = None
    version: Optional[str] = None
    train_dataset_id: Optional[int] = None
    algo_type: Optional[str] = None
    metrics_json: Optional[dict] = None
    status: str = "offline"
    online_at: Optional[datetime] = None
    offline_at: Optional[datetime] = None


# ---- 数据资产目录（plat_data_asset，第11.2/13章） ----


class DataAssetCreate(BaseModel):
    name: str
    owner: Optional[str] = None
    sensitivity_level: Optional[str] = None  # L1-L4
    usage_scope: Optional[str] = None
    quality_score: Optional[float] = None
    update_freq: Optional[str] = None
    lineage_json: Optional[dict] = None


class DataAssetUpdate(BaseModel):
    name: Optional[str] = None
    owner: Optional[str] = None
    sensitivity_level: Optional[str] = None
    usage_scope: Optional[str] = None
    quality_score: Optional[float] = None
    update_freq: Optional[str] = None
    lineage_json: Optional[dict] = None


class DataAssetOut(BaseOut):
    name: Optional[str] = None
    owner: Optional[str] = None
    sensitivity_level: Optional[str] = None
    usage_scope: Optional[str] = None
    quality_score: Optional[float] = None
    update_freq: Optional[str] = None
    lineage_json: Optional[dict] = None


# ---------------- P6: 合规采集审核 ----------------
class ComplianceSubmitIn(BaseModel):
    category: str  # qualification/license/privacy/security/...
    subject_type: str  # doctor/store/therapist/platform
    subject_id: Optional[int] = None
    title: str
    content_json: Optional[dict] = None


class ComplianceReviewIn(BaseModel):
    review_note: Optional[str] = None


class ComplianceOut(BaseOut):
    category: str
    subject_type: str
    subject_id: Optional[int] = None
    title: str
    content_json: Optional[dict] = None
    submitter_id: Optional[int] = None
    status: str
    reviewer_id: Optional[int] = None
    review_note: Optional[str] = None
    reviewed_at: Optional[datetime] = None
