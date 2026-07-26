"""AI 推理响应 Schema（技术架构第10.3章：强制 isAssist=true）。

所有 AI 输出均为辅助决策，不替代医师诊断；该字段为合规红线，禁止遗漏。
"""
from pydantic import BaseModel, Field


class PredictResponse(BaseModel):
    isAssist: bool = Field(
        default=True,
        description="AI 仅供参考，不替代医师诊断（合规红线，第10.3章）",
    )
    model_version: str = Field(default="placeholder", description="模型版本，取自 MLflow")
    # 子类按场景扩展具体预测字段


class RepurchasePredictionOut(PredictResponse):
    customer_id: int | None = None
    next_visit_prob: float | None = None
    repurchase_prob: float | None = None
    risk_level: str | None = None


class PlanRecommendOut(PredictResponse):
    customer_id: int | None = None
    care_plan_json: dict | None = None
    rationale: str | None = None  # RAG 可解释依据（第10.3章）


class RiskProfileOut(PredictResponse):
    customer_id: int | None = None
    pain_risk: str | None = None
    comorbidity_risk: str | None = None
