"""健康数据中台：治疗记录（不可删仅可更正留痕，技术架构第11.2章）。"""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError, ErrorCode
from app.core.response import success
from app.core.deps import get_db, require_role, actor_of, store_scope
from app.models.mt_models import MtTreatmentRecord, MtTreatmentRecordRevision
from app.schemas.common import PageResult
from app.schemas.mt import (
    TreatmentRecordCreate,
    TreatmentRecordOut,
    TreatmentRecordReviseIn,
    TreatmentRecordRevisionOut,
)
from app.services.audit import write_audit

router = APIRouter(prefix="/treatment-records", tags=["mt-治疗记录"])


@router.post("", response_model=None)
async def create_treatment_record(
    body: TreatmentRecordCreate, request: Request, _user: dict = Depends(require_role("store", "therapist", "platform", "xingyao")), db: AsyncSession = Depends(get_db)
):
    rec = MtTreatmentRecord(**body.model_dump())
    db.add(rec)
    await db.commit()
    await db.refresh(rec)
    await write_audit(
        db,
        action="treatment_record.create",
        resource="mt_treatment_record",
        role=_user.get("role"),
        actor_id=actor_of(_user),
        after=TreatmentRecordOut.model_validate(rec).model_dump(mode="json"),
        ip=request.client.host if request.client else None,
    )
    return success(data=TreatmentRecordOut.model_validate(rec))


@router.get("", response_model=None)
async def list_treatment_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: int | None = None,
    scope: int | None = Depends(store_scope),
    _auth: dict = Depends(require_role("store", "therapist", "platform", "xingyao")),
    db: AsyncSession = Depends(get_db),
):
    conds = [MtTreatmentRecord.is_deleted.is_(False)]
    if customer_id is not None:
        conds.append(MtTreatmentRecord.customer_id == customer_id)
    if scope is not None:
        conds.append(MtTreatmentRecord.store_id == scope)
    total = (
        await db.scalar(
            select(func.count()).select_from(MtTreatmentRecord).where(*conds)
        )
        or 0
    )
    rows = (
        await db.execute(
            select(MtTreatmentRecord)
            .where(*conds)
            .order_by(MtTreatmentRecord.id.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    ).scalars().all()
    return success(
        data=PageResult(
            total=total,
            page=page,
            page_size=page_size,
            items=[TreatmentRecordOut.model_validate(r) for r in rows],
        )
    )


# 合规强规则2：治疗记录一经提交不可删除，仅可补充更正并留痕。
# 此处显式不提供 DELETE 端点；更正通过 PATCH 追加修订记录实现。
_ALLOWED_REVISE_FIELDS = {
    "products_json",
    "oper_sites_json",
    "nps",
    "images_json",
    "remark",
}


@router.patch("/{record_id}", response_model=None)
async def revise_treatment_record(
    record_id: int,
    body: TreatmentRecordReviseIn,
    request: Request,
    _user: dict = Depends(require_role("store", "therapist", "platform", "xingyao")),
    scope: int | None = Depends(store_scope),
    db: AsyncSession = Depends(get_db),
):
    rec = await db.get(MtTreatmentRecord, record_id)
    if rec is None or rec.is_deleted:
        raise BusinessError(ErrorCode.NOT_FOUND, "治疗记录不存在")
    # RLS：非本门店无权更正
    if scope is not None and rec.store_id != scope:
        raise BusinessError(ErrorCode.FORBIDDEN, "无权限更正非本门店治疗记录")

    before = TreatmentRecordOut.model_validate(rec).model_dump(mode="json")
    for field in _ALLOWED_REVISE_FIELDS:
        val = getattr(body, field)
        if val is not None:
            setattr(rec, field, val)
    await db.commit()
    await db.refresh(rec)
    after = TreatmentRecordOut.model_validate(rec).model_dump(mode="json")

    # 留痕：审计前后对照 + 修订表
    await write_audit(
        db,
        action="treatment_record.revise",
        resource="mt_treatment_record",
        role=_user.get("role"),
        actor_id=actor_of(_user),
        before=before,
        after=after,
        ip=request.client.host if request.client else None,
    )
    rev = MtTreatmentRecordRevision(
        record_id=rec.id,
        revised_by=actor_of(_user),
        revised_by_role=_user.get("role"),
        before_json=before,
        after_json=after,
        reason=body.reason,
    )
    db.add(rev)
    await db.commit()
    await db.refresh(rev)
    return success(
        data={
            "record": TreatmentRecordOut.model_validate(rec),
            "revision": TreatmentRecordRevisionOut.model_validate(rev),
        }
    )
