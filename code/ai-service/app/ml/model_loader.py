"""MLflow 模型加载（技术架构第6章：模型注册/版本管理）。

从 MLflow 注册表按 stage（默认 Production）加载模型，并缓存避免重复拉取。
提供 list_registry() 用于运营/健康端点查询各模型版本与可达性。
"""
import mlflow
from mlflow.tracking import MlflowClient

from app.core.config import settings

_CACHE: dict[str, tuple] = {}

# 平台已接入注册表的模型名（与训练脚本 register 的 name 一一对应）
REGISTERED_MODELS = ("risk_profile", "plan_recommend", "repurchase_prediction")


def load_model(name: str):
    """从 MLflow 注册表加载模型，返回 (pyfunc_model, version)。"""
    if name in _CACHE:
        return _CACHE[name]
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    model = mlflow.pyfunc.load_model(
        f"models:/{name}/{settings.model_registry_stage}"
    )
    client = MlflowClient(tracking_uri=settings.mlflow_tracking_uri)
    # 取注册表中该模型的最新版本（stage 已废弃，按版本号取最新）
    versions = client.search_model_versions(f"name='{name}'")
    version = str(versions[0].version) if versions else "unknown"
    _CACHE[name] = (model, version)
    return _CACHE[name]


def list_registry() -> list[dict]:
    """枚举注册表中各模型的版本/可达性（不触发实际模型加载，仅查元数据）。"""
    try:
        client = MlflowClient(tracking_uri=settings.mlflow_tracking_uri)
    except Exception as e:  # tracking uri 不可达等
        return [
            {"name": m, "stage": settings.model_registry_stage,
             "available": False, "detail": str(e)}
            for m in REGISTERED_MODELS
        ]
    result = []
    for m in REGISTERED_MODELS:
        try:
            versions = client.search_model_versions(f"name='{m}'")
            if versions:
                v = versions[0]
                result.append({
                    "name": m,
                    "stage": settings.model_registry_stage,
                    "version": v.version,
                    "status": v.status,
                    "available": True,
                })
            else:
                result.append({
                    "name": m,
                    "stage": settings.model_registry_stage,
                    "version": None,
                    "status": "NOT_FOUND",
                    "available": False,
                    "detail": "注册表中无该模型版本",
                })
        except Exception as e:
            result.append({
                "name": m,
                "stage": settings.model_registry_stage,
                "available": False,
                "detail": str(e),
            })
    return result
