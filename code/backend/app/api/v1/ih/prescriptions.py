"""互联网医院处方：开方（待审核）→ 药师审核（通过/驳回）（第11.2/13.3章）。"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError, ErrorCode
from app.core.response import success
from app.core.deps import get_db, current_user, require_role, actor_of
from app.models.ih_models import IhPrescription, IhPrescriptionItem
from app.schemas.common import PageResult
from app.schemas.ih import (
    PrescriptionAuditIn,
    PrescriptionCreate,
    PrescriptionOut,
)
from app.services.audit import write_audit
from app.services.rx_engine import get_rx_engine
from app.utils.idgen import gen_no

router = APIRouter(prefix="/prescriptions", tags=["ih-处方"])


@router.post("", response_model=None)
async def create_prescription(
    body: PrescriptionCreate, request: Request, _user: dict = Depends(current_user), db: AsyncSession = Depends(get_db)
):
    no = gen_no("RX")
    rx = IhPrescription(
        prescription_no=no,
        patient_id=body.patient_id,
        doctor_id=body.doctor_id,
        diagnose=body.diagnose,
        items_json=[i.model_dump() for i in body.items],
        signature_url=body.signature_url,
        status="pending_audit",
    )
    db.add(rx)
    await db.flush()
    for it in body.items:
        db.add(IhPrescriptionItem(prescription_id=rx.id, **it.model_dump()))

    # 合理用药引擎前置校验（第14章第三方对接）：冲突/禁忌/剂量。
    # 真实传入患者孕期/过敏与药品单日用量，使禁忌与剂量告警可触发（风险3修复）。
    # 校验失败仅告警降级，保障开方主链路可用（参考 pred_log 独立事务模式）。
    rx_prescription = {
        "patient": {
            "pregnancy": bool(body.patient_pregnancy),
            "allergy": list(body.patient_allergies or []),
        },
        "items": [
            {
                "drug_name": it.name,
                "dose": it.dosage,
                "freq": it.freq,
                "daily_dose": it.daily_dose,
                "max_daily_dose": it.max_daily_dose,
            }
            for it in body.items
        ],
    }
    try:
        rx_result = get_rx_engine().check(rx_prescription)
        rx.rx_check_json = rx_result.model_dump(mode="json")
    except Exception as e:  # noqa: BLE001 - 降级不阻断开方
        rx.rx_check_json = {
            "provider": "mock",
            "degraded": True,
            "error": str(e),
            "conflicts": [],
            "contraindications": [],
            "dosage_warnings": [],
        }

    await db.commit()
    await db.refresh(rx)
    await write_audit(
        db,
        action="prescription.create",
        resource="ih_prescription",
        role=_user.get("role"),
        actor_id=actor_of(_user),
        after={"prescription_no": no, "status": "pending_audit"},
        ip=request.client.host if request.client else None,
    )
    return success(data=PrescriptionOut.model_validate(rx))


@router.get("", response_model=None)
async def list_prescriptions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    _auth: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    conds = [IhPrescription.is_deleted.is_(False)]
    if status:
        conds.append(IhPrescription.status == status)
    total = (
        await db.scalar(select(func.count()).select_from(IhPrescription).where(*conds))
        or 0
    )
    rows = (
        await db.execute(
            select(IhPrescription)
            .where(*conds)
            .order_by(IhPrescription.id.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    ).scalars().all()
    return success(
        data=PageResult(
            total=total,
            page=page,
            page_size=page_size,
            items=[PrescriptionOut.model_validate(r) for r in rows],
        )
    )


@router.get("/{rx_id}", response_model=None)
async def get_prescription(rx_id: int, _auth: dict = Depends(current_user), db: AsyncSession = Depends(get_db)):
    rx = await db.get(IhPrescription, rx_id)
    if not rx or rx.is_deleted:
        raise BusinessError(ErrorCode.RESOURCE_NOT_FOUND, "处方不存在")
    return success(data=PrescriptionOut.model_validate(rx))


@router.patch("/{rx_id}/audit", response_model=None)
async def audit_prescription(
    rx_id: int, body: PrescriptionAuditIn, request: Request, _user: dict = Depends(require_role("doctor", "platform")), db: AsyncSession = Depends(get_db)
):
    rx = await db.get(IhPrescription, rx_id)
    if not rx or rx.is_deleted:
        raise BusinessError(ErrorCode.RESOURCE_NOT_FOUND, "处方不存在")
    if rx.status != "pending_audit":
        raise BusinessError(ErrorCode.PRESCRIPTION_PENDING, "仅待审核处方可审核")
    if body.action not in ("approve", "reject"):
        raise BusinessError(ErrorCode.PARAM_INVALID, "action 仅支持 approve/reject")
    rx.status = "approved" if body.action == "approve" else "rejected"
    rx.pharmacist_id = body.reviewer_id
    rx.audit_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(rx)
    await write_audit(
        db,
        action=f"prescription.{body.action}",
        resource="ih_prescription",
        role=_user.get("role"),
        actor_id=actor_of(_user),
        before={"status": "pending_audit"},
        after={"status": rx.status},
        ip=request.client.host if request.client else None,
    )
    return success(data=PrescriptionOut.model_validate(rx))
