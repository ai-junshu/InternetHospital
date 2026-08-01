"""数据资产采集器（P1 数据资产价值链闭环 · 配置化改造）。

采集逻辑按「采集类型(collector_type)」路由到通用聚合器，而非硬编码资产名匹配。
- 资产可声明 collector_type（PlatDataAsset.collector_type），未声明则按名称推断。
- 通用聚合器依据 CollectorSpec.aggregation 口径计算 data_volume / 质量分。

采集器直接聚合作业库（PostgreSQL）中已落地的业务表，作为「资产盘点」的实时镜像。
"""
from __future__ import annotations

from sqlalchemy import func, select

from app.models.mt_models import (
    MtCarePlan,
    MtEffectTracking,
    MtPainAssessment,
    MtStore,
    MtTherapist,
    MtTreatmentRecord,
)
from app.models.plat_models import PlatDataAsset
from app.services.collector_config import (
    FALLBACK_TYPE,
    get_collector_spec,
    resolve_collector_type,
)


async def collect_asset_metrics(db, asset: PlatDataAsset) -> dict:
    """采集单个资产指标，回写并返回结果字典。

    返回：
        {
          "asset_id", "asset_name", "collector_type",
          "aggregation", "data_volume", "quality_score",
        }
    """
    collector_type = resolve_collector_type(asset.name, getattr(asset, "collector_type", None))
    spec = get_collector_spec(collector_type)

    data_volume, quality_score = await _aggregate(db, collector_type, asset)

    asset.data_volume = data_volume
    # 若资产本身质量分缺失，用采集估算值回写；否则保留人工/上游质量分
    if asset.quality_score is None or asset.quality_score <= 0:
        asset.quality_score = quality_score
    await db.commit()
    await db.refresh(asset)

    return {
        "asset_id": asset.id,
        "asset_name": asset.name,
        "collector_type": collector_type,
        "aggregation": spec.aggregation,
        "data_volume": data_volume,
        "quality_score": asset.quality_score,
    }


async def _aggregate(db, collector_type: str, asset: PlatDataAsset) -> tuple[int, float]:
    """按采集类型执行通用聚合，返回 (data_volume, quality_score)。"""
    spec = get_collector_spec(collector_type)
    quality = asset.quality_score or 0.0

    if collector_type == "treatment_outcome":
        vol = await _count(
            db, [MtTreatmentRecord, MtEffectTracking, MtPainAssessment]
        )
        # 疗效四档聚合：有记录则质量分不低于 0.6（存在有效闭环），否则保留原值
        quality = max(quality, 0.6) if vol > 0 else quality
        return vol, round(quality, 4)

    if collector_type == "customer_profile":
        vol = await _count(db, [MtStore, MtTherapist])  # 门店 + 调理师构成 B 端客户档案基数
        return vol, round(quality, 4)

    if collector_type == "plan_library":
        vol = await _count(db, [MtCarePlan])
        return vol, round(quality, 4)

    if collector_type == "store_metrics":
        vol = await _count(db, [MtTreatmentRecord, MtStore])
        quality = max(quality, 0.7) if vol > 0 else quality
        return vol, round(quality, 4)

    # 兜底：无匹配类型时仅置零，不破坏资产记录
    return 0, round(quality, 4)


async def _count(db, models: list) -> int:
    total = 0
    for m in models:
        try:
            n = await db.scalar(select(func.count()).select_from(m))
            total += int(n or 0)
        except Exception:
            # 表可能尚未迁移；采集器对缺失表容忍
            continue
    return total
