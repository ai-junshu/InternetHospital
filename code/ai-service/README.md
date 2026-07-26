# ai-service · AI 推理服务（FastAPI + MLflow）

> 平台 AI 能力服务化：复购预测 / 方案推荐 / 风险画像。所有推理响应强制携带 `isAssist=true`（仅供参考，不替代医师诊断，技术架构第10.3章）。

## 本地启动

```powershell
pip install -e .
uvicorn app.main:app --reload --port 8001
```

- OpenAPI：http://localhost:8001/docs
- 健康检查：http://localhost:8001/health

## 接口（骨架）

| 方法 | 路径 | 说明 |
| ---- | ---- | ---- |
| POST | /plan-recommend | 调理方案推荐（结合 RAG 可解释输出，第10.3章） |
| GET  | /repurchase-prediction | 客户复购/复诊概率预测（第15.4章反馈闭环数据来源） |
| GET  | /risk-profile | 健康风险画像 |

## 目录结构
```
app/
├── main.py              # 入口
├── core/                # config / response
├── api/                 # 三个推理接口占位
├── ml/                  # model_loader(MLflow) / feature_store 占位
└── schemas/predict.py   # 强制 isAssist 字段
```
