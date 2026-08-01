"""采集器声明式配置（P1 采集器配置化改造）。

设计要点：
- 采集逻辑不再是硬编码字符串匹配字典，而是「按采集类型(collector_type)路由到通用聚合器」。
- 每个数据资产可在 PlatDataAsset.collector_type 声明其采集类型；未声明时按
  asset.name 命中 DEFAULT_RULES 推断（兼容存量资产，无需改表即可扩展）。
- 新增资产只需在数据资产元数据上声明 collector_type，或由运营在 DEFAULT_RULES
  追加一条关键字规则，无需改动采集器源码。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass(frozen=True)
class CollectorSpec:
    """一种采集类型的规格定义。

    aggregation: 聚合口径，供通用聚合器解析：
        - "count": 统计关联业务表行数（data_volume）。
        - "quality": 直接回写资产质量分（来自资产自身 quality_score）。
        - "weighted_quality": data_volume 与 quality_score 联合估算（默认）。
    """

    type: str
    label: str
    aggregation: str = "weighted_quality"
    description: str = ""


# 已注册的采集器类型（通过类型路由，而非资产名硬编码匹配）
COLLECTOR_REGISTRY: dict[str, CollectorSpec] = {
    "treatment_outcome": CollectorSpec(
        type="treatment_outcome",
        label="治疗效果数据集采集",
        aggregation="weighted_quality",
        description="疗效四档聚合 + 治疗记录行数 → data_volume；质量分加权回写",
    ),
    "customer_profile": CollectorSpec(
        type="customer_profile",
        label="客户画像采集",
        aggregation="count",
        description="客户/用户档案行数 → data_volume",
    ),
    "plan_library": CollectorSpec(
        type="plan_library",
        label="调理方案库采集",
        aggregation="count",
        description="方案库条目数 → data_volume",
    ),
    "store_metrics": CollectorSpec(
        type="store_metrics",
        label="门店经营宽表采集",
        aggregation="weighted_quality",
        description="经营指标聚合 → data_volume + 质量分",
    ),
}

# 存量资产（未显式声明 collector_type）按名称关键字推断类型，便于零改动扩展。
# 规则按 (关键字, 采集类型) 声明，命中第一个即返回。
DEFAULT_RULES: list[tuple[str, str]] = [
    ("治疗效果", "treatment_outcome"),
    ("疗效", "treatment_outcome"),
    ("客户画像", "customer_profile"),
    ("客户档案", "customer_profile"),
    ("调理方案", "plan_library"),
    ("方案库", "plan_library"),
    ("门店经营", "store_metrics"),
    ("经营宽表", "store_metrics"),
]

# 回退类型（无法推断时使用）
FALLBACK_TYPE = "treatment_outcome"


def resolve_collector_type(asset_name: str, declared_type: str | None = None) -> str:
    """解析资产应使用的采集器类型。

    - 若资产显式声明了 collector_type 且已在注册表，直接使用。
    - 否则按名称关键字规则推断。
    - 都未命中则回退到 FALLBACK_TYPE。
    """
    if declared_type and declared_type in COLLECTOR_REGISTRY:
        return declared_type
    for keyword, ctype in DEFAULT_RULES:
        if keyword in (asset_name or ""):
            return ctype
    return FALLBACK_TYPE


def get_collector_spec(collector_type: str) -> CollectorSpec:
    return COLLECTOR_REGISTRY.get(collector_type, COLLECTOR_REGISTRY[FALLBACK_TYPE])


def list_collectors() -> list[dict]:
    """导出已注册采集器清单（供运营端点展示）。"""
    return [
        {
            "type": spec.type,
            "label": spec.label,
            "aggregation": spec.aggregation,
            "description": spec.description,
        }
        for spec in COLLECTOR_REGISTRY.values()
    ]
