"""验证 🔴 鉴权修复机制（不依赖数据库）。"""
import traceback
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.deps import current_user, require_role, actor_of
from app.core.security import create_access_token, decode_access_token
from app.api.v1.auth import router as auth_router
from app.core.errors import register_exception_handlers

settings.debug = True

mini = FastAPI()
mini.include_router(auth_router)
register_exception_handlers(mini)


@mini.get("/protected")
def protected(u: dict = Depends(current_user)):
    return {"ok": True, "role": u.get("role"), "sub": u.get("sub")}


@mini.get("/store-only")
def store_only(u: dict = Depends(require_role("store", "therapist", "platform", "xingyao"))):
    return {"ok": True, "role": u.get("role")}


client = TestClient(mini)
lines = []


def log(s):
    lines.append(str(s))
    print(s)


passed = failed = 0


def check(name, cond, extra=""):
    global passed, failed
    if cond:
        passed += 1
        log(f"  PASS  {name}")
    else:
        failed += 1
        log(f"  FAIL  {name}  {extra}")


try:
    # 1. 无令牌 -> 401 信封
    r = client.get("/protected")
    log(f"  [1] no-token status={r.status_code} body={r.text[:200]}")
    check("无令牌返回 401 信封", r.status_code == 200 and r.json().get("code") == 2001, r.text[:200])

    # 2. patient 令牌可解析
    tok = create_access_token(subject="7", role="patient")
    r = client.get("/protected", headers={"Authorization": f"Bearer {tok}"})
    log(f"  [2] patient status={r.status_code} body={r.text[:200]}")
    check("patient 令牌可访问", r.status_code == 200 and r.json().get("role") == "patient", r.text[:200])

    # 3. 角色越权 -> 403
    r = client.get("/store-only", headers={"Authorization": f"Bearer {tok}"})
    log(f"  [3] patient->store-only status={r.status_code} body={r.text[:200]}")
    check("patient 越权访问 store-only -> 403", r.status_code == 200 and r.json().get("code") == 2003, r.text[:200])

    # 4. dev-token 签发
    log(f"  [4] settings.debug={settings.debug}")
    r = client.post("/auth/dev-token", json={"role": "platform", "sub": "99"})
    log(f"  [4] dev-token status={r.status_code} body={r.text[:200]}")
    data = r.json().get("data") or {}
    check("dev-token 签发 platform 令牌", r.status_code == 200 and "access_token" in data, r.text[:200])
    dtok = data.get("access_token")

    if dtok:
        r = client.get("/store-only", headers={"Authorization": f"Bearer {dtok}"})
        log(f"  [4b] platform->store-only status={r.status_code} body={r.text[:200]}")
        check("platform 令牌可访问 store-only", r.status_code == 200, r.text[:200])

    # 4c. debug=False 时 dev-token 关闭
    settings.debug = False
    r = client.post("/auth/dev-token", json={"role": "platform", "sub": "1"})
    log(f"  [4c] debug=False dev-token status={r.status_code}")
    check("debug=False 时 dev-token 关闭(404)", r.status_code == 404)
    settings.debug = True

    # 5. actor_of
    check("actor_of 整数 sub -> int", actor_of({"sub": "42", "role": "store"}) == 42)
    check("actor_of 非数字 sub -> None", actor_of({"sub": "abc", "role": "patient"}) is None)
    check("actor_of 缺 sub -> None", actor_of({"role": "x"}) is None)

except Exception:
    log(traceback.format_exc())

log(f"\n结果: {passed} 通过, {failed} 失败")
with open("verify_auth_result.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("DONE")
