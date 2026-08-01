"""互联网医院：投诉与售后（PRD 3.3.4，患者权益闭环）。

- 列表按 状态/类型 筛选，分页。
- 处理回复（状态流转 + 回复内容）由 platform 角色执行；投诉含用户 PII，列表仅返回脱敏 user_id。
"""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import actor_of, get_db, require_role
from app.core.errors import BusinessError, ErrorCode
from app.core.response import success
from app.models.ih_models import IhComplaint
from app.schemas.common import PageResult
from app.schemas.ih import ComplaintCreate, ComplaintOut, ComplaintReply
from app.services.audit import write_audit

router = APIRouter(prefix="/complaints", tags=["ih-投诉售后"])

_VALID_STATUS = {"pending", "processing", "resolved", "closed"}


@router.get("", response_model=None)
async def list_complaints(
    status: str | None = None,
    type: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    conds = [IhComplaint.is_deleted.is_(False)]
    if status:
        conds.append(IhComplaint.status == status)
    if type:
        conds.append(IhComplaint.type == type)
    total = (await db.execute(select(func.count()).select_from(IhComplaint).where(*conds))).scalar() or 0
    rows = (
        await db.execute(
            select(IhComplaint).where(*conds).order_by(IhComplaint.id.desc()).limit(page_size).offset((page - 1) * page_size)
        )
    ).scalars().all()
    return success(
        data=PageResult[ComplaintOut](
            total=total, page=page, page_size=page_size, items=[ComplaintOut.model_validate(r) for r in rows]
        )
    )


@router.get("/{complaint_id}", response_model=None)
async def get_complaint(complaint_id: int, db: AsyncSession = Depends(get_db)):
    c = await db.get(IhComplaint, complaint_id)
    if not c or c.is_deleted:
        raise BusinessError(ErrorCode.NOT_FOUND, "投诉不存在")
    return success(data=ComplaintOut.model_validate(c))


@router.post("", response_model=None)
async def create_complaint(
    body: ComplaintCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    # 投诉可由患者/客服发起，不强制角色；记录审计（操作者可为空）
    c = IhComplaint(**body.model_dump())
    db.add(c)
    await db.commit()
    await db.refresh(c)
    await write_audit(
        db,
        action="complaint.create",
        resource="ih_complaint",
        actor_id=None,
        after=ComplaintOut.model_validate(c).model_dump(mode="json"),
        ip=request.client.host if request.client else None,
    )
    return success(data=ComplaintOut.model_validate(c))


@router.patch("/{complaint_id}", response_model=None)
async def handle_complaint(
    complaint_id: int,
    body: ComplaintReply,
    request: Request,
    user: dict = Depends(require_role("platform")),
    db: AsyncSession = Depends(get_db),
):
    c = await db.get(IhComplaint, complaint_id)
    if not c or c.is_deleted:
        raise BusinessError(ErrorCode.NOT_FOUND, "投诉不存在")
    if body.status not in _VALID_STATUS:
        raise BusinessError(ErrorCode.BAD_REQUEST, "无效状态")
    c.status = body.status
    if body.reply is not None:
        c.reply = body.reply
    await db.commit()
    await db.refresh(c)
    await write_audit(
        db,
        action="complaint.handle",
        resource="ih_complaint",
        role=user.get("role"),
        actor_id=actor_of(user),
        after=ComplaintOut.model_validate(c).model_dump(mode="json"),
        ip=request.client.host if request.client else None,
    )
    return success(data=ComplaintOut.model_validate(c))
