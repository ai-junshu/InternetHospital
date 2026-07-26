"""统一响应封装（与 backend 对齐，技术架构第10.2章）。

AI 推理接口额外强制 isAssist=true（第10.3章），由 schemas/predict.py 保证。
"""
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


def _now_ts() -> int:
    return int(datetime.now(timezone.utc).timestamp())


class ApiResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: Optional[Any] = None
    timestamp: int = Field(default_factory=_now_ts)
    requestId: str = ""


def success(data: Any = None, message: str = "success", request_id: str = "") -> ApiResponse:
    return ApiResponse(code=0, message=message, data=data, requestId=request_id)


def error(message: str = "error", data: Any = None, request_id: str = "") -> ApiResponse:
    return ApiResponse(code=5000, message=message, data=data, requestId=request_id)
