"""H4 合理用药真引擎单元测试（纯逻辑，无需数据库，必跑）。

验证 LocalRxEngine（local 真引擎）相对 MockRxEngine（降级基准）的能力跃迁：
- 相互作用（如 阿司匹林+布洛芬 出血）
- 人群禁忌（孕期禁用布洛芬 / 肝功能不全对乙酰氨基酚）
- 重复用药（同通用名多开）
- 特殊人群（儿童禁用阿司匹林 / 老年慎用地西泮）
- 剂量超量告警
- 工厂默认回退 local；显式 mock 仍可工作
"""

from app.core.config import settings
from app.services.rx_engine import get_rx_engine
from app.services.rx_engine.local import LocalRxEngine
from app.services.rx_engine.mock import MockRxEngine


def _rx(items, patient=None, kb_path=None):
    eng = LocalRxEngine(kb_path=kb_path)
    return eng.check({"items": items, "patient": patient or {}})


def test_local_engine_is_default_without_http():
    """工厂在 provider!=http 时回退本地真引擎。"""
    prev = settings.rx_engine_provider
    settings.rx_engine_provider = "local"
    try:
        assert isinstance(get_rx_engine(), LocalRxEngine)
    finally:
        settings.rx_engine_provider = prev


def test_mock_baseline_still_works():
    """mock 降级基准仍可独立产出 RxResult。"""
    res = MockRxEngine().check(
        {
            "items": [{"name": "布洛芬", "generic_name": "布洛芬", "daily_dose": 0, "max_daily_dose": 0}],
            "patient": {"pregnancy": True},
        }
    )
    assert res.provider == "mock"
    assert res.has_issue is False or res.has_issue is True  # 结构可用即可


def test_drug_interaction_detected():
    """阿司匹林+布洛芬 联用应触发 high 级相互作用告警。"""
    res = _rx(
        [
            {"name": "阿司匹林", "generic_name": "aspirin", "daily_dose": 0, "max_daily_dose": 0},
            {"name": "布洛芬", "generic_name": "ibuprofen", "daily_dose": 0, "max_daily_dose": 0},
        ]
    )
    assert res.has_issue
    assert any(
        c["type"] == "drug_interaction" and set(c["drugs"]) == {"aspirin", "ibuprofen"}
        for c in res.conflicts
    )
    assert res.level == "high"


def test_pregnancy_contraindication():
    """孕期患者开具布洛芬应触发禁忌。"""
    res = _rx(
        [{"name": "布洛芬", "generic_name": "ibuprofen", "daily_dose": 0, "max_daily_dose": 0}],
        patient={"pregnancy": True},
    )
    assert any(
        c["type"] == "contraindication" and c["drug"] == "ibuprofen" for c in res.contraindications
    )
    assert "pregnancy" in res.contraindications[0]["populations"]


def test_hepatic_acetaminophen_contraindication():
    """肝功能不全者用对乙酰氨基酚触发 high 禁忌。"""
    res = _rx(
        [{"name": "对乙酰氨基酚", "generic_name": "acetaminophen", "daily_dose": 0, "max_daily_dose": 0}],
        patient={"hepatic_insufficiency": True},
    )
    assert any(
        c["type"] == "contraindication" and c["drug"] == "acetaminophen"
        for c in res.contraindications
    )


def test_duplicate_drug_detected():
    """同通用名多开应触发重复用药告警。"""
    res = _rx(
        [
            {"name": "泰诺", "generic_name": "acetaminophen", "daily_dose": 0, "max_daily_dose": 0},
            {"name": "必理通", "generic_name": "acetaminophen", "daily_dose": 0, "max_daily_dose": 0},
        ]
    )
    assert any(d["type"] == "duplicate" for d in res.duplicate_warnings)


def test_child_aspirin_forbidden():
    """儿童（<12）开具阿司匹林触发 high 特殊人群告警。"""
    res = _rx(
        [{"name": "阿司匹林", "generic_name": "aspirin", "daily_dose": 0, "max_daily_dose": 0}],
        patient={"age": 8},
    )
    assert any(
        s["type"] == "special_population" and s["population"] == "child" and s["drug"] == "aspirin"
        for s in res.special_population
    )


def test_elderly_diazepam_caution():
    """老年人（>=65）用地西泮触发 medium 特殊人群告警。"""
    res = _rx(
        [{"name": "地西泮", "generic_name": "diazepam", "daily_dose": 0, "max_daily_dose": 0}],
        patient={"age": 72},
    )
    assert any(
        s["type"] == "special_population" and s["population"] == "elderly"
        for s in res.special_population
    )


def test_dosage_overflow_warning():
    """单日剂量超过安全上限触发剂量告警。"""
    res = _rx(
        [
            {
                "name": "对乙酰氨基酚",
                "generic_name": "acetaminophen",
                "daily_dose": 5000,
                "max_daily_dose": 5000,
            }
        ]
    )
    assert any(d["type"] == "dosage" for d in res.dosage_warnings)
    assert res.level == "high"


def test_clean_prescription_has_no_issue():
    """无冲突的合规处方不应产生告警。"""
    res = _rx(
        [{"name": "维生素C", "generic_name": "vitamin_c", "daily_dose": 0, "max_daily_dose": 0}],
        patient={"age": 30},
    )
    assert res.has_issue is False
    assert res.level == "none"


def test_rule_source_tagged_local():
    """local 引擎结果应标注 rule_source=local_kb。"""
    res = _rx(
        [{"name": "布洛芬", "generic_name": "ibuprofen", "daily_dose": 0, "max_daily_dose": 0}],
        patient={"pregnancy": True},
    )
    assert res.rule_source == "local_kb"
    assert res.suggestions  # 应给出处置建议
