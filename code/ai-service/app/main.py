"""AI 服务入口（FastAPI）。"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    model_registry,
    plan_recommend,
    repurchase_prediction,
    risk_profile,
)
from app.core.config import settings
from app.core.response import success

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(repurchase_prediction.router)
app.include_router(plan_recommend.router)
app.include_router(risk_profile.router)
app.include_router(model_registry.router)


@app.get("/health")
async def health():
    return success(data={"status": "ok"}, message="healthy")
