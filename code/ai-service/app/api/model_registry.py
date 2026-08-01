"""模型注册表状态/健康端点（MLflow registry 接入透明化）。

- GET /models/registry ：列出注册表中各模型版本/可达性（运营可观测）。
- GET /models/health  ：服务与 registry 整体可达性探活。
"""
from fastapi import APIRouter

from app.core.config import settings
from app.core.response import success
from app.ml.model_loader import list_registry

router = APIRouter(prefix="/models", tags=["模型注册表"])


@router.get("/registry", response_model=None)
async def registry():
    return success(
        data={
            "tracking_uri": settings.mlflow_tracking_uri,
            "registry_stage": settings.model_registry_stage,
            "models": list_registry(),
        }
    )


@router.get("/health", response_model=None)
async def health():
    models = list_registry()
    loaded = sum(1 for m in models if m.get("available"))
    return success(
        data={
            "status": "ok" if loaded > 0 else "degraded",
            "registry_reachable": any(m.get("available") for m in models),
            "available_models": loaded,
            "total_models": len(models),
        },
        message="AI 服务存活（模型加载按需，registry 不可达时降级）",
    )
