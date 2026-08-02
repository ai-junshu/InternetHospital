"""合理用药引擎抽象层（第三方对接，技术架构第14章）。

处方开方前置校验：用药冲突 / 禁忌 / 剂量告警。
抽象基类 + 工厂，便于后续从 Mock 切换至真实供应商（HttpRxEngine 预留对接点）。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class RxResult(BaseModel):
    """合理用药校验结果。

    兼容字段（conflicts / contraindications / dosage_warnings）保留以对接
    既有 prescriptions 调用方与 HttpRxEngine 供应商契约；
    新增字段（level / rule_source / suggestions / duplicate_warnings / special_population）
    用于更精细的分级告警与处置建议（LocalRxEngine 产出）。
    """

    provider: str
    conflicts: list[dict[str, Any]] = []          # 用药冲突（相互作用）
    contraindications: list[dict[str, Any]] = []   # 禁忌（孕期 / 过敏 / 肝肾功能）
    dosage_warnings: list[dict[str, Any]] = []      # 剂量告警
    duplicate_warnings: list[dict[str, Any]] = []   # 重复用药（同通用名）
    special_population: list[dict[str, Any]] = []   # 特殊人群（老年 / 儿童 / 哺乳）
    suggestions: list[str] = []                     # 处置建议（汇总）
    checked_at: str = ""
    rule_source: str = ""                           # 规则来源标识（local_kb / mock / external）
    level: str = "none"                             # 最高告警级别：none / low / medium / high

    @property
    def has_issue(self) -> bool:
        return bool(
            self.conflicts
            or self.contraindications
            or self.dosage_warnings
            or self.duplicate_warnings
            or self.special_population
        )


class RxEngine(ABC):
    """合理用药引擎接口。

    check 入参 prescription 约定结构：
        {
          "patient": {"pregnancy": bool, "allergy": [str, ...]},
          "items": [{"drug_name": str, "dose": str, "freq": str,
                     "daily_dose": float|None, "max_daily_dose": float|None}, ...]
        }
    """

    provider: str = "base"

    @abstractmethod
    def check(self, prescription: dict) -> RxResult:
        ...
