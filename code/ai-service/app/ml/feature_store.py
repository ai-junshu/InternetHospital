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
