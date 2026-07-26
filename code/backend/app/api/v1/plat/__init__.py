"""平台模块路由聚合。"""
from fastapi import APIRouter

from app.api.v1.plat import ai_models, audit_logs, compliance, data_assets, model_pred_logs

router = APIRouter()
router.include_router(data_assets.router)
router.include_router(ai_models.router)
router.include_router(audit_logs.router)
router.include_router(model_pred_logs.router)
router.include_router(compliance.router)
