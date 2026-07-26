"""平台：合规采集与审核（P6，等保三级 / 执业资质 / 隐私合规）。

- 任意已登录角色均可提交合规采集工单（submit）。
- platform / xingyao 执行审核（approve / reject），全程审计留痕。
- 非审核角色仅可见本人提交或主体为自身的工单。
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import actor_of, current_user, get_db, require_role
from app.core.errors import BusinessError, ErrorCode
from app.core.response import success
from app.models.plat_models import PlatComplianceItem
from app.schemas.common import PageResult
from app.schemas.plat import ComplianceOut, ComplianceReviewIn, ComplianceSubmitIn
from app.services.audit import write_audit

router = APIRouter(prefix="/compliance", tags=["plat-合规采集审核"])

_REVIEWER_ROLES = ("platform", "xingyao")


@router.post("/submit", response_model=None)
async def submit_compliance(
    body: ComplianceSubmitIn,
    request: Request,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    item = PlatComplianceItem(
        category=body.category,
        subject_type=body.subject_type,
        subject_id=body.subject_id,
        title=body.title,
        content_json=body.content_json,
        submitter_id=actor_of(user),
        status="pending",
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    await write_audit(
        db,
        action="compliance.submit",
        resource="plat_compliance_item",
        role=user.get("role"),
        actor_id=actor_of(user),
        after=ComplianceOut.model_validate(item).model_dump(mode="json"),
        ip=request.client.host if request.client else None,
    )
    return success(data=ComplianceOut.model_validate(item))


@router.get("", response_model=None)
async def list_compliance(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    category: str | None = None,
    status: str | None = None,
    subject_type: str | None = None,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    conds = [PlatComplianceItem.is_deleted.is_(False)]
    if user.get("role") not in _REVIEWER_ROLES:
        actor = actor_of(user)
        conds.append(
            or_(
                PlatComplianceItem.submitter_id == actor,
                PlatComplianceItem.subject_id == actor,
            )
        )
    if category:
        conds.append(PlatComplianceItem.category == category)
    if status:
        conds.append(PlatComplianceItem.status == status)
    if subject_type:
        conds.append(PlatComplianceItem.subject_type == subject_type)
    total = (await db.execute(select(func.count()).select_from(PlatComplianceItem).where(*conds))).scalar() or 0
    rows = (
        await db.execute(
            select(PlatComplianceItem)
            .where(*conds)
            .order_by(PlatComplianceItem.id.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    ).scalars().all()
    return success(
        data=PageResult[ComplianceOut](
            total=total, page=page, page_size=page_size, items=[ComplianceOut.model_validate(r) for r in rows]
        )
    )


@router.get("/{item_id}", response_model=None)
async def get_compliance(item_id: int, user: dict = Depends(current_user), db: AsyncSession = Depends(get_db)):
    item = await db.get(PlatComplianceItem, item_id)
    if not item or item.is_deleted:
        raise BusinessError(ErrorCode.NOT_FOUND, "合规工单不存在")
    if user.get("role") not in _REVIEWER_ROLES:
        actor = actor_of(user)
        if item.submitter_id != actor and item.subject_id != actor:
            raise BusinessError(ErrorCode.FORBIDDEN, "无权查看该工单")
    return success(data=ComplianceOut.model_validate(item))


async def _review(item_id: int, body: ComplianceReviewIn, approve: bool, user: dict, request: Request, db: AsyncSession):
    if user.get("role") not in _REVIEWER_ROLES:
        raise BusinessError(ErrorCode.FORBIDDEN, "仅平台/星耀可审核")
    item = await db.get(PlatComplianceItem, item_id)
    if not item or item.is_deleted:
        raise BusinessError(ErrorCode.NOT_FOUND, "合规工单不存在")
    if not approve and not body.review_note:
        raise BusinessError(ErrorCode.BAD_REQUEST, "驳回需填写审核意见")
    before = ComplianceOut.model_validate(item).model_dump(mode="json")
    item.status = "approved" if approve else "rejected"
    item.reviewer_id = actor_of(user)
    item.review_note = body.review_note
    item.reviewed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(item)
    await write_audit(
        db,
        action="compliance.approve" if approve else "compliance.reject",
        resource="plat_compliance_item",

        role=user.get("role"),
        actor_id=actor_of(user),
        before=before,
        after=ComplianceOut.model_validate(item).model_dump(mode="json"),
        ip=request.client.host if request.client else None,
    )
    return success(data=ComplianceOut.model_validate(item))


@router.post("/{item_id}/approve", response_model=None)
async def approve_compliance(
    item_id: int,
    body: ComplianceReviewIn,
    request: Request,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _review(item_id, body, approve=True, user=user, request=request, db=db)


@router.post("/{item_id}/reject", response_model=None)
async def reject_compliance(
    item_id: int,
    body: ComplianceReviewIn,
    request: Request,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _review(item_id, body, approve=False, user=user, request=request, db=db)
