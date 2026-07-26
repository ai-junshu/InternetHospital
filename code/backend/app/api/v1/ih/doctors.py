"""互联网医院医师管理（技术架构第11.2章）。"""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError, ErrorCode
from app.core.response import success
from app.core.deps import get_db, current_user, actor_of
from app.models.ih_models import IhDoctor
from app.schemas.common import PageResult
from app.schemas.ih import DoctorCreate, DoctorOut
from app.services.audit import write_audit

router = APIRouter(prefix="/doctors", tags=["ih-医师"])


@router.post("", response_model=None)
async def create_doctor(
    body: DoctorCreate, request: Request, _user: dict = Depends(current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(IhDoctor).where(IhDoctor.license_no == body.license_no)
    )
    if result.scalar_one_or_none():
        raise BusinessError(ErrorCode.PARAM_INVALID, "执业证书编号已存在")
    doc = IhDoctor(**body.model_dump())
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    await write_audit(
        db,
        action="doctor.create",
        resource="ih_doctor",
        role=_user.get("role"),
        actor_id=actor_of(_user),
        after=DoctorOut.model_validate(doc).model_dump(mode="json"),
        ip=request.client.host if request.client else None,
    )
    return success(data=DoctorOut.model_validate(doc))


@router.get("", response_model=None)
async def list_doctors(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    _auth: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    conds = [IhDoctor.is_deleted.is_(False)]
    if status:
        conds.append(IhDoctor.status == status)
    total = await db.scalar(select(func.count()).select_from(IhDoctor).where(*conds)) or 0
    rows = (
        await db.execute(
            select(IhDoctor)
            .where(*conds)
            .order_by(IhDoctor.id.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    ).scalars().all()
    return success(
        data=PageResult(
            total=total,
            page=page,
            page_size=page_size,
            items=[DoctorOut.model_validate(r) for r in rows],
        )
    )


@router.get("/{doctor_id}", response_model=None)
async def get_doctor(doctor_id: int, _auth: dict = Depends(current_user), db: AsyncSession = Depends(get_db)):
    doc = await db.get(IhDoctor, doctor_id)
    if not doc or doc.is_deleted:
        raise BusinessError(ErrorCode.RESOURCE_NOT_FOUND, "医师不存在")
    return success(data=DoctorOut.model_validate(doc))
