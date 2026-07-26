"""MLflow 模型加载（技术架构第6章：模型注册/版本管理）。

从 MLflow 注册表按 stage（默认 Production）加载模型，并缓存避免重复拉取。
"""
import mlflow
from mlflow.tracking import MlflowClient

from app.core.config import settings

_CACHE: dict[str, tuple] = {}


def load_model(name: str):
    """从 MLflow 注册表加载模型，返回 (pyfunc_model, version)。"""
    if name in _CACHE:
        return _CACHE[name]
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    model = mlflow.pyfunc.load_model(
        f"models:/{name}/{settings.model_registry_stage}"
    )
    client = MlflowClient(tracking_uri=settings.mlflow_tracking_uri)
    versions = client.get_latest_versions(
        name, stages=[settings.model_registry_stage]
    )
    version = str(versions[0].version) if versions else "unknown"
    _CACHE[name] = (model, version)
    return _CACHE[name]
