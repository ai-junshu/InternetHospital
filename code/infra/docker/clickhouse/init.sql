-- 互联网医疗中心平台 · ClickHouse 初始化
-- 经营指标宽表（技术架构第11.3章：支撑看板多维分析，预聚合）
-- 占位 DDL，后续由数据中台服务写入与维护。

CREATE DATABASE IF NOT EXISTS ihm;

CREATE TABLE IF NOT EXISTS ihm.mt_store_metrics
(
    date Date,
    store_id UInt64,
    region String,
    appointment_cnt UInt32 DEFAULT 0,
    arrival_cnt UInt32 DEFAULT 0,
    deal_customers UInt32 DEFAULT 0,
    deal_amount Float64 DEFAULT 0,
    deal_orders UInt32 DEFAULT 0,
    repurchase_customers UInt32 DEFAULT 0,
    nps_avg Float32 DEFAULT 0
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (store_id, date);
