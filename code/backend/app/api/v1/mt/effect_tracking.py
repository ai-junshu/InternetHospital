"""治疗效果四档判定路由（合规强规则3，PRD V2.0 L267-270）。

根据客户在方案周期内的疼痛评分变化、NPS 满意度与复购行为，调用 effect_service
自动判定显效/有效/无效/恶化，并落库 mt_effect_tracking，触发后续动作
（无效→推荐升级方案/建议就医）。纯判定逻辑见 services/effect_service.py。
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import actor_of, get_db, require_role, store_scope
from app.core.response import success
from app.models.mt_models import MtEffectTracking
from app.schemas.common import PageResult
from app.schemas.mt import *
from app.services.audit import write_audit
from app.services.effect_service import build_effect_tracking

router = APIRouter(prefix="/effect-tracking", tags=["mt-effect-tracking"])


@router.post("", response_model=None)
async def create_effect_tracking(
    body: EffectTrackingCreate,
    request: Request,
    _user: dict = Depends(require_role("store", "therapist", "platform", "xingyao")),
    scope: int | None = Depends(store_scope),
    db: AsyncSession = Depends(get_db),
):
    # 调用判定服务生成字段（不直接提交，整合进本事务）
    fields = await build_effect_tracking(
        db,
        customer_id=body.customer_id,
        plan_id=body.plan_id,
        baseline_pain=body.baseline_pain,
        latest_pain=body.latest_pain,
        nps=body.nps,
        repurchase_count=body.repurchase_count,
    )
    obj = MtEffectTracking(
        customer_id=fields["customer_id"],
        plan_id=fields["plan_id"],
        effect_level=fields["effect_level"],
        assess_seq_json=fields["assess_seq_json"],
        generated_at=fields["generated_at"],
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    await write_audit(
        db,
        action="effect_tracking.create",
        resource="mt_effect_tracking",
        role=_user.get("role"),
        actor_id=actor_of(_user),
        after={"customer_id": obj.customer_id, "effect_level": obj.effect_level},
        ip=request.client.host if request.client else None,
    )
    # 触发后续动作（无效/恶化 → 升级方案或建议就医）
    action = None
    if obj.effect_level in ("ineffective", "worsened"):
        action = "recommend_upgrade_or_consult"  # 业务层据此推送升级方案/就医建议
    return success(
        data={
            "id": obj.id,
            "customer_id": obj.customer_id,
            "effect_level": obj.effect_level,
            "next_action": action,
        }
    )


@router.get("", response_model=None)
async def list_effect_tracking(
    customer_id: Optional[int] = None,
    plan_id: Optional[int] = None,
    effect_level: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    _user: dict = Depends(require_role("store", "therapist", "platform", "xingyao")),
    scope: int | None = Depends(store_scope),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(MtEffectTracking)
    if customer_id is not None:
        stmt = stmt.where(MtEffectTracking.customer_id == customer_id)
    if plan_id is not None:
        stmt = stmt.where(MtEffectTracking.plan_id == plan_id)
    if effect_level is not None:
        stmt = stmt.where(MtEffectTracking.effect_level == effect_level)
    total_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(total_stmt)).scalar() or 0
    stmt = stmt.order_by(MtEffectTracking.id.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()
    return success(
        data=PageResult(
            total=total,
            page=page,
            page_size=page_size,
            items=[EffectTrackingOut.model_validate(r) for r in rows],
        )
    )
