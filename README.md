# 互联网医疗中心平台

> 双主线架构的互联网医疗与健康数据平台：**互联网医院**（2C 在线复诊 + 电子处方 + 药品销售）+ **健康数据中台**（B2B2C 连锁门店赋能）。依托"合规大脑 + 医疗 AI 数据中台"能力，以连续、结构化的治疗效果数据为核心壁垒，聚焦疼痛管理 / 调理领域。

---

## 一、项目定位

| 主线 | 面向对象 | 核心能力 |
| --- | --- | --- |
| 互联网医院（IH） | 患者 / 亚健康人群、执业医师、医院管理员 | 在线复诊、电子处方与药师审核、药品目录与销售、医生排班 |
| 健康数据中台（MT） | 连锁门店管理员、调理师 / 健康顾问 | 客户授权、疼痛评估、调理方案、治疗记录、复购与风险画像、经营看板 |
| 平台运营（PLAT） | 平台运营、星耀产业资本 / 数据中台运营 | 审计日志、AI 模型目录、数据资产目录、合规采集审核、行级隔离治理 |

> 详细产品定义见《互联网医疗中心平台产品需求文档（PRD V2.0）》，技术方案见《互联网医疗中心平台技术架构设计方案》。

---

## 二、技术栈

- **后端**：Python 3.11 · FastAPI · SQLAlchemy 2.0（异步）· Alembic
- **AI 服务**：FastAPI · MLflow · scikit-learn / XGBoost / PyTorch · LangChain/RAG
- **数据库**：PostgreSQL(+pgvector) · Redis · MongoDB · ClickHouse(OLAP) · MinIO
- **前端**：Taro 3 + React + TS（小程序）· React + Vite + Ant Design Pro（后台）· ECharts（看板）
- **基础设施**：Docker Compose（本地）· K8s / Helm（生产骨架）· Prometheus + Grafana + Jaeger（可观测）
- **安全合规**：JWT + RBAC 六角色 + 行级隔离(RLS) · TOTP 双因子 · 审计日志 SHA-256 哈希链 · 面向等保三级

---

## 三、仓库结构

```
互联网医疗中心平台/
├── code/
│   ├── backend/       # 业务后端 FastAPI（ih / mt / plat 三模块，JWT+RBAC+RLS+审计）
│   ├── ai-service/    # AI 推理服务（方案推荐 / 复购预测 / 风险画像 + RAG 可解释）
│   ├── admin-web/     # 运营后台 React + AntD Pro（客户/复购/风险/看板/平台治理）
│   ├── mp-taro/       # Taro 小程序（患者端 / 医生端：排班、开方选药、药品目录）
│   └── infra/         # 基础设施：docker-compose / k8s-helm / nginx / 备份脚本
├── 互联网医疗中心平台产品需求文档（PRD V2.0）.md / .docx
├── 互联网医疗中心平台技术架构设计方案.md / .docx
├── 互联网医疗中心平台工程进度.md / .docx        # 面向负责人的进度报告
├── 等保三级测评与执业许可材料清单.md / .docx
├── 合规清单与等保三级准备工作.md / .docx
└── 互联网医疗中心平台整体进度与下一步计划.md / .docx
```

各子模块另有独立 README：`code/backend/README.md`、`code/ai-service/README.md`、`code/infra/README.md`。

---

## 四、快速开始（本地开发）

### 1. 启动基础依赖

```powershell
cd code/infra
copy .env.example .env      # 按需修改连接串/端口
docker compose up -d        # 启动 PG / Redis / Mongo / ClickHouse / MinIO / 可观测组件
docker compose ps
```

### 2. 启动业务后端

```powershell
cd code/backend
pip install -e .
alembic upgrade head        # 初始化 ih_/mt_/plat_ 表结构
python -m app.seed          # （可选）灌入种子数据
uvicorn app.main:app --reload --port 8000
```
- OpenAPI 文档：http://localhost:8000/docs ｜ 健康检查：http://localhost:8000/health

### 3. 启动 AI 服务

```powershell
cd code/ai-service
pip install -e .
uvicorn app.main:app --reload --port 8001
```
- OpenAPI 文档：http://localhost:8001/docs

### 4. 启动前端

```powershell
# 运营后台
cd code/admin-web && npm install && npm run dev      # http://localhost:3000

# 小程序
cd code/mp-taro && npm install && npm run dev:weapp   # 微信开发者工具导入 dist
```

> 本地端口与依赖清单详见 `code/infra/README.md`。

---

## 五、项目状态（截至 2026-07-26）

| 维度 | 结论 |
| --- | --- |
| 后端地基（P0–P3） | ✅ 已落地并机制级验证 **21/21 PASS** |
| AI 服务 | ✅ 三接口真实推理 + RAG 可解释，最成熟 |
| 前端 P6 缺口接通 | ✅ 医生排班 / 调理师排班标签 / 药品目录 / 合规审核已接真实接口（admin-web build 通过、mp-taro 类型检查通过） |
| 上线就绪度 | ⚠️ **未就绪**：缺等保三级正式测评 + 执业许可（硬门槛）+ 运行时端到端验证 + 真实第三方对接 |

完整进度、未完成项、下一步里程碑与需协调事项，见 [`互联网医疗中心平台工程进度.md`](./互联网医疗中心平台工程进度.md)。

---

## 六、合规说明

本平台面向 **等保三级** 与 **互联网医院 / 药品经营执业许可** 设计。技术侧已落地双因子认证、RBAC/RLS、审计哈希链等控制项；正式测评备案、卫健委审批与许可证申办需由公司层面组织推进（详见等保三级测评与执业许可材料清单）。

> ⚠️ 医疗数据涉及个人敏感信息，请勿在本仓库提交任何真实患者数据、密钥或 `.env` 生产配置。

---

## 七、分支模型

`main`（生产）/ `release/*`（预发）/ `develop`（集成）/ `feature/*`（开发）。
