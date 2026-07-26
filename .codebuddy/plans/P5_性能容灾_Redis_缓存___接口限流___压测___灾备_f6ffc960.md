---
name: P5 性能容灾：Redis 缓存 / 接口限流 / 压测 / 灾备
overview: 落地 P5 性能与容灾四大支柱：① Redis 缓存层（cache-aside 装饰器 + 明文/聚合类端点缓存示范）；② 接口限流中间件（Redis 固定窗口，per-IP + per-user 双档，429+Retry-After）；③ 压测 harness（locust dev 依赖 + locustfile 覆盖核心端点）；④ 灾备与韧性（连接池 pool_pre_ping、lifespan 优雅关闭、/health 真实探活、PG/Redis 备份恢复脚本 + RPO/RTO 说明）。全部复用既有 redis_client，不引入额外运行时依赖（限流/缓存均用 redis-py 原生），仅压测加 dev extra。
todos:
  - id: resilience-config
    content: config 增限流/缓存配置项，session 开 pool_pre_ping，main lifespan 探活+优雅关闭，/health 升级依赖状态
    status: completed
  - id: redis-cache
    content: 新建 app/core/cache.py 缓存层与 cached 装饰器，接入 ih/users get_me 与 plat 聚合端点（不缓存 PII/密文）
    status: completed
  - id: rate-limit
    content: 新建 app/middleware/rate_limit.py 双档限流中间件并注册到 main
    status: completed
    dependencies:
      - resilience-config
  - id: load-harness
    content: pyproject 增 locust dev extra，新建 tests/load/locustfile.py 压测脚本
    status: completed
    dependencies:
      - rate-limit
      - redis-cache
  - id: dr-scripts
    content: 新建 infra/scripts backup_db.sh/restore_db.sh 与 README 灾备 RPO/RTO 小节
    status: completed
  - id: verify-p5
    content: 新建 test_rate_limit.py/test_cache.py，跑全量 pytest + 压测冒烟验证限流与缓存生效
    status: completed
    dependencies:
      - rate-limit
      - redis-cache
      - load-harness
---

## 用户需求

推进 P5 性能容灾，覆盖四块能力：Redis 缓存、接口限流、压测 harness、灾备。用户原文："开始推进P5性能容灾（Redis 缓存 / 接口限流 / 压测 / 灾备）"。

## 产品概述

在已落地的鉴权/审计/落库加密基础上，补齐平台性能与容灾基座：通过 Redis 缓存热点只读数据降低 DB 压力，通过接口限流防止滥用与雪崩，提供可执行的压测脚本用于容量评估，并以备份/恢复脚本 + 韧性改造（连接保活、优雅关闭、真实探活）支撑灾备。所有改动复用既有 `redis.asyncio` 客户端与中间件范式，不引入新运行时依赖。

## 核心功能

- Redis 缓存层：cache-aside 装饰器，按 key 命中缓存/回源写回/失效；仅缓存脱敏与聚合类只读数据，不缓存已加密明文或 PII。
- 接口限流：基于 Redis 固定窗口计数器的中间件，支持 per-ip 与 per-user 双档，超返回 429 + Retry-After，可开关、可白名单放行 /health。
- 连接韧性与真实探活：连接池 pool_pre_ping、lifespan 启停钩子、/health 探测 Redis/PG 连通、优雅关闭资源。
- 压测 harness：基于 locust 的脚本，覆盖 /health、登录、get_me、聚合端点，headless 短脉冲验证可用与限流生效。
- 灾备脚本与文档：pg_dump 备份/恢复脚本 + README 灾备与 RPO/RTO 小节（RPO<15min、RTO<1h、Redis AOF 已开）。

## 技术栈

- 后端：FastAPI + SQLAlchemy 2.0（异步）+ Redis（`redis.asyncio`，依赖已含 `redis>=5.0`，**无新增运行时依赖**）。
- 压测：locust（仅 `dev` extra，`pyproject` optional-dependencies，非运行时）。
- 灾备：bash + `pg_dump`/`pg_restore`（PostgreSQL 自带），复用 `infra/docker-compose.yml` 的 redis（AOF 已开）。

## 实现方式

### 1. Redis 缓存层（cache-aside）

- 新建 `app/core/cache.py`：基于既有 `get_redis()` 提供 `cache_get/cache_set/cache_delete`（JSON 序列化）+ `build_key(*parts)`；提供 `cached(ttl, key_builder)` 装饰器包裹 FastAPI 读端点。命中直接返回缓存、未命中执行后写回；写操作侧用 `cache_invalidate` 失效相关 key。
- 接入示范（调用点小改，验证用）：`ih/users.py get_me` 加 per-user 缓存（key=`me:{sub}`，ttl 取 `cache_default_ttl`）；`plat` 某个聚合只读端点加 cache-aside。**禁止缓存 health_tags 等密文/PII**。

### 2. 接口限流中间件

- 新建 `app/middleware/rate_limit.py`：`RateLimitMiddleware(BaseHTTPMiddleware)`。
- Redis 固定窗口：原子 `INCR` + 首次 `EXPIRE`（pipeline 保证原子性），单位时间窗口（默认 60s）。双档：`per_ip`（默认 60/min）+ `per_user`（解析 Bearer JWT 取 sub，默认 120/min），复用 `audit.py` 的 JWT 解析范式。
- 超限返回 `429` + `Retry-After` 头 + 统一错误体；`settings.rate_limit_enabled` 开关；`rate_limit_whitelist_paths` 含 `/health`、`/docs`、`/openapi.json`。
- 容错：Redis 不可用时放行（best-effort，不阻断业务）。
- 注册：在 `main.py` 中 `RequestIdMiddleware` 之后、`IdempotencyMiddleware` 之前（限流先于审计，避免审计被拦请求放大写量），并 import。

### 3. 连接韧性与真实探活

- `app/db/session.py`：`pool_pre_ping=True`（连接保活，容灾）。
- `app/main.py` `lifespan`：启动 ping Redis（`PING`）与 PG（`SELECT 1`）；关闭时 `await engine.dispose()` + `await redis_client.aclose()`。
- `/health` 升级：返回 Redis/PG 各依赖状态，仍保留总态 `ok`。
- `config.py` 增：`rate_limit_enabled`、`rate_limit_per_ip_per_min`、`rate_limit_per_user_per_min`、`rate_limit_whitelist_paths`、`cache_default_ttl`；`.env.example` 补对应变量。

### 4. 压测 harness

- `pyproject.toml` 增 `[project.optional-dependencies] dev = ["locust>=2.0"]`。
- 新建 `tests/load/locustfile.py`：覆盖 `/health`、`POST /api/v1/auth/login`、`GET /api/v1/ih/users/me`、`GET /api/v1/plat/...` 聚合端点；参数化用户数与速率；注释给出 headless 示例：`locust -f tests/load/locustfile.py --headless -u 50 -r 10 -t 30s -H http://localhost:8000`。

### 5. 灾备脚本与文档

- 新建 `infra/scripts/backup_db.sh`：`pg_dump` 业务库（压缩归档），附带 redis 快照说明与 mongo/clickhouse 可选；输出带时间戳文件。
- 新建 `infra/scripts/restore_db.sh`：对应 `pg_restore` 恢复流程 + 前置校验。
- `infra/README.md` 增"灾备与 RPO/RTO"小节：每日全量 + WAL 归档、RPO<15min、RTO<1h、Redis AOF 已开（compose `--appendonly yes`），备份脚本 cron 化建议。

### 6. 验证（运行时，沿用"实际跑通"习惯）

- 起 `infra` docker（redis 必需）；`pytest tests/` 全量仍通过（含既有 11 项）。
- 新建 `tests/test_rate_limit.py`：本地起 uvicorn，连续请求超限端点，断言 429 与 Retry-After；合法速率内返回 200。
- 新建 `tests/test_cache.py`：走 docker redis，验证 `get_me` 二次请求命中缓存（绕过 DB 查询，借计数或 TTL）、TTL 过期失效。
- 压测冒烟：headless locust 短脉冲（如 -u 30 -t 20s）跑通，观察 429 触发与 P95 延迟，输出简要结论。

## 实现要点

- 性能：Redis 读写 O(1)；固定窗口计数开销极小；限流/缓存均 best-effort，Redis 故障不阻断主流程。
- 一致性：严格复用既有中间件范式（BaseHTTPMiddleware + JWT 解析）与 `get_redis()`，与 P4 安全增强风格统一；配置注入密钥/开关沿用 `.env` 约定。
- 爆炸半径控制：限流白名单放行 /health；不缓存已加密字段与 PII；迁移/接口零破坏性改动（缓存为可选旁路）。
- 安全：仅缓存脱敏/聚合/参考类数据；密文字段（totp_secret/health_tags）绝不进缓存，避免重新暴露明文。

## 架构设计

```mermaid
flowchart LR
  C[Client] --> RL[RateLimitMiddleware<br/>Redis 固定窗口]
  RL --> ID[IdempotencyMiddleware]
  ID --> AU[AuditMiddleware]
  AU --> H[Handlers]
  H --> DB[(PostgreSQL)]
  H --> RC[(Redis)]
  subgraph 缓存旁路
    H -. 命中 .-> RC
    H -. 未命中/写回 .-> DB
    H -. 写后失效 .-> RC
  end
  RL -. INCR/EXPIRE .-> RC
  Health[/health] --> PG[(PG SELECT 1)]
  Health --> RP[(Redis PING)]
```