#!/usr/bin/env bash
# 业务库备份脚本（PostgreSQL）— P5 灾备
#
# 用法：
#   ./backup_db.sh [DBNAME]
# 环境变量（可放在 infra/.env 后 source）：
#   PGHOST / PGPORT / PGUSER / PGPASSWORD / PGDATABASE
#   REDIS_URI            （可选，用于触发 Redis RDB 快照）
#   BACKUP_DIR           （默认 ./backups）
#
# 产出：
#   <BACKUP_DIR>/ihm_<db>_<YYYYmmdd-HHMMSS>.sql.gz
#
# 说明：
#   - 使用 pg_dump 自定义格式（-Fc）更适合 pg_restore；这里用 -Z9 压缩纯文本，便于直接查看/恢复。
#   - 建议在 cron 中每日全量（如 02:00），配合 WAL 归档做 PITR（见 README）。
set -euo pipefail

DBNAME="${1:-${PGDATABASE:-ihm_platform}}"
BACKUP_DIR="${BACKUP_DIR:-$(cd "$(dirname "$0")/.." && pwd)/backups}"
TS="$(date +%Y%m%d-%H%M%S)"
OUT="${BACKUP_DIR}/ihm_${DBNAME}_${TS}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "[backup] dumping ${DBNAME} -> ${OUT}"
pg_dump \
  --host="${PGHOST:-localhost}" \
  --port="${PGPORT:-5432}" \
  --username="${PGUSER:-postgres}" \
  --dbname="$DBNAME" \
  --no-owner --no-privileges \
  --clean --if-exists \
  | gzip -9 > "$OUT"

echo "[backup] done: $(du -h "$OUT" | cut -f1)"

# 可选：触发 Redis 持久化快照（AOF 已开时同样生效）
if [ -n "${REDIS_URI:-}" ]; then
  echo "[backup] redis SAVE (snapshot)"
  redis-cli -u "$REDIS_URI" SAVE || echo "[backup] redis SAVE skipped (unreachable)"
fi

echo "[backup] keep-latest: 仅保留最近 30 份"
ls -1t "${BACKUP_DIR}"/ihm_${DBNAME}_*.sql.gz 2>/dev/null | tail -n +31 | xargs -r rm -f
