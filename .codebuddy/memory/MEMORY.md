# 互联网医疗中心平台 - 项目长期记忆

## 项目概述
- 互联网医疗中心平台，双主线架构：互联网医院（2C在线复诊+电子处方+药品销售）+ 健康数据中台（B2B2C连锁门店赋能）
- 依托星耀产业资本健康产业赋能服务投资平台的"合规大脑+医疗AI数据中台"能力
- 数据资产（连续、结构化的治疗效果数据）作为核心壁垒，支撑第二阶段融资估值
- 聚焦疼痛管理/调理领域

## 文档版本
- PRD V1.0 (2023-10-27): 初始版本，纯2C在线问诊，4类目标用户
- PRD V2.0 (2026-07-24): 双主线重构，7类目标用户，新增健康数据中台四大模块
- 技术架构设计方案 (2026-07-25): 独立文档 + PRD V2.0 第6章；推荐 Python(FastAPI)+PostgreSQL+MongoDB+Redis+ClickHouse+pgvector/Milvus+ES+数据湖Iceberg，前端 Taro小程序 + React/Ant Design Pro 后台 + ECharts 看板

## 目标用户体系（V2.0，7类）
- 互联网医院主线：患者/亚健康人群(2C)、执业医师(2B)、医院管理员(2B)
- 健康数据中台主线：连锁门店管理员(2B)、调理师/健康顾问(2B)
- 平台运营：平台运营管理员(2G)、星耀产业资本/数据中台运营(2G)

## 技术栈与工具
- 文档：Markdown 编写；.docx 用 **pandoc** 生成（--toc --toc-depth=3/4），比 docx-js 更稳
- 前端：Taro(React) 小程序 / React+Ant Design Pro 后台 / ECharts+DataV 看板 / 若依RuoYi 低代码
- 后端：Python FastAPI(主) + Node.js NestJS(辅) + Go Gin(兜底)；AI 同 Python 栈
- 数据库：PostgreSQL(JSONB)+MongoDB+Redis+ClickHouse(OLAP)+pgvector/Milvus(向量)+Elasticsearch(搜索)+Iceberg数据湖
- AI 工具链：pandas/PySpark + scikit-learn/XGBoost/PyTorch + MLflow/DVC + LangChain/LlamaIndex(RAG) + PaddleOCR
- 部署：Docker + K8s + 等保三级
- pandoc 可用（v1.19.2.1），用于 md→docx 验证与生成
- Node v24.14.0；docx-js 曾全局安装（C:\Users\Lenovo\AppData\Roaming\npm\node_modules）

## 用户偏好
- 【2026-07-26 更新，覆盖旧约定】文档默认**只输出 .md 格式**；除非特殊需要，需先向用户确认后才生成 .docx 或其他格式。（旧约定"md 与 docx 同步"已废止）
- 技术选型倾向：快速开发 + AI 贴合 + 开源可控 + 合规等保三级

## 工作区路径
- c:\Users\Lenovo\Desktop\互联网医疗中心平台\
- PRD 文件：互联网医疗中心平台产品需求文档（PRD V2.0）.md / .docx
- 技术架构：互联网医疗中心平台技术架构设计方案.md / .docx
