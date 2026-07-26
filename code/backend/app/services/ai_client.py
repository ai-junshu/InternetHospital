"""ai-service 内部调用（技术架构第12章 MLOps）。

backend 通过 HTTP 调用 ai-service 推理接口；网络/服务不可用时优雅降级，
不阻塞主链路（健康数据中台业务可独立运行）。
"""
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger("ai_client")


async def recommend_plan(
    customer_id: int,
    age: int,
    pain_score: int,
    chronic_count: int,
    pain_type: str | None = None,
) -> dict | None:
    """调用 ai-service /plan-recommend，失败返回 None（降级）。"""
    url = f"{settings.ai_service_base_url}/plan-recommend"
    payload = {
        "customer_id": customer_id,
        "age": age,
        "pain_score": pain_score,
        "chronic_count": chronic_count,
        "pain_type": pain_type,
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                return resp.json().get("data")
    except Exception as exc:  # noqa: BLE001
        logger.warning("ai-service plan-recommend 调用失败: %s", exc)
    return None


async def repurchase_prediction(
    customer_id: int,
    age: int = 40,
    visit_freq: float = 3.0,
    last_gap_days: float = 30.0,
) -> dict | None:
    """调用 ai-service /repurchase-prediction（GET），失败返回 None（降级）。

    作为第15.4章 AI 反馈闭环的数据来源：backend 拿到预测后落 mt_repurchase_prediction。
    """
    url = f"{settings.ai_service_base_url}/repurchase-prediction"
    params = {
        "customer_id": customer_id,
        "age": age,
        "visit_freq": visit_freq,
        "last_gap_days": last_gap_days,
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                return resp.json().get("data")
    except Exception as exc:  # noqa: BLE001
        logger.warning("ai-service repurchase-prediction 调用失败: %s", exc)
    return None


async def risk_profile(
    customer_id: int,
    age: int = 45,
    bmi: float = 24.0,
    comorbidity_count: int = 0,
) -> dict | None:
    """调用 ai-service /risk-profile（GET），失败返回 None（降级）。

    作为第15.4章 AI 反馈闭环的数据来源：backend 拿到画像后落 mt_risk_profile。
    """
    url = f"{settings.ai_service_base_url}/risk-profile"
    params = {
        "customer_id": customer_id,
        "age": age,
        "bmi": bmi,
        "comorbidity_count": comorbidity_count,
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                return resp.json().get("data")
    except Exception as exc:  # noqa: BLE001
        logger.warning("ai-service risk-profile 调用失败: %s", exc)
    return None
