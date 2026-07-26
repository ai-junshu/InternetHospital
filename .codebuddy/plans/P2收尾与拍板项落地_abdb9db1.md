---
name: P2收尾与拍板项落地
overview: 执行用户拍板的两项（jwt_secret 加长 + admin-web 登录入口/dev-token），并收尾 P2 遗留（RAG 可解释、AI 反馈闭环、ClickHouse 经营宽表+Grafana 看板）。P2 未做完，故不进入 A/B 并行，而是按架构与 PRD 完善；P3(B) 作为 P2 完成后的下一阶段。
design:
  architecture:
    framework: react
  styleKeywords:
    - Ant Design Pro
    - 后台管理
    - 克制专业
    - 卡片化看板
    - 响应式
  fontSystem:
    fontFamily: PingFang SC
    heading:
      size: 20px
      weight: 600
    subheading:
      size: 14px
      weight: 500
    body:
      size: 14px
      weight: 400
  colorSystem:
    primary:
      - "#1677FF"
      - "#4096FF"
    background:
      - "#F5F7FA"
      - "#FFFFFF"
    text:
      - "#1F2329"
      - "#8C8C8C"
    functional:
      - "#52C41A"
      - "#FF4D4F"
      - "#FAAD14"
todos:
  - id: harden-jwt-secret
    content: 将 config.py 的 jwt_secret 改为 ≥32 字节强随机串并写入 .env.example，复跑 verify_auth.py 确认告警消失且 9/9 通过
    status: completed
  - id: admin-web-login
    content: 新增 admin-web 登录页（dev-token 角色取令牌）+ AuthRoute 守卫（无 token/401 跳登录），接入 App.tsx
    status: completed
    dependencies:
      - harden-jwt-secret
  - id: ai-rag-rationale
    content: ai-service 新增轻量检索器并在 plan-recommend 返回真实 rationale，backend care_plans 透传落库
    status: completed
  - id: feedback-loop
    content: 新增 plat/model_pred_logs 写入与采纳/驳回接口，care_plans/repurchase/risk 回写时落 plat_model_pred_log
    status: completed
    dependencies:
      - ai-rag-rationale
  - id: store-metrics
    content: 新增 store_metrics 聚合服务（PG→ClickHouse 幂等写入）+ mt/store-metrics 查询接口并注册路由
    status: completed
  - id: dashboard-frontend
    content: admin-web data 页接 store-metrics 渲染门店经营看板，提供 Grafana store_metrics.json
    status: completed
    dependencies:
      - store-metrics
      - admin-web-login
  - id: verify-p2
    content: 用 verify_p2.py 机制级验证 RAG/反馈/宽表，import app.main 核对路由，npx tsc --noEmit 0 错误
    status: completed
    dependencies:
      - ai-rag-rationale
      - feedback-loop
      - store-metrics
      - dashboard-frontend
---

## 用户需求

1. 执行此前标记的两个待办（拍板项）：

- ① admin-web 补充登录入口（dev 环境走 `/api/v1/auth/dev-token` 取各角色 JWT），并加无 token/401 路由守卫跳转登录。
- ② `jwt_secret` 当前仅 22 字符（<32 字节，PyJWT 告警），按技术架构第 14 章「密钥经环境变量注入、HS256 建议 ≥32 字节」加长并固化到 `.env.example`。

2. 核查 P2 是否全部无遗留：经代码实测 **P2 未完成**，存在 3 项遗留（RAG 可解释占位、反馈闭环未落库/无接口、ClickHouse 仅占位 DDL 无写入与看板）。按用户指令「不能同步就按照架构设计方案和需求文档继续完善」——本计划聚焦收尾 P2 + 落地两个拍板项；P3(B) 作为 P2 完成后的后续阶段另行推进。
3. A（admin-web 登录入口）已并入拍板项①一并执行；B（P3 后端：plat 目录/RLS/种子数据/第三方对接）留待 P2 收尾后推进。

## 核心功能

- 后端鉴权加固：将 `jwt_secret` 默认值更换为 ≥32 字节强随机串，写入 `.env.example`，保留环境变量覆盖；本地 `verify_auth.py` 复跑确认 9/9 通过且告警消失。
- admin-web 登录与守卫：新增 Login 页（角色选择 + 调 dev-token 存 localStorage），BasicLayout 增加「无 token 跳登录、401 清 token 跳登录」守卫，3 个业务页接真实数据。
- P2-AI 可解释（第 10.3 章）：ai-service `plan-recommend` 实现轻量 RAG，基于症状/疼痛特征检索历史调理方案与知识库，返回真实 `rationale`（非占位），后端 `care_plans` 透传并落库。
- P2-反馈闭环（第 15.4 章）：backend 调 ai-service 时写 `plat_model_pred_log`（pending）；新增采纳/驳回接口改 `adopted` 状态，支撑 human-in-the-loop 模型迭代。
- P2-经营宽表（第 11.3 章）：backend 新增定时/手动聚合任务，将 PG `mt_*` 按日预聚合写入 ClickHouse `mt_store_metrics`；新增查询接口供 admin-web 看板读取；admin-web `data` 页接真实指标渲染门店经营看板；提供 Grafana dashboard JSON。

## 技术栈选择

- 后端：FastAPI + SQLAlchemy(async) + PyJWT + pydantic；ClickHouse 经 `clickhouse-driver`（已就绪）。
- AI 服务：FastAPI + MLflow（已落地）；RAG 复用 PG（pgvector 已编排）或关键词检索（不新增重依赖，优先轻量实现）。
- 前端：React + Ant Design Pro（admin-web，已用 ProLayout/ProTable/ProForm）。
- 验证：FastAPI TestClient 进程内 + `npx tsc --noEmit`；复用既有 `success()/PageResult/write_audit` 模式与 `verify_auth.py` 机制脚本范式。

## 实现方法

- **jwt_secret 加固**：不硬编码明文密钥，配置默认值改为 32+ 字节随机串（仅 dev 占位），`.env.example` 给出 `openssl rand -hex 32` 生成的范例，强调生产必须以环境变量覆盖；`config.py` 仅改默认值，不动 `BaseSettings` 结构。
- **admin-web 登录**：在 `src/routes` 下新增 `login` 页（角色下拉 + 调 `auth/dev-token`），`localStorage` 存 `token`/`role`；`App.tsx` 路由用 `<AuthRoute>` 包裹，读取 token，401/无 token 跳 `/login`；复用现有 `request.ts` 拦截器（已注入 token、已清 token）。保持与现有 ProLayout 菜单结构一致。
- **RAG 可解释**：在 ai-service 新增轻量检索器（优先用 PG `mt_care_plan` 历史方案 + 症状关键词匹配；若后续接 pgvector 仅替换嵌入步骤）。`plan-recommend` 在返回 `care_plan_json` 同时，根据命中的历史方案/知识片段拼装 `rationale`（引用相似案例/指南条目），避免写死占位。backend `care_plans.py` 将 `rationale` 一并落 `MtCarePlan.items_json` 或新增 `rationale` 字段透传。
- **反馈闭环**：backend 新增 `app/api/v1/plat/model_pred_logs.py`：`POST` 在 care_plans/repurchase/risk 回写成功后插入 `PlatModelPredLog`（model_id 由 ai-service 版本映射，adopted='pending'）；`PATCH /{id}/adopt` 与 `/reject` 改状态并审计。低风险、与既有 `write_audit` 同事务。
- **经营宽表**：backend 新增 `app/services/store_metrics.py` 聚合 PG `mt_treatment_record/mt_customer/mt_repurchase_prediction` 按 `store_id+date` 计算并 `INSERT` 到 ClickHouse `mt_store_metrics`；新增 `app/api/v1/mt/store-metrics.py` 查询接口（按 store/region/date 区间）。admin-web `routes/data` 用 ProTable/Statistic 渲染。Grafana dashboard JSON 落地 `infra/grafana/dashboards/store_metrics.json`。

## 实现要点（防回归）

- 复用既有 `success()`/`PageResult`/`write_audit`/`get_db`/`require_role` 范式，不新建模式；新接口同样注入鉴权依赖（store/platform 角色）。
- RAG/聚合任务均为只读或幂等写入（`INSERT` 前按 `(date,store_id)` 去重/覆盖），AI 不可用时降级（RAG 退回规则化 rationale、聚合跳过缺字段）。
- ClickHouse 写入走 `ch_client`，失败仅告警不阻断主链路；查询接口对缺数据返回空 `PageResult`。
- 验证：新增/复用机制脚本——RAG `rationale` 非占位且含命中依据、`pred_log` 落库且 adopt 改状态、ClickHouse 写入+查询成功；`import app.main` 路由数核对；`npx tsc --noEmit` 0 错误；`verify_auth.py` 复跑 9/9 且密钥告警消失。

## 架构设计

- 数据流（反馈闭环）：前端/业务路由 → 调 ai-service → 回写业务表 + 写 `plat_model_pred_log(pending)` → 运营在后台采纳/驳回 → 改 `adopted` 并审计 → 支撑模型迭代。
- 经营宽表流：PG `mt_*` → 聚合服务（按日） → ClickHouse `mt_store_metrics` → 查询接口 → admin-web 看板 / Grafana。
- 鉴权流：login(dev-token) → localStorage token → request 拦截器注入 → 后端 `require_role` 校验。

## 目录结构

```
code/
├── backend/
│   ├── app/
│   │   ├── core/config.py                         # [MODIFY] jwt_secret 默认值改为 ≥32 字节强随机串
│   │   ├── api/v1/
│   │   │   ├── auth.py                            # [已就绪] dev-token；无需改
│   │   │   ├── plat/model_pred_logs.py           # [NEW] 预测日志写入 + 采纳/驳回接口（注入鉴权）
│   │   │   ├── mt/store-metrics.py               # [NEW] ClickHouse 经营宽表查询接口（store/platform 角色）
│   │   │   ├── mt/care_plans.py                  # [MODIFY] 回写时落 plat_model_pred_log + 透传 rationale
│   │   │   ├── mt/repurchase_predictions.py       # [MODIFY] 回写时落 plat_model_pred_log
│   │   │   └── mt/risk_profiles.py               # [MODIFY] 回写时落 plat_model_pred_log
│   │   ├── services/store_metrics.py             # [NEW] PG→ClickHouse 按日聚合（幂等写入）
│   │   └── api/v1/__init__.py                    # [MODIFY] 注册 model_pred_logs、store-metrics 路由
│   └── verify_p2.py                              # [NEW] P2 机制级验证脚本（RAG/反馈/宽表）
├── ai-service/
│   └── app/
│       ├── api/plan_recommend.py                 # [MODIFY] 接轻量 RAG，rationale 返回真实命中依据
│       └── rag/retriever.py                      # [NEW] 历史方案/知识检索（关键词，可换 pgvector）
├── admin-web/
│   ├── src/
│   │   ├── routes/login/index.tsx               # [NEW] 登录页（角色选择 + dev-token）
│   │   ├── components/AuthRoute.tsx              # [NEW] 路由守卫（无 token/401 跳登录）
│   │   ├── App.tsx                              # [MODIFY] 用 AuthRoute 包裹受保护路由
│   │   └── routes/data/index.tsx                # [MODIFY] 接 store-metrics 真实渲染门店经营看板
└── infra/
    └── grafana/dashboards/store_metrics.json     # [NEW] Grafana 看板（读 mt_store_metrics）
```

admin-web 为运营/门店后台（桌面端），采用 Ant Design Pro（ProLayout/ProTable/ProForm/Statistic）。登录页简洁专业：左侧品牌区（平台名 + 双主线价值文案），右侧卡片式登录表单（角色下拉 + 「获取开发令牌」按钮，调 dev-token 后写入 localStorage 并跳首页）。看板页以 PageContainer + 行级 Statistic 卡片（到店/成交/复购/NPS）+ ProTable 趋势表，表格与卡片使用柔和阴影与悬停高亮，整体遵循既有 ProLayout 视觉风格，保持专业、克制、可读。

## Agent Extensions

### SubAgent

- **code-explorer**
- Purpose: 在生成详细实现步骤前，精确核查 ai-service RAG 接入点、PG/ClickHouse 连接配置、admin-web 现有路由与 ProLayout 结构，确保方案与现有代码模式一致。
- Expected outcome: 输出关键文件清单、现有范式与需修改的精确位置，避免方案臆测。