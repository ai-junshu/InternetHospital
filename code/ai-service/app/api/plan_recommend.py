"""调理方案推荐接口（技术架构第10.3章 RAG 可解释输出）。"""
from fastapi import APIRouter
from pydantic import BaseModel
import pandas as pd

from app.core.response import success
from app.schemas.predict import PlanRecommendOut
from app.ml.model_loader import load_model
from app.rag.retriever import build_query, build_rationale, retrieve

router = APIRouter(prefix="/plan-recommend", tags=["方案推荐"])

PLANS = {
    0: {"plan_id": "P1", "title": "温和调理方案", "items": ["热敷", "低强度运动", "作息调整"]},
    1: {"plan_id": "P2", "title": "标准调理方案", "items": ["理疗", "膳食干预", "定期复查"]},
    2: {"plan_id": "P3", "title": "强化调理方案", "items": ["专业康复", "药物辅助", "医生随访"]},
}


class PlanRecommendReq(BaseModel):
    customer_id: int
    age: int = 35
    pain_score: float = 5.0
    chronic_count: int = 0
    pain_type: str | None = None


@router.post("")
async def recommend(req: PlanRecommendReq):
    model, version = load_model("plan_recommend")
    X = pd.DataFrame([{
        "age": req.age,
        "pain_score": req.pain_score,
        "chronic_count": req.chronic_count,
    }])
    idx = int(model.predict(X)[0])
    plan = PLANS.get(idx, PLANS[0])
    # RAG 可解释：检索知识库，生成引用真实条目的依据（非占位文案）
    query = build_query(req.pain_type, req.pain_score, req.chronic_count, req.age)
    hits = retrieve(query, top_k=3)
    rationale = build_rationale(
        features={
            "version": version,
            "age": req.age,
            "pain_score": req.pain_score,
            "chronic_count": req.chronic_count,
            "pain_type": req.pain_type,
        },
        plan=plan,
        hits=hits,
    )
    data = PlanRecommendOut(
        customer_id=req.customer_id,
        model_version=version,
        care_plan_json=plan,
        rationale=rationale,
    ).model_dump()
    return success(data=data, message="方案推荐（AI 仅供参考，不替代医师诊断）")
