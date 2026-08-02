"""审计留痕服务（技术架构第10.2/13章，P4 哈希链防篡改）。

写操作统一落 plat_audit_log；与业务在同一事务内提交，保证一致。
每条记录携带链式哈希：hash = SHA256(seq_no|prev_hash|actor|role|action|resource|before|after|ip)，
prev_hash 取上一条记录的 hash，形成不可篡改的哈希链。
"""
import hashlib
import json
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plat_models import PlatAuditLog
from app.utils.mask import mask_json


def compute_audit_hash(
    *,
    seq_no: int,
    prev_hash: str,
    actor_id: Optional[int],
    role: Optional[str],
    action: str,
    resource: str,
    before: Optional[dict],
    after: Optional[dict],
    ip: Optional[str],
) -> str:
    """计算审计记录哈希（规范化拼接后 SHA-256）。"""
    canonical = "|".join(
        [
            str(seq_no),
            prev_hash or "",
            str(actor_id),
            role or "",
            action,
            resource or "",
            json.dumps(before or {}, sort_keys=True, ensure_ascii=False),
            json.dumps(after or {}, sort_keys=True, ensure_ascii=False),
            ip or "",
        ]
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def write_audit(
    db: AsyncSession,
    *,
    action: str,
    resource: str,
    role: Optional[str] = None,
    actor_id: Optional[int] = None,
    before: Optional[dict] = None,
    after: Optional[dict] = None,
    ip: Optional[str] = None,
) -> None:
    # 落库前脱敏：before/after 中敏感字段（身份证/手机/姓名等）明文不入审计表
    masked_before = mask_json(before) if before else before
    masked_after = mask_json(after) if after else after

    # 取最近一条记录的 hash 作为 prev_hash，count+1 作为 seq_no（同事务内）
    last = await db.scalar(select(PlatAuditLog).order_by(PlatAuditLog.id.desc()).limit(1))
    prev_hash = last.hash if last else ""
    count = await db.scalar(select(func.count()).select_from(PlatAuditLog)) or 0
    seq_no = count + 1
    rec = PlatAuditLog(
        actor_id=actor_id,
        role=role,
        action=action,
        resource=resource,
        before_json=masked_before,
        after_json=masked_after,
        ip=ip,
        seq_no=seq_no,
        prev_hash=prev_hash,
    )
    rec.hash = compute_audit_hash(
        seq_no=seq_no,
        prev_hash=prev_hash,
        actor_id=actor_id,
        role=role,
        action=action,
        resource=resource,
        before=masked_before,
        after=masked_after,
        ip=ip,
    )
    db.add(rec)


async def verify_audit_chain(db: AsyncSession) -> tuple[bool, Optional[int]]:
    """校验整条哈希链完整性。返回 (是否完整, 首个断裂点的 seq_no)。"""
    rows = (
        await db.execute(
            select(PlatAuditLog)
            .where(PlatAuditLog.is_deleted.is_(False))
            .order_by(PlatAuditLog.id.asc())
        )
    ).scalars().all()
    prev = ""
    for r in rows:
        if r.prev_hash != prev:
            return False, r.seq_no
        expected = compute_audit_hash(
            seq_no=r.seq_no,
            prev_hash=r.prev_hash,
            actor_id=r.actor_id,
            role=r.role,
            action=r.action or "",
            resource=r.resource or "",
            before=r.before_json,
            after=r.after_json,
            ip=r.ip,
        )
        if expected != r.hash:
            return False, r.seq_no
        prev = r.hash
    return True, None
