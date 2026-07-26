"""门店经营宽表聚合（技术架构第11.3章）。

将 PG mt_* 按日预聚合写入 ClickHouse mt_store_metrics，供 admin-web 看板
与 Grafana 多维分析。写入为幂等（先删后插），ClickHouse 不可用时仅告警降级，
不阻断主链路。

注：PG mt_treatment_record 无金额/订单字段，deal_amount/deal_orders 暂置 0，
待 P3 订单系统对接后补齐（不影响到店/客户/NPS/复购等真实指标）。
"""
import logging
from datetime import date, datetime, timezone
from typing import Iterable

from sqlalchemy import Date, distinct, func, select

from app.db.clickhouse_client import ch_client
from app.db.session import SessionLocal
from app.models.mt_models import (
    MtCustomer,
    MtRepurchasePrediction,
    MtStore,
    MtTreatmentRecord,
)

logger = logging.getLogger("store_metrics")

_COLUMNS = (
    "date", "store_id", "store_name", "region",
    "appointment_cnt", "arrival_cnt", "deal_customers",
    "deal_amount", "deal_orders", "repurchase_customers", "nps_avg",
)
_INSERT_SQL = f"INSERT INTO mt_store_metrics ({', '.join(_COLUMNS)}) VALUES"


def compute_metrics_row(
    target_date: date,
    store_id: int,
    store_name: str,
    region: str,
    appointment_cnt: int,
    deal_customers: int,
    nps_avg: float | None,
    repurchase_customers: int,
) -> tuple:
    """由 PG 聚合结果构造一条 ClickHouse 宽表行（纯函数，便于单测）。"""
    # 到店率/成交率由看板侧计算；此处到店=服务笔数（服务的即到店），成交客户=去重客户数
    return (
        target_date,
        store_id,
        store_name or "",
        region or "",
        int(appointment_cnt or 0),
        int(appointment_cnt or 0),  # arrival 代理：已服务的即到店
        int(deal_customers or 0),
        0.0,  # deal_amount：PG 无金额字段，待 P3 订单对接
        0,    # deal_orders：同上
        int(repurchase_customers or 0),
        float(nps_avg or 0.0),
    )


async def aggregate_store_metrics(target_date: date, store_id: int | None = None) -> int:
    """聚合指定日期（可指定门店）写入 ClickHouse，返回写入行数。"""
    async with SessionLocal() as s:
        # 1) 治疗记录：按门店聚合到店/客户/NPS
        t_stmt = (
            select(
                MtTreatmentRecord.store_id,
                func.count(MtTreatmentRecord.id).label("appointment_cnt"),
                func.count(distinct(MtTreatmentRecord.customer_id)).label("deal_customers"),
                func.avg(MtTreatmentRecord.nps).label("nps_avg"),
            )
            .where(
                MtTreatmentRecord.service_time.isnot(None),
                MtTreatmentRecord.service_time.cast(Date) == target_date,
            )
            .group_by(MtTreatmentRecord.store_id)
        )
        if store_id is not None:
            t_stmt = t_stmt.where(MtTreatmentRecord.store_id == store_id)
        t_rows = (await s.execute(t_stmt)).all()

        # 2) 门店元数据
        stores = (await s.execute(select(MtStore))).scalars().all()
        store_meta = {st.id: st for st in stores}

        # 3) 复购客户：repurchase_prob>=0.5 且截至当日（按 source_store_id 关联）
        r_stmt = (
            select(
                MtCustomer.source_store_id,
                func.count(distinct(MtRepurchasePrediction.customer_id)).label("rep"),
            )
            .join(MtCustomer, MtRepurchasePrediction.customer_id == MtCustomer.id)
            .where(
                MtRepurchasePrediction.repurchase_prob >= 0.5,
                MtRepurchasePrediction.predict_time.isnot(None),
                MtRepurchasePrediction.predict_time.cast(Date) <= target_date,
            )
            .group_by(MtCustomer.source_store_id)
        )
        if store_id is not None:
            r_stmt = r_stmt.where(MtCustomer.source_store_id == store_id)
        rep_rows = (await s.execute(r_stmt)).all()
        rep_map = {sid: rep for sid, rep in rep_rows if sid is not None}

    ch_rows = [
        compute_metrics_row(
            target_date=target_date,
            store_id=r.store_id,
            store_name=store_meta[r.store_id].name if r.store_id in store_meta else "",
            region=store_meta[r.store_id].region if r.store_id in store_meta else "",
            appointment_cnt=r.appointment_cnt,
            deal_customers=r.deal_customers,
            nps_avg=r.nps_avg,
            repurchase_customers=rep_map.get(r.store_id, 0),
        )
        for r in t_rows
    ]

    if not ch_rows:
        return 0

    # 4) 幂等写入：先删同日同店旧数据，再插入
    try:
        sids = [row[1] for row in ch_rows]
        ch_client.execute(
            "ALTER TABLE mt_store_metrics DELETE WHERE date=%(d)s AND store_id IN %(sids)s",
            {"d": target_date, "sids": sids},
        )
        ch_client.execute(_INSERT_SQL, ch_rows)
        logger.info("门店经营宽表写入 %d 行 (%s)", len(ch_rows), target_date)
        return len(ch_rows)
    except Exception as e:  # noqa: BLE001
        logger.warning("ClickHouse 写入失败(降级, 不阻断主链路): %s", e)
        return 0


async def query_store_metrics(
    page: int,
    page_size: int,
    store_id: int | None = None,
    region: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> tuple[list[dict], int]:
    """从 ClickHouse 查询经营宽表，返回 (rows, total)。CH 不可用时返回空。"""
    try:
        conds: list[str] = []
        params: dict = {}
        if store_id is not None:
            conds.append("store_id=%(store_id)s")
            params["store_id"] = store_id
        if region:
            conds.append("region=%(region)s")
            params["region"] = region
        if date_from is not None:
            conds.append("date>=%(date_from)s")
            params["date_from"] = date_from
        if date_to is not None:
            conds.append("date<=%(date_to)s")
            params["date_to"] = date_to
        where = (" WHERE " + " AND ".join(conds)) if conds else ""
        total = ch_client.execute(f"SELECT count() FROM mt_store_metrics{where}", params)[0][0]
        params["lim"] = page_size
        params["off"] = (page - 1) * page_size
        raw = ch_client.execute(
            f"SELECT {', '.join(_COLUMNS)} FROM mt_store_metrics{where} "
            "ORDER BY date DESC, store_id LIMIT %(lim)s OFFSET %(off)s",
            params,
        )
        rows = [dict(zip(_COLUMNS, r)) for r in raw]
        return rows, total
    except Exception as e:  # noqa: BLE001
        logger.warning("ClickHouse 查询失败(降级返回空): %s", e)
        return [], 0
