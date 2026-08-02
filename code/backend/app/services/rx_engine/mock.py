"""Mock 合理用药引擎（内置最小规则集，作**降级基准**与单测对照，非生产推荐）。

⚠️ 本实现仅覆盖极少数示范规则（相互作用 3 对、孕期禁用 4 种、剂量超量），
    远不足以承担真实处方审核。生产默认走 LocalRxEngine（local 真引擎），
    仅在配置 `rx_engine_provider=mock` 或外部/本地引擎异常时回退此处。

规则覆盖（基准集）：
- 用药冲突（相互作用）：阿司匹林+华法林、布洛芬+阿司匹林、头孢+酒/酒精。
- 禁忌：孕期禁用药物、患者已知过敏药物。
- 剂量告警：daily_dose 超过 max_daily_dose。

接口与返回结构与 LocalRxEngine / HttpRxEngine 保持一致（均返回 RxResult）。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.rx_engine.base import RxEngine, RxResult

# 用药冲突对（无序）：(药A关键字, 药B关键字, 风险说明)
_INTERACTIONS = [
    ("阿司匹林", "华法林", "增加出血风险，需监测凝血"),
    ("布洛芬", "阿司匹林", "增加胃肠道出血风险，避免联用"),
    ("头孢", "酒", "双硫仑样反应（面部潮红、心悸、呼吸困难）"),
    ("头孢", "酒精", "双硫仑样反应（面部潮红、心悸、呼吸困难）"),
]

# 孕期禁用药物关键字
_PREGNANCY_BAN = ["左氧氟沙星", "甲硝唑", "四环素", "米非司酮"]


class MockRxEngine(RxEngine):
    provider = "mock"

    def check(self, prescription: dict) -> RxResult:
        patient = prescription.get("patient") or {}
        items = prescription.get("items") or []
        pregnancy = bool(patient.get("pregnancy"))
        allergies = [str(a) for a in (patient.get("allergy") or [])]

        conflicts: list[dict[str, Any]] = []
        contraindications: list[dict[str, Any]] = []
        dosage_warnings: list[dict[str, Any]] = []

        names = [str(i.get("drug_name", "")) for i in items]

        # 1) 用药冲突（两两组合）
        for a in range(len(names)):
            for b in range(a + 1, len(names)):
                for ka, kb, desc in _INTERACTIONS:
                    if (ka in names[a] and kb in names[b]) or (ka in names[b] and kb in names[a]):
                        conflicts.append(
                            {"drug_a": names[a], "drug_b": names[b], "level": "high", "desc": desc}
                        )

        # 2) 禁忌：孕期 / 过敏
        for i, it in enumerate(items):
            nm = str(it.get("drug_name", ""))
            if pregnancy and any(ban in nm for ban in _PREGNANCY_BAN):
                contraindications.append(
                    {"drug": nm, "type": "pregnancy", "level": "high", "desc": "孕期禁用"}
                )
            for al in allergies:
                if al and al in nm:
                    contraindications.append(
                        {"drug": nm, "type": "allergy", "level": "high", "desc": f"患者已知过敏：{al}"}
                    )

        # 3) 剂量告警
        for it in items:
            dd = it.get("daily_dose")
            mx = it.get("max_daily_dose")
            if dd is not None and mx is not None:
                try:
                    if float(dd) > float(mx):
                        dosage_warnings.append(
                            {
                                "drug": str(it.get("drug_name", "")),
                                "daily_dose": dd,
                                "max_daily_dose": mx,
                                "level": "medium",
                                "desc": "日剂量超过上限",
                            }
                        )
                except (TypeError, ValueError):
                    pass

        return RxResult(
            provider=self.provider,
            conflicts=conflicts,
            contraindications=contraindications,
            dosage_warnings=dosage_warnings,
            checked_at=datetime.now(timezone.utc).isoformat(),
        )
