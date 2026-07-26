"""审计中间件（技术架构第10.2/13章全量审计留痕，P4 真落地）。

对 /api/v1 下的写操作，解析 JWT 取 actor_id/role，best-effort 写 plat_audit_log
（独立会话，不阻塞主流程、不记录敏感 body 明文）。与 services.audit.write_audit
共用哈希链算法，审计记录同样具备防篡改能力。
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.services.audit import write_audit

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.method in WRITE_METHODS and request.url.path.startswith("/api/v1"):
            await self._audit(request, response.status_code)
        return response

    async def _audit(self, request: Request, status_code: int) -> None:
        try:
            auth = request.headers.get("Authorization", "")
            role = None
            actor_id = None
            if auth.startswith("Bearer "):
                try:
                    payload = decode_access_token(auth[7:])
                    sub = payload.get("sub")
                    actor_id = int(sub) if sub is not None else None
                    role = payload.get("role")
                except Exception:
                    pass
            ip = request.client.host if request.client else None
            async with SessionLocal() as db:
                await write_audit(
                    db,
                    action=request.method,
                    resource=request.url.path,
                    role=role,
                    actor_id=actor_id,
                    ip=ip,
                    after={"status_code": status_code},
                )
                await db.commit()
        except Exception:
            # 审计失败不影响主业务流程
            pass
