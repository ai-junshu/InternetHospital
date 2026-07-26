# backend · 业务后端（FastAPI）

> 互联网医疗中心平台业务后端，按技术架构第10/11章落地：模块 `ih`（互联网医院）/ `mt`（健康数据中台）/ `plat`（平台），统一响应、JWT+RBAC、幂等、审计中间件，Alembic 迁移 `ih_/mt_/plat_` 表结构。

## 技术栈
Python 3.11 · FastAPI · SQLAlchemy 2.0（异步）· Alembic · PostgreSQL(+pgvector) · Redis · MongoDB · ClickHouse

## 本地启动

```powershell
# 1. 先启动 infra 依赖：在 code/infra 执行 docker compose up -d
# 2. 安装依赖
pip install -e .

# 3. 初始化数据库表结构（Alembic）
alembic upgrade head

# 4. 启动开发服务
uvicorn app.main:app --reload --port 8000
```

- OpenAPI 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health
- 导出契约：http://localhost:8000/openapi.json（供前端 Mock 与联调，第10.2章）

## 目录结构
```
app/
├── main.py                 # 入口：中间件链 + 路由挂载 + /health /docs
├── core/                   # config / response / errors / security / deps
├── middleware/             # request_id / idempotency / audit / rbac
├── api/v1/{ih,mt,plat}/    # 三模块路由占位
├── models/                 # ORM（base + ih_/mt_/plat_）
├── schemas/                # Pydantic（common + ih/mt/plat）
└── db/                     # session / redis / mongo / clickhouse 客户端
alembic/                    # 迁移（0001_initial 建全部表）
tests/                      # pytest
```
