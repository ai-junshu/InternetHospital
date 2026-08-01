"""复购/复诊预测接口（第15.4章 AI 反馈闭环数据来源）。"""
from fastapi import APIRouter
import pandas as pd

from app.core.response import success
from app.schemas.predict import RepurchasePredictionOut
from app.ml.model_loader import load_model
from app.ml.feature_store import to_model_features
from app.ml.feature_contract import build_frame

router = APIRouter(prefix="/repurchase-prediction", tags=["复购预测"])


@router.get("")
async def predict(
    customer_id: int,
    age: int = 40,
    visit_freq: float = 3.0,
    last_gap_days: float = 30.0,
    treatment_count: int = 0,
    adherent_count: int = 0,
    nps: float = 0.0,
    effect_level: str | None = None,
):
    model, version = load_model("repurchase_prediction")
    # P2 特征工程：聚合原始指标 → 标准化特征（原始不出域，联邦取数语义）
    feats = to_model_features(
        customer_id,
        {
            "age": age,
            "treatment_count": treatment_count,
            "adherent_count": adherent_count,
            "nps": nps,
            "effect_level": effect_level,
        },
        model_name="repurchase_prediction",
    )
    # 按 feature_contract 列序构造，保证与训练一致（registry 模型可一致加载）
    X = build_frame("repurchase_prediction", [feats])
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
