"""AI 模型管理接口（plat_ai_model，技术架构第11.2/12.3章）。

模型版本与效果指标可追溯；上线经合规大脑校验（第13.3章）。
仅 platform / xingyao 角色可管理（RBAC），全部写操作落审计（第10.2/13章）。
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError, ErrorCode
from app.core.response import success
from app.core.deps import get_db, require_role, actor_of
from app.models.plat_models import PlatAiModel
from app.schemas.common import PageResult
from app.schemas.plat import AiModelCreate, AiModelOut, AiModelUpdate
from app.services.audit import write_audit

router = APIRouter(prefix="/ai-models", tags=["plat-AI模型"])

_ROLES = ("platform", "xingyao")


def _touch_status(m: PlatAiModel, status: str) -> None:
    m.status = status
    now = datetime.now(timezone.utc)
    if status == "online":
        m.online_at = now
        m.offline_at = None
    elif status == "offline":
        m.offline_at = now


@router.get("", response_model=None)
async def list_ai_models(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    name: str | None = None,
    status: str | None = None,
    algo_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role(*_ROLES)),
):
    conds = [PlatAiModel.is_deleted.is_(False)]
    if name:
        conds.append(PlatAiModel.name.ilike(f"%{name}%"))
    if status:
        conds.append(PlatAiModel.status == status)
    if algo_type:
        conds.append(PlatAiModel.algo_type == algo_type)
    total = (
        await db.scalar(select(func.count()).select_from(PlatAiModel).where(*conds)) or 0
    )
    rows = (
        await db.execute(
            select(PlatAiModel)
            .where(*conds)
            .order_by(PlatAiModel.id.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    ).scalars().all()
    return success(
        data=PageResult(
            total=total,
            page=page,
            page_size=page_size,
            items=[AiModelOut.model_validate(r) for r in rows],
        )
    )


@router.get("/{model_id}", response_model=None)
async def get_ai_model(
    model_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role(*_ROLES)),
):
    m = await db.get(PlatAiModel, model_id)
    if not m or m.is_deleted:
        raise BusinessError(ErrorCode.RESOURCE_NOT_FOUND, "模型不存在")
    return success(data=AiModelOut.model_validate(m))


@router.post("", response_model=None)
async def create_ai_model(
    body: AiModelCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role(*_ROLES)),
):
    m = PlatAiModel(
        name=body.name,
        version=body.version,
        train_dataset_id=body.train_dataset_id,
        algo_type=body.algo_type,
        metrics_json=body.metrics_json,
        status=body.status,
    )
    _touch_status(m, body.status)
    db.add(m)
    await db.commit()
    await db.refresh(m)
    await write_audit(
        db,
        action="ai_model.create",
        resource="plat_ai_model",
        role=_user.get("role"),
        actor_id=actor_of(_user),
        after=AiModelOut.model_validate(m).model_dump(mode="json"),
        ip=request.client.host if request.client else None,
    )
    return success(data=AiModelOut.model_validate(m))


@router.put("/{model_id}", response_model=None)
async def update_ai_model(
    model_id: int,
    body: AiModelUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role(*_ROLES)),
):
    m = await db.get(PlatAiModel, model_id)
    if not m or m.is_deleted:
        raise BusinessError(ErrorCode.RESOURCE_NOT_FOUND, "模型不存在")
    before = AiModelOut.model_validate(m).model_dump(mode="json")
    if body.name is not None:
        m.name = body.name
    if body.version is not None:
        m.version = body.version
    if body.train_dataset_id is not None:
        m.train_dataset_id = body.train_dataset_id
    if body.algo_type is not None:
        m.algo_type = body.algo_type
    if body.metrics_json is not None:
        m.metrics_json = body.metrics_json
    if body.status is not None and body.status != m.status:
        _touch_status(m, body.status)
    await db.commit()
    await db.refresh(m)
    await write_audit(
        db,
        action="ai_model.update",
        resource="plat_ai_model",
        role=_user.get("role"),
        actor_id=actor_of(_user),
        before=before,
        after=AiModelOut.model_validate(m).model_dump(mode="json"),
        ip=request.client.host if request.client else None,
    )
    return success(data=AiModelOut.model_validate(m))


@router.post("/{model_id}/online", response_model=None)
async def online_ai_model(
    model_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role(*_ROLES)),
):
    m = await db.get(PlatAiModel, model_id)
    if not m or m.is_deleted:
        raise BusinessError(ErrorCode.RESOURCE_NOT_FOUND, "模型不存在")
    _touch_status(m, "online")
    await db.commit()
    await db.refresh(m)
    await write_audit(
        db,
        action="ai_model.online",
        resource="plat_ai_model",
        role=_user.get("role"),
        actor_id=actor_of(_user),
        after=AiModelOut.model_validate(m).model_dump(mode="json"),
        ip=request.client.host if request.client else None,
    )
    return success(data=AiModelOut.model_validate(m))


@router.post("/{model_id}/offline", response_model=None)
async def offline_ai_model(
    model_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role(*_ROLES)),
):
    m = await db.get(PlatAiModel, model_id)
    if not m or m.is_deleted:
        raise BusinessError(ErrorCode.RESOURCE_NOT_FOUND, "模型不存在")
    _touch_status(m, "offline")
    await db.commit()
    await db.refresh(m)
    await write_audit(
        db,
        action="ai_model.offline",
        resource="plat_ai_model",
        role=_user.get("role"),
        actor_id=actor_of(_user),
        after=AiModelOut.model_validate(m).model_dump(mode="json"),
        ip=request.client.host if request.client else None,
    )
    return success(data=AiModelOut.model_validate(m))


@router.delete("/{model_id}", response_model=None)
async def delete_ai_model(
    model_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role(*_ROLES)),
):
    m = await db.get(PlatAiModel, model_id)
    if not m or m.is_deleted:
        raise BusinessError(ErrorCode.RESOURCE_NOT_FOUND, "模型不存在")
    before = AiModelOut.model_validate(m).model_dump(mode="json")
    m.is_deleted = True
    await db.commit()
    await write_audit(
        db,
        action="ai_model.delete",
        resource="plat_ai_model",
        role=_user.get("role"),
        actor_id=actor_of(_user),
        before=before,
        ip=request.client.host if request.client else None,
    )
    return success(message="已删除", data={"id": model_id})
