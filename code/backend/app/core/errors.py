"""错误码与全局异常处理（技术架构第10.2章错误码分段）。

1xxx 参数校验 / 2xxx 鉴权权限 / 3xxx 业务规则 / 4xxx 合规拦截 / 5xxx 系统异常。
禁止在业务代码中硬编码魔法数字，统一引用 ErrorCode 枚举。
"""
from enum import IntEnum
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ErrorCode(IntEnum):
    SUCCESS = 0

    # 1xxx 参数校验
    PARAM_INVALID = 1001
    PARAM_MISSING = 1002

    # 2xxx 鉴权 / 权限
    UNAUTHORIZED = 2001
    TOKEN_EXPIRED = 2002
    FORBIDDEN = 2003

    # 3xxx 业务规则
    PRESCRIPTION_PENDING = 3001
    RESOURCE_NOT_FOUND = 3004

    # 4xxx 合规拦截
    COMPLIANCE_BLOCKED = 4001
    RATE_LIMITED = 4002

    # 5xxx 系统异常
    SYSTEM_ERROR = 5000


class BusinessError(Exception):
    """业务异常，由全局处理器转为统一响应。"""

    def __init__(
        self,
        code: ErrorCode = ErrorCode.SYSTEM_ERROR,
        message: str = "error",
        data: Any = None,
    ) -> None:
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)


def _req_id(req: Request) -> str:
    return getattr(req.state, "request_id", "")


def _safe_jsonable(obj: Any, _depth: int = 0) -> Any:
    """将任意对象转为可 JSON 序列化结构。

    用于异常处理器喂给 ApiResponse 的 data 字段。FastAPI 的
    RequestValidationError.errors() 可能包含 bytes（如上传文件 input），
    直接 model_dump() 会抛 TypeError 触发 5000 假异常；这里递归收敛。
    """
    if _depth > 8:
        return str(obj)
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, bytes):
        return obj.decode("utf-8", "replace")
    if isinstance(obj, dict):
        return {str(k): _safe_jsonable(v, _depth + 1) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_safe_jsonable(v, _depth + 1) for v in obj]
    return str(obj)


def register_exception_handlers(app) -> None:
    from app.core.response import error

    @app.exception_handler(BusinessError)
    async def _biz(req: Request, exc: BusinessError):
        return JSONResponse(
            status_code=200,
            content=error(exc.code, exc.message, _safe_jsonable(exc.data), _req_id(req)).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def _val(req: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=200,
            content=error(ErrorCode.PARAM_INVALID, "参数校验失败", _safe_jsonable(exc.errors()), _req_id(req)).model_dump(),
        )

    @app.exception_handler(Exception)
    async def _sys(req: Request, exc: Exception):
        # 兜底：即便 exc 不可序列化也收敛为字符串，杜绝 5000 假异常死循环。
        detail = _safe_jsonable({"type": type(exc).__name__, "msg": str(exc)})
        return JSONResponse(
            status_code=200,
            content=error(ErrorCode.SYSTEM_ERROR, "系统异常", detail, _req_id(req)).model_dump(),
        )
