"""健康风险画像接口（第15.4章 AI 反馈闭环数据来源）。"""
from fastapi import APIRouter
import pandas as pd

from app.core.response import success
from app.schemas.predict import RiskProfileOut
from app.ml.model_loader import load_model
from app.ml.feature_store import build_features

router = APIRouter(prefix="/risk-profile", tags=["风险画像"])

_LABELS = {0: "low", 1: "medium", 2: "high"}


@router.get("")
async def profile(
    customer_id: int,
    age: int = 45,
    bmi: float = 24.0,
    comorbidity_count: int = 0,
    pain_score: float = 5.0,
    chronic_count: int = 0,
    treatment_count: int = 0,
    adherent_count: int = 0,
    nps: float = 0.0,
    effect_level: str | None = None,
):
    model, version = load_model("risk_profile")
    # P2 特征工程：聚合原始指标 → 标准化 + 派生特征
    features = build_features(
        customer_id,
        {
            "age": age,
            "chronic_count": chronic_count,
            "pain_score": pain_score,
            "treatment_count": treatment_count,
            "adherent_count": adherent_count,
            "nps": nps,
            "effect_level": effect_level,
        },
    )
    X = pd.DataFrame([{
        "age": age,
        "bmi": bmi,
        "comorbidity_count": comorbidity_count,
        "risk_score": features["risk_score"],
    }])
    idx = int(model.predict(X)[0])
    label = _LABELS.get(idx, "medium")
    data = RiskProfileOut(
        customer_id=customer_id,
        model_version=version,
        pain_risk=label,
        comorbidity_risk=label,
    ).model_dump()
    return success(data=data, message="风险画像（AI 仅供参考，不替代医师诊断）")
