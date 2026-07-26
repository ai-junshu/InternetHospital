"""审计日志查询接口（plat_audit_log，技术架构第10.2/13章，P4 哈希链校验）。

全量审计留痕，独立存储防篡改；仅平台 / 星耀角色可查（RBAC）。
提供 /verify 端点校验哈希链完整性，作为等保三级"审计记录防篡改"证据。
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_role
from app.core.response import success
from app.models.plat_models import PlatAuditLog
from app.schemas.common import PageResult
from app.schemas.plat import AuditLogOut
from app.services.audit import verify_audit_chain

router = APIRouter(prefix="/audit-logs", tags=["plat-审计日志"])


@router.get("", response_model=None)
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    resource: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role("platform", "xingyao")),
):
    conds = [PlatAuditLog.is_deleted.is_(False)]
    if resource:
        conds.append(PlatAuditLog.resource == resource)
    total = (
        await db.scalar(select(func.count()).select_from(PlatAuditLog).where(*conds)) or 0
    )
    rows = (
        await db.execute(
            select(PlatAuditLog)
            .where(*conds)
            .order_by(PlatAuditLog.id.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    ).scalars().all()
    return success(
        data=PageResult(
            total=total,
            page=page,
            page_size=page_size,
            items=[AuditLogOut.model_validate(r) for r in rows],
        )
    )


@router.get("/verify", response_model=None)
async def verify_chain(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role("platform", "xingyao")),
):
    """校验审计哈希链完整性，返回首个断裂点的 seq_no（ok=true 表示完整）。"""
    ok, broken_at = await verify_audit_chain(db)
    return success(data={"ok": ok, "broken_at_seq": broken_at})
