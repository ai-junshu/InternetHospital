"""互联网医院用户：微信登录签发 JWT + 用户管理（技术架构第10.2章）。"""
import httpx

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import current_user
from app.core.errors import BusinessError, ErrorCode
from app.core.response import success
from app.core.cache import cached, build_key, cache_delete
from app.core.security import create_access_token
from app.core.deps import get_db
from app.models.ih_models import IhUser
from app.schemas.ih import TokenOut, UserCreate, UserLoginWxIn, UserOut
from app.services.audit import write_audit

router = APIRouter(prefix="/users", tags=["ih-用户"])


async def _wx_code2session(code: str) -> str:
    """微信 code2session；未配置 appid/secret 时走开发模式。"""
    if not settings.wx_appid or not settings.wx_secret:
        return f"dev_{code}"
    url = "https://api.weixin.qq.com/sns/jscode2session"
    params = {
        "appid": settings.wx_appid,
        "secret": settings.wx_secret,
        "js_code": code,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(url, params=params)
        data = resp.json()
        if "openid" not in data:
            raise BusinessError(ErrorCode.SYSTEM_ERROR, "微信登录失败")
        return data["openid"]


@router.post("/login/wx", response_model=None)
async def login_wx(
    body: UserLoginWxIn, request: Request, db: AsyncSession = Depends(get_db)
):
    openid = await _wx_code2session(body.code)
    result = await db.execute(select(IhUser).where(IhUser.openid == openid))
    user = result.scalar_one_or_none()
    if user is None:
        user = IhUser(
            openid=openid,
            phone_mask=body.phone_mask,
            real_name_mask=body.real_name_mask,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        await write_audit(
            db,
            action="user.register",
            resource="ih_user",
            actor_id=user.id,
            role="patient",
            after={"openid": openid},
            ip=request.client.host if request.client else None,
        )
    token = create_access_token(subject=str(user.id), role="patient")
    return success(data=TokenOut(access_token=token, user=UserOut.model_validate(user)))


@router.post("", response_model=None)
async def create_user(
    body: UserCreate, request: Request, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(IhUser).where(IhUser.openid == body.openid))
    if result.scalar_one_or_none():
        raise BusinessError(ErrorCode.PARAM_INVALID, "openid 已存在")
    user = IhUser(
        openid=body.openid,
        phone_mask=body.phone_mask,
        real_name_mask=body.real_name_mask,
        id_card_mask=body.id_card_mask,
        user_type=body.user_type,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    await write_audit(
        db,
        action="user.create",
        resource="ih_user",
        actor_id=user.id,
        role="patient",
        after=UserOut.model_validate(user).model_dump(mode="json"),
        ip=request.client.host if request.client else None,
    )
    return success(data=UserOut.model_validate(user))


@router.get("", response_model=None)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _auth: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.schemas.common import PageResult

    conds = [IhUser.is_deleted.is_(False)]
    stmt = select(IhUser)
    if conds:
        stmt = stmt.where(*conds)
    total = await db.scalar(select(func.count()).select_from(IhUser).where(*conds)) or 0
    rows = (
        await db.execute(
            stmt.order_by(IhUser.id.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    ).scalars().all()
    return success(
        data=PageResult(
            total=total,
            page=page,
            page_size=page_size,
            items=[UserOut.model_validate(r) for r in rows],
        )
    )


@router.get("/me", response_model=None)
@cached(ttl=settings.cache_default_ttl, key_builder=lambda user: f"me:{user.get('sub')}")
async def get_me(user: dict = Depends(current_user)):
    """获取当前用户资料（P4 脱敏）。经 Redis 缓存（per-user，key=me:{sub}）。"""
    return success(data={"user_id": user.get("sub"), "role": user.get("role")})


@router.get("/{user_id}", response_model=None)
async def get_user(user_id: int, _auth: dict = Depends(current_user), db: AsyncSession = Depends(get_db)):
    user = await db.get(IhUser, user_id)
    if not user or user.is_deleted:
        raise BusinessError(ErrorCode.RESOURCE_NOT_FOUND, "用户不存在")
    return success(data=UserOut.model_validate(user))
