"""健康数据中台模块路由聚合。"""
from fastapi import APIRouter

from app.api.v1.mt import (
    care_plans,
    customers,
    pain_assessment,
    repurchase_predictions,
    risk_profiles,
    scheduling,
    store_metrics,
    stores,
    treatment_records,
)

router = APIRouter()
router.include_router(customers.router)
router.include_router(pain_assessment.router)
router.include_router(care_plans.router)
router.include_router(treatment_records.router)
router.include_router(repurchase_predictions.router)
router.include_router(risk_profiles.router)
router.include_router(stores.router)
router.include_router(store_metrics.router)
router.include_router(scheduling.schedule_router)
router.include_router(scheduling.tag_router)
