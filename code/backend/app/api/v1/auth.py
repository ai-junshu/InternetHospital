"""认证端点（技术架构第10.2章）。

- /auth/dev-token：开发态令牌（仅 settings.debug=True），为后台联调/测试提供各角色 JWT。
- /auth/login：后台账号密码登录（P4 安全闭环，生产路径）；启用双因子时须真校验 TOTP。
- /auth/setup-2fa、/auth/enable-2fa：双因子签发与启用（P4）。
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import current_user, get_db
from app.core.response import success
from app.core.security import (
    create_access_token,
    gen_totp_secret,
    totp_provisioning_uri,
    verify_password,
    verify_totp,
)
from app.models.plat_models import PlatAccount

router = APIRouter(prefix="/auth", tags=["auth"])

MT_ROLES = {"store", "therapist", "platform", "xingyao"}


class DevTokenIn(BaseModel):
    role: str = "platform"
    sub: str = "1"
    store_id: int | None = None  # 门店/调理师角色可绑定门店，供 RLS 行级隔离联调


@router.post("/dev-token", response_model=None)
async def dev_token(body: DevTokenIn):
    if not settings.debug:
        raise HTTPException(status_code=404, detail="not found")
    if body.role not in MT_ROLES and body.role != "patient":
        raise HTTPException(status_code=400, detail="role 不在允许范围")
    token = create_access_token(subject=body.sub, role=body.role, store_id=body.store_id)
    return success(data={"access_token": token, "token_type": "bearer", "role": body.role})


class LoginIn(BaseModel):
    username: str
    password: str
    code: Optional[str] = None  # 双因子验证码（two_factor_enabled 时必填并真校验）


@router.post("/login", response_model=None)
async def login(body: LoginIn, db: AsyncSession = Depends(get_db)):
    """后台账号密码登录（P4 安全闭环，生产路径；dev-token 仅调试态）。"""
    acc = (
        await db.scalar(
            select(PlatAccount).where(
                PlatAccount.username == body.username, PlatAccount.is_deleted.is_(False)
            )
        )
    )
    if acc is None or acc.status != "active":
        raise HTTPException(status_code=401, detail="账号或密码错误")
    if not verify_password(body.password, acc.password_hash, acc.password_salt):
        raise HTTPException(status_code=401, detail="账号或密码错误")
    # 双因子真校验（等保三级增强）：启用时须校验 TOTP 动态码
    if acc.two_factor_enabled:
        if not body.code or not verify_totp(acc.totp_secret, body.code):
            raise HTTPException(status_code=401, detail="双因子验证码错误")
    acc.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    token = create_access_token(subject=str(acc.id), role=acc.role, store_id=acc.store_id)
    return success(data={"access_token": token, "token_type": "bearer", "role": acc.role})


# ---------------- 双因子（TOTP）签发与启用（P4） ----------------

class Setup2FAOut(BaseModel):
    secret: str
    otpauth_uri: str


@router.post("/setup-2fa", response_model=None)
async def setup_2fa(payload: dict = Depends(current_user)):
    """生成临时 TOTP 密钥与 otpauth URI（不落库，待 enable 校验通过后写入）。"""
    secret = gen_totp_secret()
    uri = totp_provisioning_uri(secret, account=payload.get("sub", "admin"))
    return success(data={"secret": secret, "otpauth_uri": uri})


class Enable2FAIn(BaseModel):
    secret: str
    code: str


@router.post("/enable-2fa", response_model=None)
async def enable_2fa(
    body: Enable2FAIn,
    payload: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """校验动态码后落库密钥并启用双因子（self-service；platform/xingyao 可代管）。"""
    sub = payload.get("sub")
    role = payload.get("role")
    conds = [PlatAccount.id == int(sub), PlatAccount.is_deleted.is_(False)]
    acc = await db.scalar(select(PlatAccount).where(*conds))
    if not acc:
        raise HTTPException(status_code=404, detail="账号不存在")
    if role not in ("platform", "xingyao") and role != acc.role:
        raise HTTPException(status_code=403, detail="无权操作该账号")
    if not verify_totp(body.secret, body.code):
        raise HTTPException(status_code=400, detail="验证码错误")
    acc.totp_secret = body.secret
    acc.two_factor_enabled = True
    await db.commit()
    return success(data={"two_factor_enabled": True})
