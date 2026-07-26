"""健康风险画像接口（第15.4章 AI 反馈闭环数据来源）。"""
from fastapi import APIRouter
import pandas as pd

from app.core.response import success
from app.schemas.predict import RiskProfileOut
from app.ml.model_loader import load_model

router = APIRouter(prefix="/risk-profile", tags=["风险画像"])

_LABELS = {0: "low", 1: "medium", 2: "high"}


@router.get("")
async def profile(
    customer_id: int,
    age: int = 45,
    bmi: float = 24.0,
    comorbidity_count: int = 0,
):
    model, version = load_model("risk_profile")
    X = pd.DataFrame([{
        "age": age,
        "bmi": bmi,
        "comorbidity_count": comorbidity_count,
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
