# infra · 基础设施仓库

> 互联网医疗中心平台多仓库架构中的**基础设施基座**：统一管理本地依赖、共享 CI/CD 模板与 K8s 部署骨架。各业务仓库（backend / ai-service / mp-taro / admin-web）独立迭代，运行时依赖本仓库提供的本地环境。

## 目录结构

```
infra/
├── docker-compose.yml          # 本地一键起全部依赖
├── .env.example                # 环境变量模板（复制为 .env）
├── pre-commit-config.yaml      # 共享代码质量钩子（ruff/eslint/密钥扫描）
├── .github/workflows/          # 共享 CI 模板（ci-python.yml / ci-node.yml）
├── docker/
│   ├── postgres/init-pgvector.sql   # 启用 pgvector 扩展
│   └── clickhouse/init.sql          # mt_store_metrics 宽表 DDL 占位
├── nginx/dev.conf              # 本地开发反向代理（前端 → 后端 API）
└── k8s/helm/                   # Helm chart 骨架（ns-business/ns-ai/ns-data）
```

## 一、本地依赖（开发环境）

```powershell
# 1. 准备环境变量
cp .env.example .env           # Windows: copy .env.example .env

# 2. 一键启动全部依赖
docker compose up -d

# 3. 查看健康状态
docker compose ps
```

启动后各服务端口（默认，可在 .env 覆盖）：

| 服务 | 端口 | 用途 | 依据 |
| ---- | ---- | ---- | ---- |
| PostgreSQL(+pgvector) | 5432 | 业务主库 + 向量 | 第5/7章 |
| Redis | 6379 | 缓存/会话/限流 | 第5章 |
| MongoDB | 27017 | 治疗记录/评估原始 JSON | 第5章 |
| ClickHouse | 8123/19000 | OLAP 经营宽表 | 第5/11.3章 |
| MinIO | 9000/9001 | 私有桶对象存储（等价 OSS/COS） | 第14.4章 |
| Jaeger | 16686 | 链路追踪 UI | 第15.5章 |
| Prometheus | 9090 | 指标采集 | 第12.2/15.5章 |
| Grafana | 3000 | 看板可视化 | 第9/12.2章 |

## 二、各业务仓库开发约定

各仓库连接串统一引用 `.env` 中的变量（见 `.env.example`）。技术架构规定的接口前缀与统一响应由 backend 仓库统一落地，前端经 `openapi.yaml` 契约联调。

| 仓库 | 技术栈 | 本地启动 |
| ---- | ------ | -------- |
| backend | Python FastAPI | `uvicorn app.main:app --reload` → http://localhost:8000/docs |
| ai-service | Python FastAPI + MLflow | `uvicorn app.main:app --reload` → http://localhost:8001/docs |
| mp-taro | Taro 3 + React + TS | `npm install && npm run dev` |
| admin-web | React + Vite + AntD Pro | `npm install && npm run dev` → http://localhost:3000 |

## 三、共享 CI/CD

- `ci-python.yml`：ruff lint + pytest + docker build（backend / ai-service 复用）。
- `ci-node.yml`：eslint + jest + docker build（mp-taro / admin-web 复用）。
- 分支模型（第12.2章）：`main`(生产) / `release/*`(预发) / `develop`(集成) / `feature/*`(开发)。

## 四、生产部署（Helm 骨架）

`k8s/helm/` 提供三命名空间（`ns-business` / `ns-ai` / `ns-data`，对应第10.1章拓扑）的占位 chart，需结合真实镜像仓库与 KMS 注入密钥后使用。

## 五、灾备与 RPO/RTO（P5 性能容灾）

### 目标基线
- **RPO（恢复点目标）< 15min**：数据丢失窗口不超过 15 分钟。
- **RTO（恢复时间目标）< 1h**：从故障到服务恢复不超过 1 小时。

### 备份脚本
`scripts/backup_db.sh` 与 `scripts/restore_db.sh` 提供 PostgreSQL 全量备份/恢复：

```bash
# 备份（每日全量，建议 cron 02:00）
source .env && ./scripts/backup_db.sh ihm_platform
# 恢复（会 DROP 重建目标库，需交互确认）
./scripts/restore_db.sh backups/ihm_ihm_platform_20260101-020000.sql.gz ihm_platform
```

### 持久化与冗余约定
- **PostgreSQL**：
  - 每日全量（`backup_db.sh`，保留最近 30 份）+ **WAL 归档**做 PITR（生产开启 `archive_mode=on`）。
  - 主从流复制（至少一个同步/异步只读副本）满足 RPO<15min。
- **Redis**：`docker-compose.yml` 已开启 **AOF 持久化**（`--appendonly yes`），重启不丢缓存/限流计数；备份时可 `redis-cli SAVE` 落 RDB 快照（脚本已含可选步骤）。
- **MongoDB / ClickHouse**：治疗记录原始 JSON 与 OLAP 宽表，按业务重要性纳入相同备份窗口（副本集 + 定时 `mongodump` / `clickhouse-backup`）。

### 高可用与韧性（代码层，已落地）
- 连接池 `pool_pre_ping=True`（断连自动剔除，第10.2章）。
- 应用 `lifespan` 启动探活 + 优雅关闭（释放 PG 连接池与 Redis 连接）。
- `/health` 真实探测 Redis / PostgreSQL 连通，供 K8s liveness/readiness 探针使用。
- 接口限流（Redis 固定窗口，per-ip + per-user）防雪崩；Redis 故障时 best-effort 放行。

### 演练建议
- 每季度一次恢复演练：从最近备份 `restore_db.sh` 到隔离库，校验数据完整性与恢复耗时（校准 RTO）。
