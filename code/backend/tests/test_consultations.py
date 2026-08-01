"""迭代C 在线复诊会话加固点测试（双端结束 / 2003 越权 / 归属过滤）。

- 路由注册、Schema：无外部依赖，必跑。
- 端到端 CRUD（创建→归属过滤→越权→双端结束）：需可达的 Postgres；不可达时自动跳过。
复用 test_p6_endpoints.py 的 _db_available / httpx.ASGITransport / create_access_token 模式。
"""
import asyncio

import httpx
import pytest
from sqlalchemy import text

from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import SessionLocal, engine
from app.models.base import Base


# ===================== 无外部依赖：必跑 =====================
def test_consultation_routes_registered():
    from app.main import app

    paths = {getattr(r, "path", "") for r in app.routes}
    for p in [
        "/api/v1/ih/consultations",
        "/api/v1/ih/consultations/{consultation_id}",
        "/api/v1/ih/consultations/{consultation_id}/start",
        "/api/v1/ih/consultations/{consultation_id}/end",
    ]:
        assert p in paths, f"缺少路由 {p}"


def test_end_consultation_no_query_params():
    """回归：end 端点不应再接受 doctor_id/patient_id 查询参数（越权绕过已修复）。"""
    from app.main import app
    from app.api.v1.ih import consultations as cmod

    sig = cmod.end_consultation
    import inspect

    params = inspect.signature(sig).parameters
    assert "doctor_id" not in params, "end_consultation 仍暴露 doctor_id 查询参数，存在越权绕过"
    assert "patient_id" not in params, "end_consultation 仍暴露 patient_id 查询参数，存在越权绕过"


# ===================== 端到端（需 Postgres） =====================
def _db_available() -> bool:
    try:

        async def _c():
            async with engine.connect() as conn:
                await conn.execute(text("select 1"))

        asyncio.run(_c())
        return True
    except Exception:
        return False
    finally:
        try:
            asyncio.run(engine.dispose())
        except Exception:
            pass


async def _seed(db):
    # 清理历史种子，按外键依赖顺序删除，保证可重复运行
    await db.execute(text("delete from ih_consultation where patient_id=:u"), {"u": 992001})
    await db.execute(text("delete from ih_consultation where doctor_id in (select id from ih_doctor where user_id=:u)"), {"u": 992002})
    await db.execute(text("delete from ih_doctor where user_id=:u"), {"u": 992002})
    await db.execute(text("delete from ih_user where id in (:p, :d)"), {"p": 992001, "d": 992002})
    await db.commit()

    from app.models.ih_models import IhDoctor, IhUser

    patient = IhUser(id=992001, openid="seed-conv-patient")
    doctor_user = IhUser(id=992002, openid="seed-conv-doctor")
    db.add_all([patient, doctor_user])
    await db.flush()
    doc = IhDoctor(user_id=992002, license_no="L-CONV-SEED", status="active")
    db.add(doc)
    await db.flush()
    await db.commit()
    return 992001, doc.id


async def _create_consultation(client, token, patient_id, doctor_id):
    H = lambda t: {"Authorization": f"Bearer {t}"}
    r = await client.post(
        "/api/v1/ih/consultations",
        json={"patient_id": patient_id, "doctor_id": doctor_id, "chief_complaint": "SEED-复诊"},
        headers=H(token),
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]["id"]


async def _run():
    from app.main import app

    settings.rate_limit_enabled = False
    await engine.dispose()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as db:
        patient_id, doctor_id = await _seed(db)

    patient_token = create_access_token(str(patient_id), "patient")
    doctor_token = create_access_token(str(doctor_id), "doctor")
    other_patient_token = create_access_token("992099", "patient")
    other_doctor_token = create_access_token("992088", "doctor")
    platform_token = create_access_token("1", "platform")
    H = lambda t: {"Authorization": f"Bearer {t}"}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        cid = await _create_consultation(client, platform_token, patient_id, doctor_id)

        # ---- 归属过滤：患者列表仅见本人会话 ----
        r = await client.get("/api/v1/ih/consultations", headers=H(patient_token))
        assert r.status_code == 200, r.text
        rows = r.json()["data"]["items"]
        assert any(it["id"] == cid for it in rows)
        r = await client.get("/api/v1/ih/consultations", headers=H(other_patient_token))
        assert r.status_code == 200
        assert all(it["id"] != cid for it in r.json()["data"]["items"])

        # ---- 越权读取：非本人会话返回 2003 FORBIDDEN ----
        r = await client.get(f"/api/v1/ih/consultations/{cid}", headers=H(other_patient_token))
        assert r.status_code == 200  # 外层 200，业务码在 data.code
        assert r.json()["code"] == 2003, r.text
        r = await client.get(f"/api/v1/ih/consultations/{cid}", headers=H(other_doctor_token))
        assert r.json()["code"] == 2003, r.text
        # 本人可读
        r = await client.get(f"/api/v1/ih/consultations/{cid}", headers=H(patient_token))
        assert r.json()["code"] == 0, r.text

        # ---- 双端结束：仅本人可结束 ----
        # 医师先接诊
        r = await client.patch(f"/api/v1/ih/consultations/{cid}/start?doctor_id={doctor_id}", headers=H(doctor_token))
        assert r.status_code == 200, r.text
        assert r.json()["data"]["status"] == "ongoing"

        # 其他患者尝试结束 -> 2003
        r = await client.patch(f"/api/v1/ih/consultations/{cid}/end", headers=H(other_patient_token))
        assert r.json()["code"] == 2003, r.text
        # 其他医师尝试结束 -> 2003
        r = await client.patch(f"/api/v1/ih/consultations/{cid}/end", headers=H(other_doctor_token))
        assert r.json()["code"] == 2003, r.text
        # 患者本人可结束
        r = await client.patch(f"/api/v1/ih/consultations/{cid}/end", headers=H(patient_token))
        assert r.json()["code"] == 0, r.text
        assert r.json()["data"]["status"] == "ended"
        # 结束后再结束 -> PARAM_INVALID
        r = await client.patch(f"/api/v1/ih/consultations/{cid}/end", headers=H(patient_token))
        assert r.json()["code"] != 0, r.text


@pytest.mark.skipif(not _db_available(), reason="需要可达的 Postgres")
def test_consultation_e2e():
    asyncio.run(_run())
