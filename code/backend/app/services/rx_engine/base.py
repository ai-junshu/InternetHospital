"""合理用药引擎抽象层（第三方对接，技术架构第14章）。

处方开方前置校验：用药冲突 / 禁忌 / 剂量告警。
抽象基类 + 工厂，便于后续从 Mock 切换至真实供应商（HttpRxEngine 预留对接点）。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class RxResult(BaseModel):
    """合理用药校验结果。"""

    provider: str
    conflicts: list[dict[str, Any]] = []
    contraindications: list[dict[str, Any]] = []
    dosage_warnings: list[dict[str, Any]] = []
    checked_at: str = ""

    @property
    def has_issue(self) -> bool:
        return bool(self.conflicts or self.contraindications or self.dosage_warnings)


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
