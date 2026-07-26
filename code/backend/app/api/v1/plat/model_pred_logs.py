"""AI 预测日志接口（第15.4章 反馈闭环）。

- GET  /model-pred-logs          列表（平台/星耀）
- PATCH /model-pred-logs/{id}/adopt   采纳
- PATCH /model-pred-logs/{id}/reject  驳回
均注入 require_role(platform, xingyao)，并写审计留痕。
"""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_role, actor_of
from app.core.response import success
from app.schemas.common import PageResult
from app.schemas.plat import PredLogOut
from app.services.audit import write_audit
from app.services.pred_log import list_pred_logs, set_adopted

router = APIRouter(prefix="/model-pred-logs", tags=["plat-AI反馈闭环"])


@router.get("", response_model=None)
async def get_pred_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    model_id: int | None = None,
    customer_id: int | None = None,
    adopted: str | None = None,
    _auth: dict = Depends(require_role("platform", "xingyao")),
    db: AsyncSession = Depends(get_db),
):
    rows, total = await list_pred_logs(page, page_size, model_id, customer_id, adopted)
    return success(
        data=PageResult(
            total=total,
            page=page,
            page_size=page_size,
            items=[PredLogOut.model_validate(r) for r in rows],
        )
    )


@router.patch("/{log_id}/adopt", response_model=None)
async def adopt_log(
    log_id: int, request: Request, _user: dict = Depends(require_role("platform", "xingyao")), db: AsyncSession = Depends(get_db)
):
    log = await set_adopted(log_id, "adopted")
    if log is None:
        from app.core.errors import BusinessError, ErrorCode

        raise BusinessError(ErrorCode.NOT_FOUND, "预测日志不存在")
    await write_audit(
        db,
        action="model_pred_log.adopt",
        resource="plat_model_pred_log",
        role=_user.get("role"),
        actor_id=actor_of(_user),
        after=PredLogOut.model_validate(log).model_dump(mode="json"),
        ip=request.client.host if request.client else None,
    )
    return success(data=PredLogOut.model_validate(log))


@router.patch("/{log_id}/reject", response_model=None)
async def reject_log(
    log_id: int, request: Request, _user: dict = Depends(require_role("platform", "xingyao")), db: AsyncSession = Depends(get_db)
):
    log = await set_adopted(log_id, "rejected")
    if log is None:
        from app.core.errors import BusinessError, ErrorCode

        raise BusinessError(ErrorCode.NOT_FOUND, "预测日志不存在")
    await write_audit(
        db,
        action="model_pred_log.reject",
        resource="plat_model_pred_log",
        role=_user.get("role"),
        actor_id=actor_of(_user),
        after=PredLogOut.model_validate(log).model_dump(mode="json"),
        ip=request.client.host if request.client else None,
    )
    return success(data=PredLogOut.model_validate(log))
