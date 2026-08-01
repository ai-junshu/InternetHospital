"""特征工程单测：验证 build_features 聚合与派生特征正确。"""
from app.ml.feature_store import build_features


def test_empty_input():
    f = build_features(1, {})
    assert f["customer_id"] == 1
    assert f["treatment_count"] == 0
    assert f["adherence_rate"] == 0.0
    assert f["effect_score"] == 0.0
    assert f["risk_score"] == 0.0
    assert f["risk_flags"] == []


def test_adherence_rate():
    f = build_features(
        2,
        {"treatment_count": 4, "adherent_count": 3, "nps": 9,
         "effect_level": "significant", "pain_score": 2},
    )
    assert f["adherence_rate"] == 0.75
    assert f["effect_score"] == 1.0
    assert f["risk_flags"] == []  # 高依从+显效+低痛 → 无风险标记


def test_risk_flags():
    f = build_features(
        3,
        {"treatment_count": 2, "adherent_count": 0, "nps": 3,
         "effect_level": "worsened", "pain_score": 8},
    )
    assert f["adherence_rate"] == 0.0
    assert "low_adherence" in f["risk_flags"]
    assert "poor_effect" in f["risk_flags"]
    assert "high_pain" in f["risk_flags"]
    assert f["risk_score"] > 0.5


def test_effect_score_mapping():
    assert build_features(4, {"effect_level": "effective"})["effect_score"] == 0.7
    assert build_features(5, {"effect_level": "ineffective"})["effect_score"] == 0.3
    assert build_features(6, {"effect_level": "worsened"})["effect_score"] == 0.0
    assert build_features(7, {"effect_level": None})["effect_score"] == 0.0
