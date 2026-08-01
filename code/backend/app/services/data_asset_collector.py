"""数据资产指标采集服务（P1 运行时闭环）。

将「治疗效果数据集」等资产从 seed 静态质量分，升级为基于业务表实时聚合
的动态质量分与数据量，回写 plat_data_asset，支撑融资估值。原始不出域。
"""
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mt_models import (
    MtCarePlan,
    MtEffectTracking,
    MtTreatmentRecord,
    MtCustomer,
)

# 资产名称 → 采集器映射（按 name 精确/包含匹配）
_COLLECTORS = {}


def _register(name_key):
    def deco(fn):
        _COLLECTORS[name_key] = fn
        return fn

    return deco


@_register("治疗效果数据集")
async def _collect_treatment_effect(db: AsyncSession) -> dict:
    """聚合连续结构化治疗效果数据：客户数、治疗记录数、显效占比。"""
    customer_cnt = (
        await db.scalar(select(func.count()).select_from(MtCustomer)) or 0
    )
    record_cnt = (
        await db.scalar(select(func.count()).select_from(MtTreatmentRecord)) or 0
    )
    eff_cnt = (
        await db.scalar(
            select(func.count()).select_from(MtEffectTracking).where(
                MtEffectTracking.effect_level.in_(["significant", "effective"])
            )
        )
        or 0
    )
    total_eff = (
        await db.scalar(select(func.count()).select_from(MtEffectTracking)) or 0
    )
    # 质量分：覆盖率（有疗效判定的客户/总客户）与显效率综合
    effective_rate = (eff_cnt / total_eff) if total_eff else 0.0
    coverage = min(1.0, (total_eff / customer_cnt)) if customer_cnt else 0.0
    quality = round(0.5 * coverage + 0.5 * effective_rate, 3)
    return {
        "data_volume": record_cnt,
        "quality_score": quality,
    }


@_register("调理方案数据集")
async def _collect_care_plan(db: AsyncSession) -> dict:
    plan_cnt = await db.scalar(select(func.count()).select_from(MtCarePlan)) or 0
    return {"data_volume": plan_cnt, "quality_score": round(min(1.0, plan_cnt / 1000), 3)}


async def collect_asset_metrics(db: AsyncSession, asset_name: str) -> Optional[dict]:
    """按资产名匹配采集器并聚合指标；无匹配返回 None。"""
    for key, fn in _COLLECTORS.items():
        if key in (asset_name or ""):
            return await fn(db)
    return None
