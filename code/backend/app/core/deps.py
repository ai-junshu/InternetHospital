"""依赖注入（技术架构第10.2章：JWT + RBAC 七角色）。

七角色：patient / doctor / pharmacist / store / therapist / platform / xingyao
"""
from typing import Any

from fastapi import Depends, Header, Query
from sqlalchemy import select

from app.core.errors import BusinessError, ErrorCode
from app.core.security import decode_access_token
from app.db.session import get_session
from app.models.mt_models import MtCustomer

# 七角色（第10.2章 RBAC）
ROLES = {"patient", "doctor", "pharmacist", "store", "therapist", "platform", "xingyao"}

# JWT 载荷中的门店声明键（RLS 行级隔离，第15.2章）
STORE_CLAIM = "store_id"


async def get_db():
    async for session in get_session():
        yield session


def current_user(authorization: str = Header(default="")) -> dict[str, Any]:
    if not authorization.startswith("Bearer "):
        raise BusinessError(ErrorCode.UNAUTHORIZED, "缺少合法 JWT")
    token = authorization[len("Bearer "):]
    try:
        payload = decode_access_token(token)
    except Exception:
        raise BusinessError(ErrorCode.TOKEN_EXPIRED, "令牌无效或过期")
    return payload


def require_role(*roles: str):
    def _dep(payload: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
        if payload.get("role") not in roles:
            raise BusinessError(ErrorCode.FORBIDDEN, "角色无权访问")
        return payload

    return _dep


def actor_of(payload: dict[str, Any]) -> int | None:
    """从 JWT 载荷提取数值型操作者 id（审计 actor_id 为整数列；sub 可能为字符串）。"""
    sub = payload.get("sub")
    if sub is None:
        return None
    try:
        return int(sub)
    except (TypeError, ValueError):
        return None


def store_scope(
    payload: dict[str, Any] = Depends(current_user),
    scope_store_id: int | None = Query(default=None, description="下钻门店（仅 platform/xingyao 生效）"),
) -> int | None:
    """RLS 行级隔离作用域解析（第15.2章）。

    - platform / xingyao：返回查询参数 scope_store_id（None 表示全部门店，可下钻指定门店）。
    - store / therapist：忽略查询参数，强制取 JWT 的 store_id 声明；缺失则 403（防越权）。
    - 其它角色：403。
    """
    role = payload.get("role")
    if role in ("platform", "xingyao"):
        return scope_store_id
    if role in ("store", "therapist"):
        sid = payload.get(STORE_CLAIM)
        if sid is None:
            raise BusinessError(ErrorCode.FORBIDDEN, "账号未绑定门店，无法访问门店数据")
        return int(sid)
    raise BusinessError(ErrorCode.FORBIDDEN, "角色无权访问门店数据")


def customer_ids_for_store(scope: int):
    """返回属于指定门店的客户 id 子查询（供无 store_id 的 mt_* 表经 customer_id 关联隔离）。"""
    return select(MtCustomer.id).where(
        MtCustomer.source_store_id == scope,
        MtCustomer.is_deleted.is_(False),
    )
