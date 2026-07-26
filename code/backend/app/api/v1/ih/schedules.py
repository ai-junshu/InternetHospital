"""互联网医院：医生排班（技术架构 11.2 / PRD 3.1.4）。

- 医生角色仅能管理自己的排班；platform 可管理全部。
- 所有写操作均走审计留痕（write_audit）。
"""
from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import actor_of, get_db, require_role
from app.core.errors import BusinessError, ErrorCode
from app.core.response import success
from app.models.ih_models import IhDoctor, IhDoctorSchedule
from app.schemas.common import PageResult
from app.schemas.ih import DoctorScheduleCreate, DoctorScheduleOut, DoctorScheduleUpdate
from app.services.audit import write_audit

router = APIRouter(prefix="/schedules", tags=["ih-医生排班"])


async def _resolve_doctor_id(db: AsyncSession, payload: dict) -> int | None:
    """doctor 角色通过 JWT sub(ih_user.id) 解析其 ih_doctor.id。"""
    sub = payload.get("sub")
    if sub is None:
        return None
    try:
        uid = int(sub)
    except (TypeError, ValueError):
        return None
    doc = (await db.execute(select(IhDoctor).where(IhDoctor.user_id == uid))).scalars().first()
    return doc.id if doc else None


@router.post("", response_model=None)
async def create_schedule(
    body: DoctorScheduleCreate,
    request: Request,
    user: dict = Depends(require_role("doctor", "platform")),
    db: AsyncSession = Depends(get_db),
):
    doctor_id = body.doctor_id
    if user.get("role") == "doctor":
        mine = await _resolve_doctor_id(db, user)
        if mine is None:
            raise BusinessError(ErrorCode.FORBIDDEN, "当前账号未关联医生档案")
        if body.doctor_id and body.doctor_id != mine:
            raise BusinessError(ErrorCode.FORBIDDEN, "不能给他人排班")
        doctor_id = mine
    sch = IhDoctorSchedule(doctor_id=doctor_id, **body.model_dump(exclude={"doctor_id"}))
    db.add(sch)
    await db.commit()
    await db.refresh(sch)
    await write_audit(
        db,
        action="doctor_schedule.create",
        resource="ih_doctor_schedule",

        role=user.get("role"),
        actor_id=actor_of(user),
        after=DoctorScheduleOut.model_validate(sch).model_dump(mode="json"),
        ip=request.client.host if request.client else None,
    )
    return success(data=DoctorScheduleOut.model_validate(sch))


@router.get("", response_model=None)
async def list_schedules(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    doctor_id: int | None = None,
    work_date: date | None = None,
    am_pm: str | None = None,
    status: str | None = None,
    user: dict = Depends(require_role("doctor", "platform")),
    db: AsyncSession = Depends(get_db),
):
    conds = [IhDoctorSchedule.is_deleted.is_(False)]
    if user.get("role") == "doctor":
        mine = await _resolve_doctor_id(db, user)
        conds.append(IhDoctorSchedule.doctor_id == (mine or -1))
    elif doctor_id:
        conds.append(IhDoctorSchedule.doctor_id == doctor_id)
    if work_date is not None:
        conds.append(IhDoctorSchedule.work_date == work_date)
    if am_pm:
        conds.append(IhDoctorSchedule.am_pm == am_pm)
    if status:
        conds.append(IhDoctorSchedule.status == status)
    total = (await db.execute(select(func.count()).select_from(IhDoctorSchedule).where(*conds))).scalar() or 0
    rows = (
        await db.execute(
            select(IhDoctorSchedule)
            .where(*conds)
            .order_by(IhDoctorSchedule.work_date, IhDoctorSchedule.start_time)
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    ).scalars().all()
    return success(
        data=PageResult[DoctorScheduleOut](
            total=total, page=page, page_size=page_size, items=[DoctorScheduleOut.model_validate(r) for r in rows]
        )
    )


@router.get("/{schedule_id}", response_model=None)
async def get_schedule(
    schedule_id: int,
    user: dict = Depends(require_role("doctor", "platform")),
    db: AsyncSession = Depends(get_db),
):
    sch = await db.get(IhDoctorSchedule, schedule_id)
    if not sch or sch.is_deleted:
        raise BusinessError(ErrorCode.NOT_FOUND, "排班不存在")
    return success(data=DoctorScheduleOut.model_validate(sch))


@router.patch("/{schedule_id}", response_model=None)
async def update_schedule(
    schedule_id: int,
    body: DoctorScheduleUpdate,
    request: Request,
    user: dict = Depends(require_role("doctor", "platform")),
    db: AsyncSession = Depends(get_db),
):
    sch = await db.get(IhDoctorSchedule, schedule_id)
    if not sch or sch.is_deleted:
        raise BusinessError(ErrorCode.NOT_FOUND, "排班不存在")
    if user.get("role") == "doctor":
        mine = await _resolve_doctor_id(db, user)
        if mine is None or sch.doctor_id != mine:
            raise BusinessError(ErrorCode.FORBIDDEN, "只能修改本人排班")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(sch, k, v)
    await db.commit()
    await db.refresh(sch)
    await write_audit(
        db,
        action="doctor_schedule.update",
        resource="ih_doctor_schedule",

        role=user.get("role"),
        actor_id=actor_of(user),
        after=DoctorScheduleOut.model_validate(sch).model_dump(mode="json"),
        ip=request.client.host if request.client else None,
    )
    return success(data=DoctorScheduleOut.model_validate(sch))


@router.delete("/{schedule_id}", response_model=None)
async def delete_schedule(
    schedule_id: int,
    request: Request,
    user: dict = Depends(require_role("doctor", "platform")),
    db: AsyncSession = Depends(get_db),
):
    sch = await db.get(IhDoctorSchedule, schedule_id)
    if not sch or sch.is_deleted:
        raise BusinessError(ErrorCode.NOT_FOUND, "排班不存在")
    if user.get("role") == "doctor":
        mine = await _resolve_doctor_id(db, user)
        if mine is None or sch.doctor_id != mine:
            raise BusinessError(ErrorCode.FORBIDDEN, "只能删除本人排班")
    sch.is_deleted = True
    await db.commit()
    await write_audit(
        db,
        action="doctor_schedule.delete",
        resource="ih_doctor_schedule",

        role=user.get("role"),
        actor_id=actor_of(user),
        ip=request.client.host if request.client else None,
    )
    return success(message="已删除")
