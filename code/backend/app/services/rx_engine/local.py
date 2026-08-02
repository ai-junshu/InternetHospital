"""合理用药本地真引擎（LocalRxEngine）。

内置一份可维护的临床规则知识库（纯 Python 常量表），不依赖任何外部付费
供应商即可覆盖真实常用场景：药物相互作用、禁忌人群、重复用药、特殊人群
（老年/儿童/哺乳期/肝功能不全/肾功能不全）与剂量告警。

规则表设计为可被 `rx_engine_kb_path` 指向的外部 JSON 覆盖（可选），从而
支持运营/药师持续补充而无需改代码。

> 说明：本引擎用于「处方辅助审核」与合规留痕，不能替代临床医师最终判断，
> 也不构成诊疗建议。规则集为常见用药安全要点摘编，非穷尽。
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from typing import Any

from app.services.rx_engine.base import RxEngine, RxResult

# ---------------------------------------------------------------------------
# 内置知识库（DEFAULT_KB）
# 字段约定：
#   interactions: list[(通用名A, 通用名B, {severity, desc, advice})] 无序对
#   contraindications: list[{generic, pops, severity, desc, advice}]
#   duplicate: list[{generic, severity, desc, advice}]  重复用药同通用名
#   special_population: list[{pop, generic, severity, desc, advice}]
#   dosage: dict[通用名 -> 成人每日上限 mg]
# 人群标签：pregnancy(孕期) / lactation(哺乳期) / child(儿童<12) /
#          elderly(老年>=65) / hepatic(肝功能不全) / renal(肾功能不全)
# ---------------------------------------------------------------------------
DEFAULT_KB: dict[str, Any] = {
    "interactions": [
        # 中枢抑制叠加
        ("acetaminophen", "diphenhydramine", {
            "severity": "medium",
            "desc": "含对乙酰氨基酚与苯海拉明联用可增强中枢抑制，易致嗜睡、跌倒。",
            "advice": "避免同时驾驶/操作机械；夜间短期联用需告知患者。",
        }),
        ("diazepam", "diphenhydramine", {
            "severity": "high",
            "desc": "苯二氮䓬类与抗组胺药联用显著增强镇静、呼吸抑制风险。",
            "advice": "不建议联用；如必须，严密监测意识与呼吸。",
        }),
        # 出血风险叠加
        ("aspirin", "ibuprofen", {
            "severity": "high",
            "desc": "阿司匹林与布洛芬联用增加消化道出血与溃疡风险，且布洛芬削弱阿司匹林心血管保护。",
            "advice": "避免长期联用；如需镇痛可改用对胃黏膜刺激较小的方案并加用质子泵抑制剂。",
        }),
        ("warfarin", "aspirin", {
            "severity": "high",
            "desc": "华法林与阿司匹林联用显著增加出血风险。",
            "advice": "必须在医师指导下联用并规律监测 INR。",
        }),
        ("warfarin", "ibuprofen", {
            "severity": "high",
            "desc": "华法林与非甾体抗炎药联用增加消化道出血。",
            "advice": "避免联用或加用胃保护剂并监测 INR。",
        }),
        # 肝毒性叠加
        ("acetaminophen", "ibuprofen", {
            "severity": "medium",
            "desc": "长期大剂量对乙酰氨基酚联用 NSAIDs 增加肝/肾负担。",
            "advice": "控制每日对乙酰氨基酚总量≤2000mg（肝功能不全者更低）。",
        }),
        ("metformin", "alcohol", {
            "severity": "medium",
            "desc": "二甲双胍与大量饮酒可诱发乳酸酸中毒。",
            "advice": "用药期间避免饮酒。",
        }),
        # 5-羟色胺综合征
        ("sertraline", "tramadol", {
            "severity": "high",
            "desc": "SSRI 与曲马多联用可能诱发 5-羟色胺综合征。",
            "advice": "避免联用；必要时换用非 5-羟色胺能镇痛方案。",
        }),
        # QT 延长
        ("azithromycin", "amiodarone", {
            "severity": "high",
            "desc": "大环内酯类与胺碘酮联用延长 QT 间期，致心律失常。",
            "advice": "避免联用；如必须，监测心电图与电解质。",
        }),
        # 血压/电解质叠加
        ("lisinopril", "spironolactone", {
            "severity": "high",
            "desc": "ACEI 与保钾利尿药联用致高钾血症、低血压。",
            "advice": "监测血钾与肾功能；避免高钾饮食。",
        }),
    ],
    "contraindications": [
        {
            "generic": "ibuprofen",
            "pops": ["pregnancy"],
            "severity": "high",
            "desc": "妊娠晚期禁用 NSAIDs（包括布洛芬），可致胎儿动脉导管早闭、羊水过少。",
            "advice": "孕期镇痛改用对乙酰氨基酚（遵产科建议）。",
        },
        {
            "generic": "ibuprofen",
            "pops": ["renal", "hepatic"],
            "severity": "medium",
            "desc": "肾功能不全/肝功能不全者 NSAIDs 可加重肾损伤。",
            "advice": "慎用或减量，监测肾功能。",
        },
        {
            "generic": "warfarin",
            "pops": ["pregnancy"],
            "severity": "high",
            "desc": "华法林妊娠禁用，致畸且出血风险。",
            "advice": "改用肝素类（遵专科建议）。",
        },
        {
            "generic": "metformin",
            "pops": ["renal"],
            "severity": "high",
            "desc": "eGFR<30 禁用二甲双胍，防乳酸酸中毒。",
            "advice": "评估肾功能后决定是否用药。",
        },
        {
            "generic": "diazepam",
            "pops": ["pregnancy", "lactation"],
            "severity": "medium",
            "desc": "苯二氮䓬类可透过胎盘/乳汁，孕期哺乳期慎用。",
            "advice": "权衡利弊，尽量短期使用。",
        },
        {
            "generic": "tramadol",
            "pops": ["lactation"],
            "severity": "high",
            "desc": "曲马多经乳汁分泌，婴儿可致呼吸抑制/成瘾。",
            "advice": "哺乳期避免使用。",
        },
        {
            "generic": "azithromycin",
            "pops": ["hepatic"],
            "severity": "medium",
            "desc": "肝功能不全者大环内酯类代谢减慢，蓄积风险。",
            "advice": "慎用并监测肝功能。",
        },
        {
            "generic": "acetaminophen",
            "pops": ["hepatic"],
            "severity": "high",
            "desc": "肝功能不全者对乙酰氨基酚代谢受限，易蓄积肝毒。",
            "advice": "日总量≤2000mg 或更低，监测肝功能。",
        },
    ],
    "duplicate": [
        {
            "generic": "acetaminophen",
            "severity": "medium",
            "desc": "多种复方感冒药含对乙酰氨基酚，重复开具易致过量肝损伤。",
            "advice": "合并计算每日对乙酰氨基酚总量，避免多源叠加。",
        },
        {
            "generic": "ibuprofen",
            "severity": "low",
            "desc": "同一通用名多规格/多频次开具属重复用药。",
            "advice": "确认是否必要，避免重复。",
        },
    ],
    "special_population": [
        {
            "pop": "elderly",
            "generic": "diazepam",
            "severity": "medium",
            "desc": "老年人生理功能减退，苯二氮䓬类易致跌倒、认知障碍。",
            "advice": "起始低剂量，最短疗程。",
        },
        {
            "pop": "elderly",
            "generic": "warfarin",
            "severity": "medium",
            "desc": "老年人华法林出血风险高，需更频繁监测 INR。",
            "advice": "加强 INR 监测与用药教育。",
        },
        {
            "pop": "child",
            "generic": "aspirin",
            "severity": "high",
            "desc": "儿童病毒感染期用阿司匹林可诱发瑞氏综合征。",
            "advice": "18 岁以下退热避免使用阿司匹林，改用对乙酰氨基酚/布洛芬。",
        },
        {
            "pop": "child",
            "generic": "ibuprofen",
            "severity": "low",
            "desc": "婴幼儿用 NSAIDs 需按体重精确计算剂量。",
            "advice": "按体重给药并确认无脱水。",
        },
        {
            "pop": "lactation",
            "generic": "ibuprofen",
            "severity": "low",
            "desc": "布洛芬哺乳期相对安全，但仍建议最短疗程。",
            "advice": "按需短期使用。",
        },
        {
            "pop": "renal",
            "generic": "lisinopril",
            "severity": "medium",
            "desc": "肾功能不全者 ACEI 可升高血钾、恶化肾功能。",
            "advice": "监测电解质与肾功能。",
        },
    ],
    "dosage": {
        # 通用名 -> 成人每日上限 mg（仅作超量提醒，非治疗推荐）
        "acetaminophen": 4000,
        "ibuprofen": 3200,
        "aspirin": 4000,
    },
}


def _load_kb(kb_path: str | None) -> dict[str, Any]:
    """载入知识库：优先外部 JSON 覆盖，否则用内置 DEFAULT_KB。"""
    if kb_path:
        p = Path(kb_path)
        if p.exists():
            try:
                with p.open(encoding="utf-8") as f:
                    data = json.load(f)
                # 外部知识库以 DEFAULT_KB 为基座，未提供的键沿用内置
                return {k: data.get(k, DEFAULT_KB.get(k, [])) for k in DEFAULT_KB}
            except (json.JSONDecodeError, OSError):
                # 解析失败回退内置，避免引擎整体不可用
                return DEFAULT_KB
    return DEFAULT_KB


def _norm(name: str) -> str:
    return (name or "").strip().lower()


def _parse_age(patient: dict | None) -> int | None:
    if not patient:
        return None
    age = patient.get("age")
    if isinstance(age, int):
        return age
    try:
        return int(age)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


_SEVERITY_RANK = {"none": 0, "low": 1, "medium": 2, "high": 3}


class LocalRxEngine(RxEngine):
    """基于内置/可配置知识库的合理用药真引擎。

    覆盖：药物相互作用、人群禁忌、重复用药、特殊人群、剂量上限。
    返回结果含分级（level）、规则来源（rule_source=local_kb）与处置建议。
    """

    def __init__(self, kb_path: str | None = None) -> None:
        self._kb = _load_kb(kb_path)
        self._kb_path = kb_path

    def check(self, prescription: dict[str, Any]) -> RxResult:
        items: list[dict[str, Any]] = [dict(it) for it in prescription.get("items", [])]
        patient = prescription.get("patient") or {}
        conflicts: list[dict[str, Any]] = []
        contraindications: list[dict[str, Any]] = []
        duplicate_warnings: list[dict[str, Any]] = []
        special_population: list[dict[str, Any]] = []
        dosage_warnings: list[dict[str, Any]] = []
        suggestions: list[str] = []

        generics = [_norm(it.get("generic_name", "")) for it in items if _norm(it.get("generic_name", ""))]
        patient_pops = self._patient_pops(patient)

        # 1) 两两相互作用
        for i in range(len(generics)):
            for j in range(i + 1, len(generics)):
                key = tuple(sorted([generics[i], generics[j]]))
                for a, b, rule in self._kb.get("interactions", []):
                    if tuple(sorted([_norm(a), _norm(b)])) == key:
                        conflicts.append(
                            {
                                "type": "drug_interaction",
                                "drugs": [generics[i], generics[j]],
                                "severity": rule["severity"],
                                "desc": rule["desc"],
                                "advice": rule["advice"],
                            }
                        )
                        suggestions.append(rule["advice"])
                        break

        # 2) 人群禁忌
        for rule in self._kb.get("contraindications", []):
            g = _norm(rule.get("generic", ""))
            if g in generics and (set(rule.get("pops", [])) & patient_pops):
                hit_pop = sorted(set(rule.get("pops", [])) & patient_pops)
                contraindications.append(
                    {
                        "type": "contraindication",
                        "drug": g,
                        "populations": hit_pop,
                        "severity": rule["severity"],
                        "desc": rule["desc"],
                        "advice": rule["advice"],
                    }
                )
                suggestions.append(rule["advice"])

        # 3) 重复用药（同通用名多开）
        seen: dict[str, int] = {}
        for g in generics:
            seen[g] = seen.get(g, 0) + 1
        for rule in self._kb.get("duplicate", []):
            g = _norm(rule.get("generic", ""))
            if g in seen and seen[g] > 1:
                duplicate_warnings.append(
                    {
                        "type": "duplicate",
                        "drug": g,
                        "count": seen[g],
                        "severity": rule["severity"],
                        "desc": rule["desc"],
                        "advice": rule["advice"],
                    }
                )
                suggestions.append(rule["advice"])

        # 4) 特殊人群
        for rule in self._kb.get("special_population", []):
            g = _norm(rule.get("generic", ""))
            pop = rule.get("pop")
            if g in generics and pop in patient_pops:
                special_population.append(
                    {
                        "type": "special_population",
                        "drug": g,
                        "population": pop,
                        "severity": rule["severity"],
                        "desc": rule["desc"],
                        "advice": rule["advice"],
                    }
                )
                suggestions.append(rule["advice"])

        # 5) 剂量上限
        for it in items:
            g = _norm(it.get("generic_name", ""))
            cap = self._kb.get("dosage", {}).get(g)
            md = it.get("max_daily_dose")
            if cap and md and md > cap:
                dosage_warnings.append(
                    {
                        "type": "dosage",
                        "drug": g,
                        "max_daily_dose": md,
                        "cap": cap,
                        "severity": "high",
                        "desc": f"{g} 单日最大剂量 {md}mg 超出安全上限 {cap}mg。",
                        "advice": "下调剂量或更换方案，避免蓄积毒性。",
                    }
                )
                suggestions.append("下调剂量或更换方案，避免蓄积毒性。")

        level = self._level(
            conflicts, contraindications, duplicate_warnings, special_population, dosage_warnings
        )
        return RxResult(
            provider="local",
            conflicts=conflicts,
            contraindications=contraindications,
            dosage_warnings=dosage_warnings,
            duplicate_warnings=duplicate_warnings,
            special_population=special_population,
            suggestions=sorted(set(suggestions)),
            checked_at=_dt.datetime.now(_dt.timezone.utc).isoformat(),
            rule_source="local_kb",
            level=level,
        )

    # ---- 内部工具 ----
    def _patient_pops(self, patient: dict[str, Any]) -> set[str]:
        pops: set[str] = set()
        if not patient:
            return pops
        # 显式标签优先
        for tag in patient.get("populations", []) or []:
            pops.add(_norm(tag))
        # 由结构化字段推导（兼容 pregnancy / is_pregnant 两种键名）
        _preg = patient.get("is_pregnant", patient.get("pregnancy", ""))
        if str(_preg).lower() in ("1", "true", "yes", "是"):
            pops.add("pregnancy")
        if str(patient.get("is_lactating", "")).lower() in ("1", "true", "yes", "是"):
            pops.add("lactation")
        age = _parse_age(patient)
        if age is not None:
            if age >= 65:
                pops.add("elderly")
            if age < 12:
                pops.add("child")
        if str(patient.get("hepatic_insufficiency", "")).lower() in ("1", "true", "yes", "是"):
            pops.add("hepatic")
        if str(patient.get("renal_insufficiency", "")).lower() in ("1", "true", "yes", "是"):
            pops.add("renal")
        return pops

    def _level(self, *lists: list[dict[str, Any]]) -> str:
        top = "none"
        for lst in lists:
            for item in lst:
                sev = item.get("severity", "low")
                if _SEVERITY_RANK.get(sev, 1) > _SEVERITY_RANK.get(top, 0):
                    top = sev
        return top
