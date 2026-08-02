"""健康数据中台：调理师排班 + 标签分配（P6）。

- 排班按 store_id 行级隔离（store/therapist 角色仅能操作本店；platform/xingyao 可下钻）。
- 标签：目录（platform/xingyao 维护）+ 分配给具体调理师（store/therapist/platform 可分配）。
- 所有写操作均走审计留痕。
"""
from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import actor_of, get_db, require_role, store_scope
from app.core.errors import BusinessError, ErrorCode
from app.core.response import success
from app.models.mt_models import MtTherapist, MtTherapistSchedule, MtTherapistTag, MtTherapistTagRel
from app.schemas.common import PageResult
from app.schemas.mt import (
    TherapistScheduleCreate,
    TherapistScheduleOut,
    TherapistScheduleUpdate,
    TherapistTagCreate,
    TherapistTagOut,
)
from app.services.audit import write_audit

schedule_router = APIRouter(prefix="/therapists", tags=["mt-调理师排班"])
tag_router = APIRouter(prefix="/therapist-tags", tags=["mt-调理师标签"])


class _TagAssignIn(BaseModel):
    tag_id: int


async def _load_therapist(
    db: AsyncSession, therapist_id: int, scope: int | None
) -> MtTherapist:
    """加载调理师并做行级隔离校验。

    scope 由路由层 Depends(store_scope) 注入：
    - store/therapist：强制为 JWT store_id，仅能操作本店调理师；
    - platform/xingyao：None 表示全量，或为下钻指定的 store_id。
    """
    th = await db.get(MtTherapist, therapist_id)
    if not th or th.is_deleted:
        raise BusinessError(ErrorCode.NOT_FOUND, "调理师不存在")
    if scope is not None and th.store_id != scope:
        raise BusinessError(ErrorCode.FORBIDDEN, "无权操作该店调理师")
    return th


# ===================== 调理师排班 =====================
@schedule_router.post("/{therapist_id}/schedules", response_model=None)
async def create_therapist_schedule(
    therapist_id: int,
    body: TherapistScheduleCreate,
    request: Request,
    user: dict = Depends(require_role("store", "therapist", "platform", "xingyao")),
    scope: int | None = Depends(store_scope),
    db: AsyncSession = Depends(get_db),
):
    th = await _load_therapist(db, therapist_id, scope)
    sch = MtTherapistSchedule(
        therapist_id=th.id,
        store_id=th.store_id,
        **body.model_dump(exclude={"therapist_id"}),
    )
    db.add(sch)
    await db.commit()
    await db.refresh(sch)
    await write_audit(
        db,
        action="therapist_schedule.create",
        resource="mt_therapist_schedule",

        role=user.get("role"),
        actor_id=actor_of(user),
        after={"id": sch.id, "therapist_id": th.id, "store_id": th.store_id, "work_date": str(sch.work_date)},
        ip=request.client.host if request.client else None,
    )
    return success(data=TherapistScheduleOut.model_validate(sch))


@schedule_router.get("/{therapist_id}/schedules", response_model=None)
async def list_therapist_schedules(
    therapist_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    work_date: date | None = None,
    am_pm: str | None = None,
    status: str | None = None,
    user: dict = Depends(require_role("store", "therapist", "platform", "xingyao")),
    scope: int | None = Depends(store_scope),
    db: AsyncSession = Depends(get_db),
):
    await _load_therapist(db, therapist_id, scope)  # 行级隔离校验
    conds = [MtTherapistSchedule.therapist_id == therapist_id, MtTherapistSchedule.is_deleted.is_(False)]
    if work_date is not None:
        conds.append(MtTherapistSchedule.work_date == work_date)
    if am_pm:
        conds.append(MtTherapistSchedule.am_pm == am_pm)
    if status:
        conds.append(MtTherapistSchedule.status == status)
    total = (await db.execute(select(func.count()).select_from(MtTherapistSchedule).where(*conds))).scalar() or 0
    rows = (
        await db.execute(
            select(MtTherapistSchedule)
            .where(*conds)
            .order_by(MtTherapistSchedule.work_date, MtTherapistSchedule.start_time)
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    ).scalars().all()
    return success(
        data=PageResult[TherapistScheduleOut](
            total=total, page=page, page_size=page_size, items=[TherapistScheduleOut.model_validate(r) for r in rows]
        )
    )


@schedule_router.patch("/{therapist_id}/schedules/{schedule_id}", response_model=None)
async def update_therapist_schedule(
    therapist_id: int,
    schedule_id: int,
    body: TherapistScheduleUpdate,
    request: Request,
    user: dict = Depends(require_role("store", "therapist", "platform", "xingyao")),
    scope: int | None = Depends(store_scope),
    db: AsyncSession = Depends(get_db),
):
    await _load_therapist(db, therapist_id, scope)
    sch = await db.get(MtTherapistSchedule, schedule_id)
    if not sch or sch.is_deleted or sch.therapist_id != therapist_id:
        raise BusinessError(ErrorCode.NOT_FOUND, "排班不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(sch, k, v)
    await db.commit()
    await db.refresh(sch)
    await write_audit(
        db,
        action="therapist_schedule.update",
        resource="mt_therapist_schedule",
        role=user.get("role"),
        actor_id=actor_of(user),
        after=TherapistScheduleOut.model_validate(sch).model_dump(mode="json"),
        ip=request.client.host if request.client else None,
    )
    return success(data=TherapistScheduleOut.model_validate(sch))


@schedule_router.delete("/{therapist_id}/schedules/{schedule_id}", response_model=None)
async def delete_therapist_schedule(
    therapist_id: int,
    schedule_id: int,
    request: Request,
    user: dict = Depends(require_role("store", "therapist", "platform", "xingyao")),
    scope: int | None = Depends(store_scope),
    db: AsyncSession = Depends(get_db),
):
    await _load_therapist(db, therapist_id, scope)
    sch = await db.get(MtTherapistSchedule, schedule_id)
    if not sch or sch.is_deleted or sch.therapist_id != therapist_id:
        raise BusinessError(ErrorCode.NOT_FOUND, "排班不存在")
    sch.is_deleted = True
    await db.commit()
    await write_audit(
        db,
        action="therapist_schedule.delete",
        resource="mt_therapist_schedule",
        role=user.get("role"),
        actor_id=actor_of(user),
        ip=request.client.host if request.client else None,
    )
    return success(message="已删除")


# ===================== 调理师标签 =====================
@tag_router.get("", response_model=None)
async def list_tags(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    category: str | None = None,
    user: dict = Depends(require_role("store", "therapist", "platform", "xingyao")),
    db: AsyncSession = Depends(get_db),
):
    conds = [MtTherapistTag.is_deleted.is_(False)]
    if category:
        conds.append(MtTherapistTag.category == category)
    total = (await db.execute(select(func.count()).select_from(MtTherapistTag).where(*conds))).scalar() or 0
    rows = (
        await db.execute(
            select(MtTherapistTag)
            .where(*conds)
            .order_by(MtTherapistTag.id)
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    ).scalars().all()
    return success(
        data=PageResult[TherapistTagOut](
            total=total, page=page, page_size=page_size, items=[TherapistTagOut.model_validate(r) for r in rows]
        )
    )


@tag_router.post("", response_model=None)
async def create_tag(
    body: TherapistTagCreate,
    request: Request,
    user: dict = Depends(require_role("platform", "xingyao")),
    db: AsyncSession = Depends(get_db),
):
    # 复用 TherapistTagOut 作为入参（id/created_at 由服务端生成）
    tag = MtTherapistTag(name=body.name, category=body.category, description=body.description)
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    await write_audit(
        db,
        action="therapist_tag.create",
        resource="mt_therapist_tag",

        role=user.get("role"),
        actor_id=actor_of(user),
        after={"id": tag.id, "name": tag.name},
        ip=request.client.host if request.client else None,
    )
    return success(data=TherapistTagOut.model_validate(tag))


@schedule_router.get("/{therapist_id}/tags", response_model=None)
async def list_therapist_tags(
    therapist_id: int,
    user: dict = Depends(require_role("store", "therapist", "platform", "xingyao")),
    scope: int | None = Depends(store_scope),
    db: AsyncSession = Depends(get_db),
):
    await _load_therapist(db, therapist_id, scope)
    rows = (
        await db.execute(
            select(MtTherapistTagRel, MtTherapistTag)
            .join(MtTherapistTag, MtTherapistTag.id == MtTherapistTagRel.tag_id)
            .where(MtTherapistTagRel.therapist_id == therapist_id, MtTherapistTagRel.is_deleted.is_(False))
        )
    ).all()
    items = [
        {
            "therapist_id": rel.therapist_id,
            "tag_id": rel.tag_id,
            "tag_name": tag.name,
            "category": tag.category,
            "assigned_by": rel.assigned_by,
            "created_at": rel.created_at,
        }
        for rel, tag in rows
    ]
    return success(data=items)


@schedule_router.post("/{therapist_id}/tags", response_model=None)
async def assign_therapist_tag(
    therapist_id: int,
    body: _TagAssignIn,
    request: Request,
    user: dict = Depends(require_role("store", "therapist", "platform", "xingyao")),
    scope: int | None = Depends(store_scope),
    db: AsyncSession = Depends(get_db),
):
    await _load_therapist(db, therapist_id, scope)
    tag = await db.get(MtTherapistTag, body.tag_id)
    if not tag or tag.is_deleted:
        raise BusinessError(ErrorCode.NOT_FOUND, "标签不存在")
    exists = (
        await db.execute(
            select(MtTherapistTagRel).where(
                MtTherapistTagRel.therapist_id == therapist_id,
                MtTherapistTagRel.tag_id == body.tag_id,
                MtTherapistTagRel.is_deleted.is_(False),
            )
        )
    ).scalars().first()
    if exists:
        return success(message="已分配", data={"therapist_id": therapist_id, "tag_id": body.tag_id})
    rel = MtTherapistTagRel(therapist_id=therapist_id, tag_id=body.tag_id, assigned_by=actor_of(user))
    db.add(rel)
    await db.commit()
    await write_audit(
        db,
        action="therapist_tag.assign",
        resource="mt_therapist_tag_rel",
        role=user.get("role"),
        actor_id=actor_of(user),
        after={"therapist_id": therapist_id, "tag_id": body.tag_id},
        ip=request.client.host if request.client else None,
    )
    return success(message="已分配", data={"therapist_id": therapist_id, "tag_id": body.tag_id})


@schedule_router.delete("/{therapist_id}/tags/{tag_id}", response_model=None)
async def unassign_therapist_tag(
    therapist_id: int,
    tag_id: int,
    request: Request,
    user: dict = Depends(require_role("store", "therapist", "platform", "xingyao")),
    scope: int | None = Depends(store_scope),
    db: AsyncSession = Depends(get_db),
):
    await _load_therapist(db, therapist_id, scope)
    rel = (
        await db.execute(
            select(MtTherapistTagRel).where(
                MtTherapistTagRel.therapist_id == therapist_id,
                MtTherapistTagRel.tag_id == tag_id,
                MtTherapistTagRel.is_deleted.is_(False),
            )
        )
    ).scalars().first()
    if not rel:
        raise BusinessError(ErrorCode.NOT_FOUND, "未分配该标签")
    rel.is_deleted = True
    await db.commit()
    await write_audit(
        db,
        action="therapist_tag.unassign",
        resource="mt_therapist_tag_rel",
        role=user.get("role"),
        actor_id=actor_of(user),
        after={"therapist_id": therapist_id, "tag_id": tag_id},
        ip=request.client.host if request.client else None,
    )
    return success(message="已移除")
