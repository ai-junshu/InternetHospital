"""AI 模型特征契约（MLflow registry 加载一致性保障）。

问题背景：推理 API（risk_profile / plan_recommend / repurchase_prediction）用
pandas DataFrame 预测，列顺序/列名须与训练时完全一致，否则 mlflow sklearn flavor
加载的模型会在 predict 时因列错位报错。

本模块集中定义三类模型的「标准特征列」，训练脚本与推理入口共用同一份契约，
确保 registry 中的模型可被一致加载与调用。
"""
from __future__ import annotations

# 风险评级（疼痛/调理管理适配）：年龄、慢病数、疼痛评分、焦虑评分、依从性评分、
# 既往中断次数、治疗周数、BMI、睡眠障碍评分、方案覆盖度
RISK_FEATURES = [
    "age", "chronic_disease_count", "pain_score", "anxiety_score",
    "adherence_score", "prior_dropout_count", "treatment_weeks",
    "bmi", "sleep_disorder_score", "plan_coverage",
]

# 方案推荐（调理方案适配）：疼痛评分、焦虑评分、睡眠评分、依从性评分、年龄、
# 治疗周数、慢病数、既往方案满意度、方案完成率、目标达成度、偏好强度、运动评分
PLAN_FEATURES = [
    "pain_score", "anxiety_score", "sleep_score", "adherence_score", "age",
    "treatment_weeks", "chronic_disease_count", "prior_plan_satisfaction",
    "plan_completion_rate", "goal_achievement", "preference_strength",
    "exercise_score",
]

# 复购预测（门店私域运营）：历史消费金额、消费次数、最近消费间隔天数、客单价、
# 复购意向评分、活跃天数、方案完成率、满意度、优惠敏感系数、推荐好友数、生日当月、节假日系数
REPURCHASE_FEATURES = [
    "total_amount", "purchase_count", "recency_days", "avg_order_value",
    "repurchase_intent", "active_days", "plan_completion_rate", "satisfaction",
    "coupon_sensitivity", "referral_count", "is_birthday_month", "holiday_factor",
]

# 模型名（与 MLflow registry 注册名一致）→特征列映射
MODEL_FEATURE_MAP = {
    "plan_recommend": PLAN_FEATURES,
    "repurchase_prediction": REPURCHASE_FEATURES,
    "risk_profile": RISK_FEATURES,
}


def features_for(model_name: str) -> list[str]:
    return list(MODEL_FEATURE_MAP.get(model_name, []))


def build_frame(model_name: str, records: list[dict]) -> "pd.DataFrame":
    """按契约列序构造 DataFrame（列缺失补 0，多余列丢弃），保证与训练一致。"""
    import pandas as pd

    cols = features_for(model_name)
    rows = []
    for r in records:
        rows.append({c: r.get(c, 0) for c in cols})
    return pd.DataFrame(rows, columns=cols)
