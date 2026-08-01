"""在线复诊会话与消息（技术架构第11.2章 / PRD 3.1.3-3.1.4）。

MVP 闭环：患者支付复诊/咨询费 → 创建会话 → 医师接诊 → 图文沟通 → 开方 → 结束。
状态机：open（待接诊）→ ongoing（问诊中）→ ended（已结束）。
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, current_user, actor_of
from app.core.errors import BusinessError, ErrorCode
from app.core.response import success
from app.models.ih_models import (
    IhConsultation,
    IhConsultationMessage,
    IhDoctor,
    IhOrder,
    IhUser,
)
from app.schemas.common import PageResult
from app.schemas.ih import (
    ConsultationCreate,
    ConsultationMessageCreate,
    ConsultationMessageOut,
    ConsultationOut,
)
from app.services.audit import write_audit
from app.utils.idgen import gen_no

router = APIRouter(prefix="/consultations", tags=["ih-在线复诊"])


async def _get_consultation(consultation_id: int, db: AsyncSession) -> IhConsultation:
    obj = await db.get(IhConsultation, consultation_id)
    if not obj or obj.is_deleted:
        raise BusinessError(ErrorCode.RESOURCE_NOT_FOUND, "问诊会话不存在")
    return obj


async def _assert_exists(model, pk, db: AsyncSession) -> None:
    obj = await db.get(model, pk)
    if not obj or getattr(obj, "is_deleted", False):
        raise BusinessError(ErrorCode.RESOURCE_NOT_FOUND, f"{model.__name__} 不存在")


@router.post("", response_model=None)
async def create_consultation(
    body: ConsultationCreate, request: Request, _user: dict = Depends(current_user), db: AsyncSession = Depends(get_db)
):
    await _assert_exists(IhUser, body.patient_id, db)
    await _assert_exists(IhDoctor, body.doctor_id, db)
    if body.order_id is not None:
        await _assert_exists(IhOrder, body.order_id, db)

    no = gen_no("CON")
    obj = IhConsultation(
        consultation_no=no,
        patient_id=body.patient_id,
        doctor_id=body.doctor_id,
        order_id=body.order_id,
        chief_complaint=body.chief_complaint,
        status="open",
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    await write_audit(
        db,
        action="consultation.create",
        resource="ih_consultation",
        role=_user.get("role"),
        actor_id=actor_of(_user),
        after={"consultation_no": no, "doctor_id": body.doctor_id},
        ip=request.client.host if request.client else None,
    )
    return success(data=ConsultationOut.model_validate(obj))


@router.get("", response_model=None)
async def list_consultations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    patient_id: int | None = None,
    doctor_id: int | None = None,
    status: str | None = None,
    _auth: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    conds = [IhConsultation.is_deleted.is_(False)]
    # S3 越权修复：role=patient/doctor 时强制归属，忽略外部传入的越权 id
    role = _auth.get("role")
    if role == "patient":
        conds.append(IhConsultation.patient_id == actor_of(_auth))
    elif role == "doctor":
        conds.append(IhConsultation.doctor_id == actor_of(_auth))
    else:
        if patient_id is not None:
            conds.append(IhConsultation.patient_id == patient_id)
        if doctor_id is not None:
            conds.append(IhConsultation.doctor_id == doctor_id)
    if status is not None:
        conds.append(IhConsultation.status == status)
    total = (
        await db.scalar(select(func.count()).select_from(IhConsultation).where(*conds))
        or 0
    )
    rows = (
        await db.execute(
            select(IhConsultation)
            .where(*conds)
            .order_by(IhConsultation.id.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    ).scalars().all()
    return success(
        data=PageResult(
            total=total,
            page=page,
            page_size=page_size,
            items=[ConsultationOut.model_validate(r) for r in rows],
        )
    )


@router.get("/{consultation_id}", response_model=None)
async def get_consultation(consultation_id: int, _auth: dict = Depends(current_user), db: AsyncSession = Depends(get_db)):
    obj = await _get_consultation(consultation_id, db)
    # S3 越权修复：按登录角色归属校验（患者仅本人、医师仅本人、platform 全量）
    role = _auth.get("role")
    if role == "patient" and obj.patient_id != actor_of(_auth):
        raise BusinessError(ErrorCode.FORBIDDEN, "非本人问诊会话")
    if role == "doctor" and obj.doctor_id != actor_of(_auth):
        raise BusinessError(ErrorCode.FORBIDDEN, "非本人问诊会话")
    return success(data=ConsultationOut.model_validate(obj))


@router.patch("/{consultation_id}/start", response_model=None)
async def start_consultation(
    consultation_id: int, doctor_id: int, request: Request,
    _user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    obj = await _get_consultation(consultation_id, db)
    if obj.status != "open":
        raise BusinessError(ErrorCode.PARAM_INVALID, "会话状态不允许接诊")
    obj.status = "ongoing"
    obj.started_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(obj)
    await write_audit(
        db,
        action="consultation.start",
        resource="ih_consultation",
        role=_user.get("role"),
        actor_id=actor_of(_user),
        after={"consultation_no": obj.consultation_no, "status": "ongoing"},
        ip=request.client.host if request.client else None,
    )
    return success(data=ConsultationOut.model_validate(obj))


@router.patch("/{consultation_id}/end", response_model=None)
async def end_consultation(
    consultation_id: int,
    request: Request,
    _auth: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    obj = await _get_consultation(consultation_id, db)
    if obj.status != "ongoing":
        raise BusinessError(ErrorCode.PARAM_INVALID, "仅问诊中会话可结束")
    # 归属校验：主体取自 JWT，不信任前端传入的 id（杜绝不传参绕过）。
    # 与 get_consultation 越权逻辑保持一致：患者/医师仅能结束本人会话，platform 全量。
    role = _auth.get("role")
    if role == "patient" and obj.patient_id != actor_of(_auth):
        raise BusinessError(ErrorCode.FORBIDDEN, "非本人会话，无法结束")
    if role == "doctor" and obj.doctor_id != actor_of(_auth):
        raise BusinessError(ErrorCode.FORBIDDEN, "非本人会话，无法结束")
    if role not in ("patient", "doctor", "platform"):
        raise BusinessError(ErrorCode.FORBIDDEN, "无权限结束会话")
    obj.status = "ended"
    obj.ended_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(obj)
    await write_audit(
        db,
        action="consultation.end",
        resource="ih_consultation",
        role=_auth.get("role"),
        actor_id=actor_of(_auth),
        after={"consultation_no": obj.consultation_no, "status": "ended"},
        ip=request.client.host if request.client else None,
    )
    return success(data=ConsultationOut.model_validate(obj))


@router.post("/{consultation_id}/messages", response_model=None)
async def send_message(
    consultation_id: int,
    body: ConsultationMessageCreate,
    request: Request,
    _user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    obj = await _get_consultation(consultation_id, db)
    if obj.status == "ended":
        raise BusinessError(ErrorCode.PARAM_INVALID, "会话已结束，无法发送消息")
    if body.msg_type not in ("text", "image", "voice"):
        raise BusinessError(ErrorCode.PARAM_INVALID, "msg_type 非法")
    if body.sender_role not in ("patient", "doctor", "platform"):
        raise BusinessError(ErrorCode.PARAM_INVALID, "sender_role 非法")

    msg = IhConsultationMessage(
        consultation_id=obj.id,
        sender_role=body.sender_role,
        sender_id=body.sender_id,
        msg_type=body.msg_type,
        content=body.content,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    await write_audit(
        db,
        action="consultation.message",
        resource="ih_consultation_message",
        role=_user.get("role"),
        actor_id=actor_of(_user),
        after={"consultation_no": obj.consultation_no, "msg_type": body.msg_type},
        ip=request.client.host if request.client else None,
    )
    return success(data=ConsultationMessageOut.model_validate(msg))


@router.get("/{consultation_id}/messages", response_model=None)
async def list_messages(
    consultation_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    _auth: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    obj = await _get_consultation(consultation_id, db)
    conds = [
        IhConsultationMessage.consultation_id == obj.id,
        IhConsultationMessage.is_deleted.is_(False),
    ]
    total = (
        await db.scalar(
            select(func.count()).select_from(IhConsultationMessage).where(*conds)
        )
        or 0
    )
    rows = (
        await db.execute(
            select(IhConsultationMessage)
            .where(*conds)
            .order_by(IhConsultationMessage.id.asc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    ).scalars().all()
    return success(
        data=PageResult(
            total=total,
            page=page,
            page_size=page_size,
            items=[ConsultationMessageOut.model_validate(r) for r in rows],
        )
    )
