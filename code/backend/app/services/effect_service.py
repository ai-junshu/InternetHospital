"""治疗效果四档判定（合规强规则3，PRD V2.0 L267-270）。

根据客户在方案周期内的疼痛评分变化、复购/到店行为与 NPS 满意度，
自动判定显效(significant)/有效(effective)/无效(ineffective)/恶化(worsened)，
并触发不同后续动作（无效→推荐升级方案/建议就医）。
判定为纯函数，便于单测与复用。
"""
from datetime import datetime, timezone
from typing import Any, Optional

# 四档枚举（与 mt_effect_tracking.effect_level 对齐）
EFFECT_SIGNIFICANT = "significant"  # 显效
EFFECT_EFFECTIVE = "effective"      # 有效
EFFECT_INEFFECTIVE = "ineffective"  # 无效
EFFECT_WORSENED = "worsened"        # 恶化

VALID_EFFECT_LEVELS = {
    EFFECT_SIGNIFICANT,
    EFFECT_EFFECTIVE,
    EFFECT_INEFFECTIVE,
    EFFECT_WORSENED,
}


def judge_effect_level(
    *,
    baseline_pain: float | None,
    latest_pain: float | None,
    nps: int | None = None,
    repurchase_count: int | None = None,
) -> tuple[str, dict]:
    """判定效果四档。

    规则（PRD L267-270）：
    - 恶化：疼痛评分较基线上升 >= 1 分（且无显著下降）。
    - 显效：疼痛评分下降 >= 3 分，或下降到 0-1 且 NPS>=8。
    - 有效：疼痛评分下降 1~2 分，或 NPS>=8 且无恶化。
    - 无效：不满足上述三项（含数据不足时保守判为无效，触发人工复核/升级方案）。

    返回 (effect_level, detail)，detail 含判定依据供审计/解释。
    """
    detail: dict[str, Any] = {
        "baseline_pain": baseline_pain,
        "latest_pain": latest_pain,
        "nps": nps,
        "repurchase_count": repurchase_count,
    }
    if baseline_pain is None or latest_pain is None:
        detail["reason"] = "pain_score_missing"
        return EFFECT_INEFFECTIVE, detail

    delta = round(latest_pain - baseline_pain, 2)
    detail["delta"] = delta

    if delta >= 1:
        detail["reason"] = "pain_worsened"
        return EFFECT_WORSENED, detail
    if delta <= -3 or (latest_pain <= 1 and (nps or 0) >= 8):
        detail["reason"] = "pain_significantly_relieved"
        return EFFECT_SIGNIFICANT, detail
    if delta <= -1 or (nps or 0) >= 8:
        detail["reason"] = "pain_relieved_or_high_nps"
        return EFFECT_EFFECTIVE, detail

    detail["reason"] = "no_clear_improvement"
    return EFFECT_INEFFECTIVE, detail


async def build_effect_tracking(
    db,
    *,
    customer_id: int,
    plan_id: int | None,
    baseline_pain: float | None,
    latest_pain: float | None,
    nps: int | None = None,
    repurchase_count: int | None = None,
) -> dict:
    """生成一条效果跟踪记录（含判定），调用方负责落库与审计。

    返回待写入 mt_effect_tracking 的字段字典；不直接提交，便于与服务层事务整合。
    """
    level, detail = judge_effect_level(
        baseline_pain=baseline_pain,
        latest_pain=latest_pain,
        nps=nps,
        repurchase_count=repurchase_count,
    )
    return {
        "customer_id": customer_id,
        "plan_id": plan_id,
        "effect_level": level,
        "assess_seq_json": {"detail": detail, "generated_at": datetime.now(timezone.utc).isoformat()},
        "generated_at": datetime.now(timezone.utc),
    }
