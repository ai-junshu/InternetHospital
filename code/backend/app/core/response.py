"""统一响应封装（技术架构第10.2章）。

格式：{ code, message, data, timestamp, requestId }
code = 0 成功，非 0 为错误码；HTTP 状态码统一 200，错误通过 code 体现。
"""
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.core.errors import ErrorCode


def _now_ts() -> int:
    return int(datetime.now(timezone.utc).timestamp())


class ApiResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: Optional[Any] = None
    timestamp: int = Field(default_factory=_now_ts)
    requestId: str = ""


def success(data: Any = None, message: str = "success", request_id: str = "") -> ApiResponse:
    return ApiResponse(
        code=ErrorCode.SUCCESS.value,
        message=message,
        data=data,
        requestId=request_id,
    )


def error(
    code: ErrorCode = ErrorCode.SYSTEM_ERROR,
    message: str = "error",
    data: Any = None,
    request_id: str = "",
) -> ApiResponse:
    return ApiResponse(
        code=code.value,
        message=message,
        data=data,
        requestId=request_id,
    )
