"""数据资产目录接口（plat_data_asset，技术架构第11.2章）。

对外输出走隐私计算/联邦学习，原始不出域（第15.3章）。
敏感等级 L1-L4（第13章）；仅 platform / xingyao 可管理（RBAC），写操作落审计。
"""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError, ErrorCode
from app.core.response import success
from app.core.deps import get_db, require_role, actor_of
from app.core.cache import cached, build_key, cache_delete_prefix
from app.models.plat_models import PlatDataAsset, PlatDataLineage
from app.schemas.common import PageResult
from app.schemas.plat import (
    DataAssetCreate,
    DataAssetOut,
    DataAssetUpdate,
    AssetLineageIn,
    AssetLineageOut,
    AssetValuationOut,
    AssetExportItem,
)
from app.services.audit import write_audit
from app.services.data_asset_collector import collect_asset_metrics

router = APIRouter(prefix="/data-assets", tags=["plat-数据资产"])

_ROLES = ("platform", "xingyao")

# 允许写入的敏感等级集合（第13章 L1-L4）
_SENSITIVITY_LEVELS = {"L1", "L2", "L3", "L4"}


@router.get("", response_model=None)
@cached(
    ttl=None,
    key_builder=lambda page, page_size, name, owner, sensitivity_level, **_: (
        f"assets:{page}:{page_size}:{name}:{owner}:{sensitivity_level}"
    ),
)
async def list_data_assets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    name: str | None = None,
    owner: str | None = None,
    sensitivity_level: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role(*_ROLES)),
):
    conds = [PlatDataAsset.is_deleted.is_(False)]
    if name:
        conds.append(PlatDataAsset.name.ilike(f"%{name}%"))
    if owner:
        conds.append(PlatDataAsset.owner == owner)
    if sensitivity_level:
        conds.append(PlatDataAsset.sensitivity_level == sensitivity_level)
    total = (
        await db.scalar(select(func.count()).select_from(PlatDataAsset).where(*conds)) or 0
    )
    rows = (
        await db.execute(
            select(PlatDataAsset)
            .where(*conds)
            .order_by(PlatDataAsset.id.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    ).scalars().all()
    return success(
        data=PageResult(
            total=total,
            page=page,
            page_size=page_size,
            items=[DataAssetOut.model_validate(r) for r in rows],
        )
    )


@router.get("/export", response_model=None)
async def export_assets(
    sensitivity_level: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role(*_ROLES)),
):
    """对外输出清单（第15.3章 隐私计算/联邦学习，原始不出域）。

    仅返回摘要字段（脱敏，不含 lineage_json / valuation_json 明细）。
    """
    conds = [PlatDataAsset.is_deleted.is_(False)]
    if sensitivity_level:
        conds.append(PlatDataAsset.sensitivity_level == sensitivity_level)
    rows = (
        await db.execute(
            select(PlatDataAsset)
            .where(*conds)
            .order_by(PlatDataAsset.id.desc())
            .limit(500)
        )
    ).scalars().all()
    return success(
        data=[AssetExportItem.model_validate(r).model_dump() for r in rows]
    )


@router.get("/{asset_id}", response_model=None)
async def get_data_asset(
    asset_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role(*_ROLES)),
):
    a = await db.get(PlatDataAsset, asset_id)
    if not a or a.is_deleted:
        raise BusinessError(ErrorCode.RESOURCE_NOT_FOUND, "数据资产不存在")
    return success(data=DataAssetOut.model_validate(a))


@router.post("", response_model=None)
async def create_data_asset(
    body: DataAssetCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role(*_ROLES)),
):
    if body.sensitivity_level and body.sensitivity_level not in _SENSITIVITY_LEVELS:
        raise BusinessError(ErrorCode.PARAM_INVALID, "敏感等级须为 L1-L4")
    a = PlatDataAsset(
        name=body.name,
        owner=body.owner,
        sensitivity_level=body.sensitivity_level,
        usage_scope=body.usage_scope,
        quality_score=body.quality_score,
        update_freq=body.update_freq,
        lineage_json=body.lineage_json,
    )
    db.add(a)
    await db.commit()
    await db.refresh(a)
    await write_audit(
        db,
        action="data_asset.create",
        resource="plat_data_asset",
        role=_user.get("role"),
        actor_id=actor_of(_user),
        after=DataAssetOut.model_validate(a).model_dump(mode="json"),
        ip=request.client.host if request.client else None,
    )
    await cache_delete_prefix(build_key("assets"))  # 失效聚合列表缓存（P5）
    return success(data=DataAssetOut.model_validate(a))


@router.put("/{asset_id}", response_model=None)
async def update_data_asset(
    asset_id: int,
    body: DataAssetUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role(*_ROLES)),
):
    a = await db.get(PlatDataAsset, asset_id)
    if not a or a.is_deleted:
        raise BusinessError(ErrorCode.RESOURCE_NOT_FOUND, "数据资产不存在")
    before = DataAssetOut.model_validate(a).model_dump(mode="json")
    if body.name is not None:
        a.name = body.name
    if body.owner is not None:
        a.owner = body.owner
    if body.sensitivity_level is not None:
        if body.sensitivity_level not in _SENSITIVITY_LEVELS:
            raise BusinessError(ErrorCode.PARAM_INVALID, "敏感等级须为 L1-L4")
        a.sensitivity_level = body.sensitivity_level
    if body.usage_scope is not None:
        a.usage_scope = body.usage_scope
    if body.quality_score is not None:
        a.quality_score = body.quality_score
    if body.update_freq is not None:
        a.update_freq = body.update_freq
    if body.lineage_json is not None:
        a.lineage_json = body.lineage_json
    await db.commit()
    await db.refresh(a)
    await write_audit(
        db,
        action="data_asset.update",
        resource="plat_data_asset",
        role=_user.get("role"),
        actor_id=actor_of(_user),
        before=before,
        after=DataAssetOut.model_validate(a).model_dump(mode="json"),
        ip=request.client.host if request.client else None,
    )
    await cache_delete_prefix(build_key("assets"))  # 失效聚合列表缓存（P5）
    return success(data=DataAssetOut.model_validate(a))


@router.delete("/{asset_id}", response_model=None)
async def delete_data_asset(
    asset_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role(*_ROLES)),
):
    a = await db.get(PlatDataAsset, asset_id)
    if not a or a.is_deleted:
        raise BusinessError(ErrorCode.RESOURCE_NOT_FOUND, "数据资产不存在")
    before = DataAssetOut.model_validate(a).model_dump(mode="json")
    a.is_deleted = True
    await db.commit()
    await write_audit(
        db,
        action="data_asset.delete",
        resource="plat_data_asset",
        role=_user.get("role"),
        actor_id=actor_of(_user),
        before=before,
        ip=request.client.host if request.client else None,
    )
    await cache_delete_prefix(build_key("assets"))  # 失效聚合列表缓存（P5）
    return success(message="已删除", data={"id": asset_id})


# ===================== P1 数据资产闭环 =====================
_LIFECYCLE_FLOW = {
    "collected": "cleaned",
    "cleaned": "stored",
    "stored": "analyzed",
    "analyzed": "output",
    "output": "archived",
    "archived": "destroyed",
}
_SENSITIVITY_FACTOR = {"L1": 1.0, "L2": 1.5, "L3": 2.5, "L4": 4.0}


def _valuation(a: PlatDataAsset) -> dict:
    """资产估值（融资用，第11.2章）：质量分 × 数据量 × 敏感度系数。"""
    factor = _SENSITIVITY_FACTOR.get(a.sensitivity_level or "L1", 1.0)
    volume = a.data_volume or 0
    score = a.quality_score or 0.0
    return {
        "id": a.id,
        "asset_id": a.id,
        "quality_score": score,
        "data_volume": volume,
        "sensitivity_level": a.sensitivity_level,
        "sensitivity_factor": factor,
        "estimated_value": round(score * volume * factor, 2),
        "formula": "quality_score * data_volume * sensitivity_factor",
    }


@router.get("/{asset_id}/lineage", response_model=None)
async def get_asset_lineage(
    asset_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role(*_ROLES)),
):
    a = await db.get(PlatDataAsset, asset_id)
    if not a or a.is_deleted:
        raise BusinessError(ErrorCode.RESOURCE_NOT_FOUND, "数据资产不存在")
    # 上游（我依赖谁）与下游（谁依赖我）
    up = (
        await db.execute(
            select(PlatDataLineage).where(
                PlatDataLineage.downstream_asset_id == asset_id
            )
        )
    ).scalars().all()
    down = (
        await db.execute(
            select(PlatDataLineage).where(
                PlatDataLineage.upstream_asset_id == asset_id
            )
        )
    ).scalars().all()
    return success(
        data={
            "upstream": [AssetLineageOut.model_validate(r).model_dump() for r in up],
            "downstream": [AssetLineageOut.model_validate(r).model_dump() for r in down],
        }
    )


@router.post("/{asset_id}/lineage", response_model=None)
async def add_asset_lineage(
    asset_id: int,
    body: AssetLineageIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role(*_ROLES)),
):
    a = await db.get(PlatDataAsset, asset_id)
    if not a or a.is_deleted:
        raise BusinessError(ErrorCode.RESOURCE_NOT_FOUND, "数据资产不存在")
    # 任意一端须为当前资产，禁止凭空建无关血缘
    if body.upstream_asset_id != asset_id and body.downstream_asset_id != asset_id:
        raise BusinessError(ErrorCode.PARAM_INVALID, "血缘须以当前资产为上游或下游")
    link = PlatDataLineage(
        upstream_asset_id=body.upstream_asset_id,
        downstream_asset_id=body.downstream_asset_id,
        transform_logic=body.transform_logic,
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    await write_audit(
        db,
        action="data_asset.lineage.add",
        resource="plat_data_lineage",
        role=_user.get("role"),
        actor_id=actor_of(_user),
        after=AssetLineageOut.model_validate(link).model_dump(mode="json"),
        ip=request.client.host if request.client else None,
    )
    return success(data=AssetLineageOut.model_validate(link))


@router.get("/{asset_id}/valuation", response_model=None)
async def get_asset_valuation(
    asset_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role(*_ROLES)),
):
    a = await db.get(PlatDataAsset, asset_id)
    if not a or a.is_deleted:
        raise BusinessError(ErrorCode.RESOURCE_NOT_FOUND, "数据资产不存在")
    val = _valuation(a)
    a.valuation_json = val  # 物化最新估值，便于导出
    await db.commit()
    return success(data=AssetValuationOut(**val).model_dump())


@router.post("/{asset_id}/lifecycle", response_model=None)
async def advance_asset_lifecycle(
    asset_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role(*_ROLES)),
):
    a = await db.get(PlatDataAsset, asset_id)
    if not a or a.is_deleted:
        raise BusinessError(ErrorCode.RESOURCE_NOT_FOUND, "数据资产不存在")
    cur = a.lifecycle_status
    nxt = _LIFECYCLE_FLOW.get(cur)
    if nxt is None:
        raise BusinessError(ErrorCode.PARAM_INVALID, f"当前状态 {cur} 无后续流转")
    before = DataAssetOut.model_validate(a).model_dump(mode="json")
    a.lifecycle_status = nxt
    await db.commit()
    await db.refresh(a)
    await write_audit(
        db,
        action="data_asset.lifecycle",
        resource="plat_data_asset",
        role=_user.get("role"),
        actor_id=actor_of(_user),
        before=before,
        after=DataAssetOut.model_validate(a).model_dump(mode="json"),
        ip=request.client.host if request.client else None,
    )
    return success(data=DataAssetOut.model_validate(a))


@router.post("/{asset_id}/collect", response_model=None)
async def collect_asset(
    asset_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role(*_ROLES)),
):
    """手动触发资产指标采集：从业务表聚合质量分与数据量回写（P1 运行时闭环）。"""
    a = await db.get(PlatDataAsset, asset_id)
    if not a or a.is_deleted:
        raise BusinessError(ErrorCode.RESOURCE_NOT_FOUND, "数据资产不存在")
    metrics = await collect_asset_metrics(db, a.name)
    if metrics is None:
        return success(
            data=DataAssetOut.model_validate(a),
            message="无匹配采集器，指标未变更",
        )
    before = DataAssetOut.model_validate(a).model_dump(mode="json")
    if metrics.get("data_volume") is not None:
        a.data_volume = metrics["data_volume"]
    if metrics.get("quality_score") is not None:
        a.quality_score = metrics["quality_score"]
    await db.commit()
    await db.refresh(a)
    await write_audit(
        db,
        action="data_asset.collect",
        resource="plat_data_asset",
        role=_user.get("role"),
        actor_id=actor_of(_user),
        before=before,
        after=DataAssetOut.model_validate(a).model_dump(mode="json"),
        ip=request.client.host if request.client else None,
    )
    return success(data=DataAssetOut.model_validate(a))
