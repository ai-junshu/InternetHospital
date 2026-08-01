"""互联网医院：监管看板聚合（PRD 3.3 合规监管看板）。

单个 GET 返回聚合 JSON，替代前端 4×page_size=1 拼 total 的临时方案：
- 核心指标：在线医师数、待审处方数、累计问诊数、已支付订单数
- 合规：处方总数、审方通过率、投诉量
- 预警：低库存药品数（stock < safety_stock）、近 30 日处方趋势
复用既有 {users,doctors,prescriptions,orders,consultations} 表的聚合查询，不加新表。
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.response import success
from app.models.ih_models import (
    IhComplaint,
    IhConsultation,
    IhDoctor,
    IhDrugStock,
    IhOrder,
    IhPrescription,
    IhUser,
)

router = APIRouter(prefix="/dashboards", tags=["ih-监管看板"])


@router.get("", response_model=None)
async def dashboards(db: AsyncSession = Depends(get_db)):
    # 核心指标
    doctors = (
        await db.execute(select(func.count()).select_from(IhDoctor).where(IhDoctor.is_deleted.is_(False), IhDoctor.status == "active"))
    ).scalar() or 0
    pending_rx = (
        await db.execute(
            select(func.count()).select_from(IhPrescription).where(IhPrescription.is_deleted.is_(False), IhPrescription.status == "pending_audit")
        )
    ).scalar() or 0
    consults = (
        await db.execute(select(func.count()).select_from(IhConsultation).where(IhConsultation.is_deleted.is_(False)))
    ).scalar() or 0
    paid_orders = (
        await db.execute(select(func.count()).select_from(IhOrder).where(IhOrder.is_deleted.is_(False), IhOrder.pay_status == "paid"))
    ).scalar() or 0

    # 合规：处方总数 + 审方通过率
    rx_total = (
        await db.execute(select(func.count()).select_from(IhPrescription).where(IhPrescription.is_deleted.is_(False)))
    ).scalar() or 0
    rx_approved = (
        await db.execute(
            select(func.count()).select_from(IhPrescription).where(IhPrescription.is_deleted.is_(False), IhPrescription.status == "approved")
        )
    ).scalar() or 0
    rx_pass_rate = round(rx_approved / rx_total, 4) if rx_total else 0.0

    # 投诉量
    complaints = (
        await db.execute(select(func.count()).select_from(IhComplaint).where(IhComplaint.is_deleted.is_(False)))
    ).scalar() or 0

    # 低库存预警
    low_stock = (
        await db.execute(
            select(func.count()).select_from(IhDrugStock).where(
                IhDrugStock.is_deleted.is_(False),
                IhDrugStock.safety_stock > 0,
                IhDrugStock.stock < IhDrugStock.safety_stock,
            )
        )
    ).scalar() or 0

    # 近 30 日处方趋势（按日期分组）
    since = datetime.now(timezone.utc) - timedelta(days=30)
    day_expr = func.to_char(IhPrescription.created_at, "YYYY-MM-DD")
    trend_rows = (
        await db.execute(
            select(day_expr.label("day"), func.count().label("cnt"))
            .where(IhPrescription.is_deleted.is_(False), IhPrescription.created_at >= since)
            .group_by(day_expr)
            .order_by(day_expr)
        )
    ).all()
    rx_trend = [{"date": r.day, "count": r.cnt} for r in trend_rows]

    return success(
        data={
            "core": {
                "active_doctors": doctors,
                "pending_prescriptions": pending_rx,
                "total_consultations": consults,
                "paid_orders": paid_orders,
            },
            "compliance": {
                "prescription_total": rx_total,
                "prescription_approved": rx_approved,
                "prescription_pass_rate": rx_pass_rate,
                "complaint_total": complaints,
            },
            "warning": {
                "low_stock_count": low_stock,
            },
            "rx_trend_30d": rx_trend,
        }
    )
