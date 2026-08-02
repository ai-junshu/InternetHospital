"""健康数据中台：调理方案（调用 ai-service plan-recommend，第11.2/12章）。"""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError, ErrorCode
from app.core.response import success
from app.core.deps import get_db, require_role, actor_of, store_scope, customer_ids_for_store
from app.models.mt_models import MtCarePlan
from app.schemas.common import PageResult
from app.schemas.mt import CarePlanCreate, CarePlanOut
from app.services.ai_client import recommend_plan
from app.services.audit import write_audit
from app.services.pred_log import create_pred_log

router = APIRouter(prefix="/care-plans", tags=["mt-调理方案"])


@router.post("", response_model=None)
async def create_care_plan(
    body: CarePlanCreate, request: Request, _user: dict = Depends(require_role("store", "therapist", "platform", "xingyao")), db: AsyncSession = Depends(get_db)
):
    # 合规强规则1：方案必须关联执业医师出具的方案建议/处方 ID（doctor_advice_id>0），
    # 禁止以 0 等无效值冒充医师建议（等保三级留痕合规）。
    if not body.doctor_advice_id or body.doctor_advice_id <= 0:
        raise BusinessError(
            ErrorCode.PARAM_INVALID,
            "照护计划必须关联执业医师出具的方案建议/处方（doctor_advice_id 无效）",
        )
    rec = await recommend_plan(
        body.customer_id, body.age or 0, body.pain_score or 0, body.chronic_count or 0, body.pain_type
    )
    items_json = rec.get("care_plan_json") if rec else None
    # RAG 可解释依据随方案一并落库（第10.3章），并入 items_json 透传，免迁移
    if rec and rec.get("rationale"):
        items_json = dict(items_json or {})
        items_json["rationale"] = rec["rationale"]
    product_combo_json = rec.get("product_combo_json") if rec else None
    # 合规强规则1：方案必须关联执业医师出具的方案建议/处方 ID，
    # 禁止以创建人(调理师自身)冒充医师建议（原 doctor_advice_id=created_by 为语义错位）。
    plan = MtCarePlan(
        customer_id=body.customer_id,
        doctor_advice_id=body.doctor_advice_id,
        pain_type=body.pain_type,
        goal=body.goal,
        cycle=body.cycle,
        items_json=items_json,
        product_combo_json=product_combo_json,
        status="active",
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    await write_audit(
        db,
        action="care_plan.create",
        resource="mt_care_plan",
        role=_user.get("role"),
        actor_id=actor_of(_user),
        after=CarePlanOut.model_validate(plan).model_dump(mode="json"),
        ip=request.client.host if request.client else None,
    )
    # AI 反馈闭环：落预测日志（adopted=pending），独立事务降级不阻断
    await create_pred_log(
        model_id=None,
        version=rec.get("model_version") if rec else None,
        customer_id=body.customer_id,
        input_json={"age": body.age, "pain_score": body.pain_score, "chronic_count": body.chronic_count, "pain_type": body.pain_type},
        predict_json=items_json,
        user_id=actor_of(_user),
    )
    return success(data=CarePlanOut.model_validate(plan))


@router.get("", response_model=None)
async def list_care_plans(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: int | None = None,
    scope: int | None = Depends(store_scope),
    _auth: dict = Depends(require_role("store", "therapist", "platform", "xingyao")),
    db: AsyncSession = Depends(get_db),
):
    conds = [MtCarePlan.is_deleted.is_(False)]
    if customer_id is not None:
        conds.append(MtCarePlan.customer_id == customer_id)
    if scope is not None:
        conds.append(MtCarePlan.customer_id.in_(customer_ids_for_store(scope)))
    total = (
        await db.scalar(select(func.count()).select_from(MtCarePlan).where(*conds)) or 0
    )
    rows = (
        await db.execute(
            select(MtCarePlan)
            .where(*conds)
            .order_by(MtCarePlan.id.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    ).scalars().all()
    return success(
        data=PageResult(
            total=total,
            page=page,
            page_size=page_size,
            items=[CarePlanOut.model_validate(r) for r in rows],
        )
    )
