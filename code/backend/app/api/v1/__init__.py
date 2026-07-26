"""v1 路由聚合（技术架构第10.2章：/api/v1/{ih,mt,plat}/...）。"""
from fastapi import APIRouter

from app.api.v1 import ih, mt, plat, auth

router = APIRouter()
router.include_router(ih.router, prefix="/ih")
router.include_router(mt.router, prefix="/mt")
router.include_router(plat.router, prefix="/plat")
router.include_router(auth.router)
