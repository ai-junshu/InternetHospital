"""示例模型训练与注册（最小可跑验证用）。

（可选）启动 MLflow server 看 UI（与训练共享同一文件库）：
    mlflow server --backend-store-uri sqlite:///tracking.db --default-artifact-root ./mlartifacts --host 0.0.0.0 --port 5000

再运行本脚本：
    python scripts/train_sample.py

会训练 3 个简单 sklearn 模型并注册到 MLflow 注册表（stage=Production）：
    - plan_recommend        方案推荐（3 类分类）
    - repurchase_prediction 复购概率（回归）
    - risk_profile          风险画像（3 级分类）
"""
import os

import numpy as np
import pandas as pd
import mlflow
from mlflow.tracking import MlflowClient
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor

# 默认使用文件型存储（无需启动 server 即可验证注册/加载闭环）；
# 接入 server 时设置环境变量 MLFLOW_TRACKING_URI 覆盖即可。
TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "sqlite:///tracking.db")


def _register(name: str, estimator, X: pd.DataFrame, y, stage: str = "Production"):
    mlflow.set_tracking_uri(TRACKING_URI)
    with mlflow.start_run(run_name=name):
        estimator.fit(X, y)
        mlflow.sklearn.log_model(estimator, name, registered_model_name=name)
    client = MlflowClient(tracking_uri=TRACKING_URI)
    versions = client.get_latest_versions(name, stages=["None"])
    if versions:
        client.transition_model_version_stage(name, versions[0].version, stage)
    print(f"[OK] registered {name} -> {stage}")


def main():
    rng = np.random.default_rng(42)
    n = 300

    # 1) 方案推荐：分类（3 类方案）
    X1 = pd.DataFrame({
        "age": rng.integers(20, 80, n),
        "pain_score": rng.integers(1, 10, n).astype(float),
        "chronic_count": rng.integers(0, 4, n),
    })
    y1 = rng.integers(0, 3, n)
    _register("plan_recommend", RandomForestClassifier(n_estimators=50, random_state=0), X1, y1)

    # 2) 复购预测：回归（概率 0~1）
    X2 = pd.DataFrame({
        "age": rng.integers(20, 80, n),
        "visit_freq": rng.integers(0, 10, n).astype(float),
        "last_gap_days": rng.integers(5, 90, n).astype(float),
    })
    base = (X2["visit_freq"] / 10) * 0.6 + (1 - (X2["last_gap_days"] - 5) / 85) * 0.4
    y2 = np.clip(base + rng.normal(0, 0.05, n), 0, 1).values
    _register("repurchase_prediction", RandomForestRegressor(n_estimators=50, random_state=0), X2, y2)

    # 3) 风险画像：分类（3 级）
    X3 = pd.DataFrame({
        "age": rng.integers(20, 80, n),
        "bmi": rng.normal(24, 4, n),
        "comorbidity_count": rng.integers(0, 5, n),
    })
    y3 = rng.integers(0, 3, n)
    _register("risk_profile", RandomForestClassifier(n_estimators=50, random_state=0), X3, y3)

    print("ALL DONE")


if __name__ == "__main__":
    main()
