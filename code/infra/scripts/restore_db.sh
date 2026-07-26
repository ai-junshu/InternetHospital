#!/usr/bin/env bash
# 业务库恢复脚本（PostgreSQL）— P5 灾备
#
# 用法：
#   ./restore_db.sh <backup_file.sql.gz> [DBNAME]
# 环境变量：PGHOST / PGPORT / PGUSER / PGPASSWORD / PGDATABASE（可被位置参数覆盖）
#
# 安全：
#   - 默认目标库为备份内数据库名；生产恢复前务必先确认目标（建议恢复到新库再切换）。
#   - 脚本会重建目标库（DROP+CREATE），请确认无重要未备份数据。
set -euo pipefail

BACKUP="${1:?用法: ./restore_db.sh <backup_file.sql.gz> [DBNAME]}"
DBNAME="${2:-${PGDATABASE:-ihm_platform}}"
PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-postgres}"

if [ ! -f "$BACKUP" ]; then
  echo "[restore] ERROR: 备份文件不存在: $BACKUP" >&2
  exit 1
fi

echo "[restore] 目标: ${PGUSER}@${PGHOST}:${PGPORT}/${DBNAME}"
read -r -p "[restore] 将 DROP 并重建 '${DBNAME}'，确认? (yes/N) " CONFIRM
if [ "${CONFIRM}" != "yes" ]; then
  echo "[restore] 已取消"
  exit 0
fi

export PGPASSWORD
echo "[restore] 终止连接 + 重建数据库"
psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d postgres -v ON_ERROR_STOP=1 <<SQL
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${DBNAME}' AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS "${DBNAME}";
CREATE DATABASE "${DBNAME}";
SQL

echo "[restore] 从 ${BACKUP} 恢复"
gunzip -c "$BACKUP" \
  | psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$DBNAME" -v ON_ERROR_STOP=1

echo "[restore] 完成 ✅"
