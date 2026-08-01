"""特征工程（技术架构第6章：特征仓库）。

设计原则（第15.3章 隐私计算/联邦学习，原始不出域）：
- ai-service 不直接持有 backend 业务表，特征由调用方（backend 经 API 传入）
  提供"原始指标"，本模块负责标准化与派生聚合，产出模型可用特征向量。
- build_features 为纯函数，便于单测；不依赖任何数据库连接。

输入 raw（原始指标，来自联邦取数）：
    treatment_count     治疗总次数
    adherent_count      依从（按计划完成）次数
    nps                 最近一次满意度（0-10）
    effect_level        效果四档 significant/effective/ineffective/worsened（或 None）
    age                 年龄
    chronic_count       慢性病数量
    pain_score          当前疼痛评分（0-10）
    pain_type           疼痛类型（可选）
输出 features：标准化数值特征 + 派生特征（adherence_rate / effect_score / risk_flags）
"""
from typing import Optional

_EFFECT_SCORE = {
    "significant": 1.0,
    "effective": 0.7,
    "ineffective": 0.3,
    "worsened": 0.0,
}


def build_features(customer_id: int, raw: Optional[dict] = None) -> dict:
    raw = raw or {}
    treatment_count = int(raw.get("treatment_count", 0) or 0)
    adherent_count = int(raw.get("adherent_count", 0) or 0)
    nps = float(raw.get("nps", 0) or 0)
    effect_level = raw.get("effect_level")
    age = int(raw.get("age", 0) or 0)
    chronic_count = int(raw.get("chronic_count", 0) or 0)
    pain_score = float(raw.get("pain_score", 0) or 0)

    # 派生特征
    adherence_rate = round(adherent_count / treatment_count, 3) if treatment_count else 0.0
    effect_score = _EFFECT_SCORE.get(effect_level, 0.0)
    # 风险标记：低依从 或 效果恶化 或 高疼痛
    risk_flags = []
    if adherence_rate < 0.5 and treatment_count > 0:
        risk_flags.append("low_adherence")
    if effect_level in ("ineffective", "worsened"):
        risk_flags.append("poor_effect")
    if pain_score >= 7:
        risk_flags.append("high_pain")

    # 风险评分：仅在存在有效信号（有治疗记录 / 有疼痛评分 / 有疗效判定）时计算，
    # 避免空数据被误判为高风险。
    has_signal = treatment_count > 0 or pain_score > 0 or effect_level is not None
    risk_score = round(
        0.3 * (1 - adherence_rate)
        + 0.4 * (1 - effect_score)
        + 0.3 * (pain_score / 10),
        3,
    ) if has_signal else 0.0

    return {
        "customer_id": customer_id,
        # 原始标准化（供模型）
        "treatment_count": treatment_count,
        "adherence_rate": adherence_rate,
        "nps": nps,
        "effect_score": effect_score,
        "age": age,
        "chronic_count": chronic_count,
        "pain_score": pain_score,
        # 派生
        "effect_level": effect_level,
        "risk_flags": risk_flags,
        "risk_score": risk_score,
    }


# 各模型所需的「契约特征映射」：把 build_features 的输出映射到 feature_contract 列。
# 训练脚本与推理入口共用 feature_contract.MODEL_FEATURE_MAP，保证列一致。
_MODEL_FEATURE_MAP = {
    "risk_profile": lambda f: {
        "age": f["age"],
        "chronic_disease_count": f["chronic_count"],
        "pain_score": f["pain_score"],
        "anxiety_score": 0.0,  # 联邦取数暂未提供，默认中性
        "adherence_score": f["adherence_rate"],
        "prior_dropout_count": 0,
        "treatment_weeks": f["treatment_count"],
        "bmi": 24.0,
        "sleep_disorder_score": 0.0,
        "plan_coverage": f["effect_score"],
    },
    "plan_recommend": lambda f: {
        "pain_score": f["pain_score"],
        "anxiety_score": 0.0,
        "sleep_score": 0.0,
        "adherence_score": f["adherence_rate"],
        "age": f["age"],
        "treatment_weeks": f["treatment_count"],
        "chronic_disease_count": f["chronic_count"],
        "prior_plan_satisfaction": f["nps"],
        "plan_completion_rate": f["adherence_rate"],
        "goal_achievement": f["effect_score"],
        "preference_strength": 0.0,
        "exercise_score": 0.0,
    },
    "repurchase_prediction": lambda f: {
        "total_amount": f["treatment_count"] * 100.0,
        "purchase_count": f["treatment_count"],
        "recency_days": 30.0,
        "avg_order_value": 100.0,
        "repurchase_intent": f["nps"] / 10.0,
        "active_days": f["treatment_count"] * 2,
        "plan_completion_rate": f["adherence_rate"],
        "satisfaction": f["nps"],
        "coupon_sensitivity": 0.5,
        "referral_count": 0,
        "is_birthday_month": 0,
        "holiday_factor": 0.0,
    },
}


def to_model_features(customer_id: int, raw: Optional[dict], model_name: str) -> dict:
    """产出与 feature_contract 完全一致列序的特征 dict（供 build_frame）。"""
    base = build_features(customer_id, raw)
    mapper = _MODEL_FEATURE_MAP.get(model_name)
    if mapper is None:
        return base
    return mapper(base)
