"""AI 预测日志写入（第15.4章 反馈闭环，human-in-the-loop）。

业务逻辑回写 AI 预测后，记录 plat_model_pred_log(adopted='pending')，
供运营在后台采纳/驳回，支撑模型迭代。

写入为补充审计：使用独立事务，失败仅告警，不阻断主业务链路。
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.plat_models import PlatModelPredLog

logger = logging.getLogger("pred_log")


async def create_pred_log(
    model_id: int | None,
    version: str | None,
    customer_id: int,
    input_json: dict | None,
    predict_json: dict | None,
    user_id: int | None = None,
) -> int | None:
    """落一条预测日志（pending）。返回日志 id；失败返回 None（降级）。"""
    try:
        async with SessionLocal() as s:
            log = PlatModelPredLog(
                model_id=model_id,
                version=version,
                customer_id=customer_id,
                input_features_json=input_json,
                predict_result_json=predict_json,
                predict_time=datetime.now(timezone.utc),
                user_id=user_id,
                adopted="pending",
            )
            s.add(log)
            await s.commit()
            await s.refresh(log)
            return log.id
    except Exception as e:  # noqa: BLE001
        logger.warning("plat_model_pred_log 写入失败(降级, 不阻断主链路): %s", e)
        return None


async def list_pred_logs(
    page: int,
    page_size: int,
    model_id: int | None = None,
    customer_id: int | None = None,
    adopted: str | None = None,
) -> tuple[list[PlatModelPredLog], int]:
    """分页查询预测日志（供平台/星耀后台）。"""
    async with SessionLocal() as s:
        conds = [PlatModelPredLog.is_deleted.is_(False)]
        if model_id is not None:
            conds.append(PlatModelPredLog.model_id == model_id)
        if customer_id is not None:
            conds.append(PlatModelPredLog.customer_id == customer_id)
        if adopted:
            conds.append(PlatModelPredLog.adopted == adopted)
        total = (
            await s.scalar(select(func.count()).select_from(PlatModelPredLog).where(*conds))
            or 0
        )
        rows = (
            await s.execute(
                select(PlatModelPredLog)
                .where(*conds)
                .order_by(PlatModelPredLog.id.desc())
                .limit(page_size)
                .offset((page - 1) * page_size)
            )
        ).scalars().all()
        return list(rows), total


async def set_adopted(log_id: int, adopted: str) -> PlatModelPredLog | None:
    """更新采纳状态（adopted/rejected）。返回更新后的日志或 None。"""
    async with SessionLocal() as s:
        log = await s.get(PlatModelPredLog, log_id)
        if log is None or log.is_deleted:
            return None
        log.adopted = adopted
        await s.commit()
        await s.refresh(log)
        return log
