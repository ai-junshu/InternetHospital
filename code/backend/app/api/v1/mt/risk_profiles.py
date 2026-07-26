"""健康数据中台：健康风险画像回写（调用 ai-service risk-profile，第15.4章）。"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import success
from app.core.deps import get_db, require_role, actor_of, store_scope, customer_ids_for_store
from app.models.mt_models import MtRiskProfile
from app.schemas.common import PageResult
from app.schemas.mt import RiskProfileIn, RiskProfileOut
from app.services.ai_client import risk_profile
from app.services.audit import write_audit

router = APIRouter(prefix="/risk-profiles", tags=["mt-风险画像"])


@router.post("", response_model=None)
async def predict_risk(
    body: RiskProfileIn, request: Request, _user: dict = Depends(require_role("store", "therapist", "platform", "xingyao")), db: AsyncSession = Depends(get_db)
):
    """调用 AI 风险画像，结果回写 mt_risk_profile（AI 不可用则降级，仅落基础记录）。"""
    rec = await risk_profile(
        body.customer_id, body.age, body.bmi, body.comorbidity_count
    )
    record = MtRiskProfile(
        customer_id=body.customer_id,
        predict_time=datetime.now(timezone.utc),
        pain_risk=rec.get("pain_risk") if rec else None,
        comorbidity_risk=rec.get("comorbidity_risk") if rec else None,
        model_version=rec.get("model_version") if rec else None,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    await write_audit(
        db,
        action="risk_profile.create",
        resource="mt_risk_profile",
        role=_user.get("role"),
        actor_id=actor_of(_user),
        after=RiskProfileOut.model_validate(record).model_dump(mode="json"),
        ip=request.client.host if request.client else None,
    )
    # AI 反馈闭环：落预测日志（adopted=pending）
    await create_pred_log(
        model_id=None,
        version=record.model_version,
        customer_id=body.customer_id,
        input_json={"age": body.age, "bmi": body.bmi, "comorbidity_count": body.comorbidity_count},
        predict_json=RiskProfileOut.model_validate(record).model_dump(mode="json"),
        user_id=actor_of(_user),
    )
    return success(data=RiskProfileOut.model_validate(record))


@router.get("", response_model=None)
async def list_risk_profiles(
    page: int = 1,
    page_size: int = 20,
    customer_id: int | None = None,
    _auth: dict = Depends(require_role("store", "therapist", "platform", "xingyao")),
    db: AsyncSession = Depends(get_db),
):
    conds = [MtRiskProfile.is_deleted.is_(False)]
    if customer_id is not None:
        conds.append(MtRiskProfile.customer_id == customer_id)
    total = (
        await db.scalar(
            select(func.count()).select_from(MtRiskProfile).where(*conds)
        )
        or 0
    )
    rows = (
        await db.execute(
            select(MtRiskProfile)
            .where(*conds)
            .order_by(MtRiskProfile.id.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    ).scalars().all()
    return success(
        data=PageResult(
            total=total,
            page=page,
            page_size=page_size,
            items=[RiskProfileOut.model_validate(r) for r in rows],
        )
    )
