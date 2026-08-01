"""互联网医院模块路由聚合。"""
from fastapi import APIRouter

from app.api.v1.ih import (
    complaints,
    consultations,
    dashboards,
    departments,
    doctors,
    drug_stocks,
    drugs,
    orders,
    pharmacies,
    prescriptions,
    schedules,
    users,
)

router = APIRouter()
router.include_router(users.router)
router.include_router(doctors.router)
router.include_router(prescriptions.router)
router.include_router(orders.router)
router.include_router(consultations.router)
router.include_router(schedules.router)
router.include_router(drugs.router)
router.include_router(pharmacies.router)
router.include_router(drug_stocks.router)
router.include_router(complaints.router)
router.include_router(dashboards.router)
router.include_router(departments.router)
