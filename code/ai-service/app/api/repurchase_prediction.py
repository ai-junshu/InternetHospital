"""复购/复诊预测接口（第15.4章 AI 反馈闭环数据来源）。"""
from fastapi import APIRouter
import pandas as pd

from app.core.response import success
from app.schemas.predict import RepurchasePredictionOut
from app.ml.model_loader import load_model

router = APIRouter(prefix="/repurchase-prediction", tags=["复购预测"])


@router.get("")
async def predict(
    customer_id: int,
    age: int = 40,
    visit_freq: float = 3.0,
    last_gap_days: float = 30.0,
):
    model, version = load_model("repurchase_prediction")
    X = pd.DataFrame([{
        "age": age,
        "visit_freq": visit_freq,
        "last_gap_days": last_gap_days,
    }])
    prob = max(0.0, min(1.0, float(model.predict(X)[0])))
    risk_level = "high" if prob > 0.66 else ("medium" if prob > 0.33 else "low")
    data = RepurchasePredictionOut(
        customer_id=customer_id,
        model_version=version,
        next_visit_prob=round(prob * 0.9, 3),
        repurchase_prob=round(prob, 3),
        risk_level=risk_level,
    ).model_dump()
    return success(data=data, message="复购预测（AI 仅供参考，不替代医师诊断）")
