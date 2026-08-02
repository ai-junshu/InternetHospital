"""健康数据中台：复购/复诊预测回写（调用 ai-service repurchase-prediction，第15.4章）。"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import success
from app.core.deps import get_db, require_role, actor_of, store_scope, customer_ids_for_store
from app.models.mt_models import MtRepurchasePrediction
from app.schemas.common import PageResult
from app.schemas.mt import RepurchasePredictIn, RepurchasePredictionOut
from app.services.ai_client import repurchase_prediction
from app.services.audit import write_audit
from app.services.pred_log import create_pred_log

router = APIRouter(prefix="/repurchase-predictions", tags=["mt-复购预测"])


@router.post("", response_model=None)
async def predict_repurchase(
    body: RepurchasePredictIn, request: Request, _user: dict = Depends(require_role("store", "therapist", "platform", "xingyao")), db: AsyncSession = Depends(get_db)
):
    """调用 AI 复购预测，结果回写 mt_repurchase_prediction（AI 不可用则降级，仅落基础记录）。"""
    rec = await repurchase_prediction(
        body.customer_id, body.age, body.visit_freq, body.last_gap_days
    )
    record = MtRepurchasePrediction(
        customer_id=body.customer_id,
        predict_time=datetime.now(timezone.utc),
        next_visit_prob=rec.get("next_visit_prob") if rec else None,
        repurchase_prob=rec.get("repurchase_prob") if rec else None,
        risk_level=rec.get("risk_level") if rec else None,
        model_version=rec.get("model_version") if rec else None,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    await write_audit(
        db,
        action="repurchase_prediction.create",
        resource="mt_repurchase_prediction",
        role=_user.get("role"),
        actor_id=actor_of(_user),
        after=RepurchasePredictionOut.model_validate(record).model_dump(mode="json"),
        ip=request.client.host if request.client else None,
    )
    # AI 反馈闭环：落预测日志（adopted=pending）
    await create_pred_log(
        model_id=None,
        version=record.model_version,
        customer_id=body.customer_id,
        input_json={"age": body.age, "visit_freq": body.visit_freq, "last_gap_days": body.last_gap_days},
        predict_json=RepurchasePredictionOut.model_validate(record).model_dump(mode="json"),
        user_id=actor_of(_user),
    )
    return success(data=RepurchasePredictionOut.model_validate(record))


@router.get("", response_model=None)
async def list_repurchase_predictions(
    page: int = 1,
    page_size: int = 20,
    customer_id: int | None = None,
    scope: int | None = Depends(store_scope),
    _auth: dict = Depends(require_role("store", "therapist", "platform", "xingyao")),
    db: AsyncSession = Depends(get_db),
):
    conds = [MtRepurchasePrediction.is_deleted.is_(False)]
    if customer_id is not None:
        conds.append(MtRepurchasePrediction.customer_id == customer_id)
    if scope is not None:
        conds.append(MtRepurchasePrediction.customer_id.in_(customer_ids_for_store(scope)))
    total = (
        await db.scalar(
            select(func.count()).select_from(MtRepurchasePrediction).where(*conds)
        )
        or 0
    )
    rows = (
        await db.execute(
            select(MtRepurchasePrediction)
            .where(*conds)
            .order_by(MtRepurchasePrediction.id.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    ).scalars().all()
    return success(
        data=PageResult(
            total=total,
            page=page,
            page_size=page_size,
            items=[RepurchasePredictionOut.model_validate(r) for r in rows],
        )
    )
