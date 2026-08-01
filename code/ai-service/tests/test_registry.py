"""MLflow registry 接入 & 特征契约一致性测试。

不依赖真实 MLflow server：仅验证
- 特征契约列（feature_contract）与推理入口（build_frame）构造的 DataFrame 列一致；
- 推理入口能正确产出与契约对齐的 DataFrame，且不抛列错位异常；
- /models/registry、/models/health 路由已注册。
"""
import sys
from pathlib import Path

import pandas as pd

# 让脚本可直接运行（pytest 自动加 app 路径，这里兜底）
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ml.feature_contract import MODEL_FEATURE_MAP, build_frame
from app.ml.feature_store import to_model_features


def test_contract_columns_matched_to_inference():
    """推理入口构造的 DataFrame 列必须与契约定义完全一致（顺序+集合）。"""
    for model_name, expected in MODEL_FEATURE_MAP.items():
        raw = {"age": 40, "pain_score": 5.0, "chronic_count": 1,
               "treatment_count": 3, "adherent_count": 2, "nps": 7.0}
        feats = to_model_features(1, raw, model_name=model_name)
        X = build_frame(model_name, [feats])
        assert isinstance(X, pd.DataFrame)
        assert list(X.columns) == expected, f"{model_name} 列序不一致"
        assert X.shape == (1, len(expected))


def test_build_frame_missing_column_fill_zero():
    """build_frame 对缺失列补 0，多余列丢弃，保证与训练列严格一致。"""
    X = build_frame("risk_profile", [{"age": 30}])  # 仅给 age
    assert X.shape[1] == len(MODEL_FEATURE_MAP["risk_profile"])
    assert X["age"].iloc[0] == 30
    assert X.drop(columns=["age"]).iloc[0].sum() == 0  # 其余补 0


def test_registry_routes_registered():
    from app.main import app

    paths = {getattr(r, "path", "") for r in app.routes}
    assert "/models/registry" in paths
    assert "/models/health" in paths
