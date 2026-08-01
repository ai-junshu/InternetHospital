"""示例模型训练与注册（最小可跑验证用）。

（可选）启动 MLflow server 看 UI（与训练共享同一文件库）：
    mlflow server --backend-store-uri sqlite:///tracking.db --default-artifact-root ./mlartifacts --host 0.0.0.0 --port 5000

再运行本脚本：
    python scripts/train_sample.py

会训练 3 个简单 sklearn 模型并注册到 MLflow 注册表（stage=Production）：
    - plan_recommend        方案推荐（3 类分类）
    - repurchase_prediction 复购概率（回归）
    - risk_profile          风险画像（3 级分类）

关键：训练用的特征列严格复用 app.ml.feature_contract 中定义的契约列，
与推理入口（build_frame）保持一致，registry 中的模型才能被一致加载调用。
"""
import os

import numpy as np
import pandas as pd
import mlflow
from mlflow.tracking import MlflowClient
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor

from app.ml.feature_contract import build_frame

# 默认使用文件型存储（无需启动 server 即可验证注册/加载闭环）；
# 接入 server 时设置环境变量 MLFLOW_TRACKING_URI 覆盖即可。
TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "sqlite:///tracking.db")
REGISTRY_STAGE = os.environ.get("MLFLOW_REGISTRY_STAGE", "Production")


def _register(name: str, estimator, X: pd.DataFrame, y, stage: str = REGISTRY_STAGE):
    mlflow.set_tracking_uri(TRACKING_URI)
    with mlflow.start_run(run_name=name):
        estimator.fit(X, y)
        # 记录特征列签名，便于 registry 校验输入一致性
        mlflow.sklearn.log_model(
            estimator, name,
            registered_model_name=name,
            signature=mlflow.models.infer_signature(X, pd.DataFrame({"y": y})),
        )
    client = MlflowClient(tracking_uri=TRACKING_URI)
    # 取该模型最新版本号（不依赖已废弃的 stage 参数），再 transition 到目标 stage
    latest = client.search_model_versions(f"name='{name}'")
    if latest:
        client.transition_model_version_stage(name, latest[0].version, stage)
    print(f"[OK] registered {name} ({X.shape[1]} features) -> {stage}")


def _gen_samples(n: int, feats: dict):
    """生成 n 条随机样本（字段名=契约特征列名），供 build_frame 构造。"""
    rng = np.random.default_rng(42)
    rows = []
    for _ in range(n):
        row = {}
        for k, v in feats.items():
            if v == "int":
                row[k] = int(rng.integers(0, 10))
            elif v == "float":
                row[k] = float(rng.normal(5, 3))
            else:
                row[k] = 0
        rows.append(row)
    return rows


def main():
    n = 300

    # 1) 方案推荐：分类（3 类方案）—— 使用 PLAN_FEATURES 契约列
    plan_fields = {
        "pain_score": "float", "anxiety_score": "float", "sleep_score": "float",
        "adherence_score": "float", "age": "int", "treatment_weeks": "int",
        "chronic_disease_count": "int", "prior_plan_satisfaction": "float",
        "plan_completion_rate": "float", "goal_achievement": "float",
        "preference_strength": "float", "exercise_score": "float",
    }
    X1 = build_frame("plan_recommend", _gen_samples(n, plan_fields))
    y1 = np.random.default_rng(42).integers(0, 3, n)
    _register("plan_recommend", RandomForestClassifier(n_estimators=50, random_state=0), X1, y1)

    # 2) 复购预测：回归（概率 0~1）—— 使用 REPURCHASE_FEATURES 契约列
    repurchase_fields = {
        "total_amount": "float", "purchase_count": "int", "recency_days": "float",
        "avg_order_value": "float", "repurchase_intent": "float", "active_days": "int",
        "plan_completion_rate": "float", "satisfaction": "float",
        "coupon_sensitivity": "float", "referral_count": "int",
        "is_birthday_month": "int", "holiday_factor": "float",
    }
    X2 = build_frame("repurchase_prediction", _gen_samples(n, repurchase_fields))
    base = (X2["purchase_count"] / 10) * 0.6 + (1 - (X2["recency_days"] - 5) / 85) * 0.4
    y2 = np.clip(base.values + np.random.normal(0, 0.05, n), 0, 1)
    _register("repurchase_prediction", RandomForestRegressor(n_estimators=50, random_state=0), X2, y2)

    # 3) 风险画像：分类（3 级）—— 使用 RISK_FEATURES 契约列
    risk_fields = {
        "age": "int", "chronic_disease_count": "int", "pain_score": "float",
        "anxiety_score": "float", "adherence_score": "float",
        "prior_dropout_count": "int", "treatment_weeks": "int",
        "bmi": "float", "sleep_disorder_score": "float", "plan_coverage": "float",
    }
    X3 = build_frame("risk_profile", _gen_samples(n, risk_fields))
    y3 = np.random.default_rng(42).integers(0, 3, n)
    _register("risk_profile", RandomForestClassifier(n_estimators=50, random_state=0), X3, y3)

    print("ALL DONE")


if __name__ == "__main__":
    main()
