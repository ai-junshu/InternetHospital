"""健康数据中台：疼痛评估录入（技术架构第11.2章）。"""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError, ErrorCode
from app.core.response import success
from app.core.deps import get_db, require_role, actor_of, store_scope, customer_ids_for_store
from app.models.mt_models import MtPainAssessment
from app.schemas.common import PageResult
from app.schemas.mt import PainAssessmentCreate, PainAssessmentOut
from app.services.audit import write_audit

router = APIRouter(prefix="/pain-assessments", tags=["mt-疼痛评估"])


@router.post("", response_model=None)
async def create_pain_assessment(
    body: PainAssessmentCreate, request: Request, _user: dict = Depends(require_role("store", "therapist", "platform", "xingyao")), db: AsyncSession = Depends(get_db)
):
    pa = MtPainAssessment(**body.model_dump())
    db.add(pa)
    await db.commit()
    await db.refresh(pa)
    await write_audit(
        db,
        action="pain_assessment.create",
        resource="mt_pain_assessment",
        role=_user.get("role"),
        actor_id=actor_of(_user),
        after=PainAssessmentOut.model_validate(pa).model_dump(mode="json"),
        ip=request.client.host if request.client else None,
    )
    return success(data=PainAssessmentOut.model_validate(pa))


@router.get("", response_model=None)
async def list_pain_assessments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: int | None = None,
    scope: int | None = Depends(store_scope),
    _auth: dict = Depends(require_role("store", "therapist", "platform", "xingyao")),
    db: AsyncSession = Depends(get_db),
):
    conds = [MtPainAssessment.is_deleted.is_(False)]
    if customer_id is not None:
        conds.append(MtPainAssessment.customer_id == customer_id)
    if scope is not None:
        conds.append(MtPainAssessment.customer_id.in_(customer_ids_for_store(scope)))
    total = (
        await db.scalar(
            select(func.count()).select_from(MtPainAssessment).where(*conds)
        )
        or 0
    )
    rows = (
        await db.execute(
            select(MtPainAssessment)
            .where(*conds)
            .order_by(MtPainAssessment.id.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    ).scalars().all()
    return success(
        data=PageResult(
            total=total,
            page=page,
            page_size=page_size,
            items=[PainAssessmentOut.model_validate(r) for r in rows],
        )
    )
