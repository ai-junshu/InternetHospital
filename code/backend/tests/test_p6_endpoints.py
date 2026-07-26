"""P6 后端端点补齐冒烟测试（医生排班 / 药品目录 / 调理师排班标签 / 合规采集审核）。

- 路由注册、缓存 key、Schema 序列化：无外部依赖，必跑。
- 端到端 CRUD：需可达的 Postgres；不可达时自动跳过（pytest.skip）。
"""
import asyncio
import os

import pytest
import httpx
from sqlalchemy import text

from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import SessionLocal, engine
from app.models.base import Base


# ===================== 无外部依赖：必跑 =====================
def test_p6_routes_registered():
    from app.main import app

    paths = {getattr(r, "path", "") for r in app.routes}
    expected = [
        "/api/v1/ih/schedules",
        "/api/v1/ih/schedules/{schedule_id}",
        "/api/v1/ih/drugs",
        "/api/v1/ih/drugs/{drug_id}",
        "/api/v1/mt/therapists/{therapist_id}/schedules",
        "/api/v1/mt/therapists/{therapist_id}/tags",
        "/api/v1/mt/therapist-tags",
        "/api/v1/plat/compliance/submit",
        "/api/v1/plat/compliance/{item_id}/approve",
        "/api/v1/plat/compliance/{item_id}/reject",
    ]
    for p in expected:
        assert p in paths, f"缺少路由 {p}"


def test_p6_drug_cache_key():
    from app.api.v1.ih.drugs import _drugs_cache_key

    key = _drugs_cache_key(keyword="感", otc_type="otc", category=None, status="on", page=2, page_size=20)
    assert key.startswith("drugs:")
    assert "感" in key
    assert ":2:" in key


def test_p6_schemas_serialize():
    from datetime import date, time

    from app.schemas.ih import DoctorScheduleCreate, DrugCreate
    from app.schemas.mt import TherapistScheduleCreate
    from app.schemas.plat import ComplianceSubmitIn

    assert DoctorScheduleCreate(work_date=date(2026, 8, 1), start_time=time(9, 0), end_time=time(12, 0)).am_pm == "morning"
    assert DrugCreate(name="布洛芬").otc_type == "otc"
    assert ComplianceSubmitIn(category="license", subject_type="doctor", subject_id=1, title="执业证").category == "license"
    assert TherapistScheduleCreate(therapist_id=1, work_date=date(2026, 8, 1), start_time=time(9, 0), end_time=time(12, 0)).capacity == 1


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
        # 释放连接池，避免跨 event loop 复用导致 "Event loop is closed"
        try:
            asyncio.run(engine.dispose())
        except Exception:
            pass


async def _seed(db):
    # 清理历史种子，按外键依赖顺序删除，保证可重复运行
    await db.execute(
        text("delete from ih_doctor_schedule where doctor_id in (select id from ih_doctor where user_id=:u)"),
        {"u": 991001},
    )
    await db.execute(text("delete from ih_doctor where user_id=:u"), {"u": 991001})
    await db.execute(text("delete from ih_user where id=:u"), {"u": 991001})
    await db.execute(
        text("delete from mt_therapist_tag_rel where therapist_id in (select id from mt_therapist where license_no=:l)"),
        {"l": "LT-SEED"},
    )
    await db.execute(
        text("delete from mt_therapist_schedule where therapist_id in (select id from mt_therapist where license_no=:l)"),
        {"l": "LT-SEED"},
    )
    await db.execute(text("delete from mt_therapist where license_no=:l"), {"l": "LT-SEED"})
    await db.execute(text("delete from mt_therapist_tag where name like 'SEED-TAG-%'"))
    await db.execute(text("delete from mt_store where name like 'SEED-STORE-%'"))
    await db.execute(text("delete from ih_drug where name like 'SEED-%'"))
    await db.execute(
        text(
            "delete from plat_compliance_item where subject_id in (select id from ih_doctor where user_id=:u) "
            "or submitter_id=:u"
        ),
        {"u": 991001},
    )
    await db.commit()

    from app.models.ih_models import IhDoctor, IhUser
    from app.models.mt_models import MtStore, MtTherapist

    user = IhUser(id=991001, openid="seed-openid-991001")
    db.add(user)
    await db.flush()
    doc = IhDoctor(user_id=991001, license_no="L-SEED-1", status="active")
    db.add(doc)
    await db.flush()
    store = MtStore(name=f"SEED-STORE-{os.getpid()}", region="r", status="active")
    db.add(store)
    await db.flush()
    th = MtTherapist(name="SEED-TH", license_no="LT-SEED", store_id=store.id, status="active")
    db.add(th)
    await db.flush()
    await db.commit()
    return doc.id, store.id, th.id


async def _run():
    from app.main import app

    settings.rate_limit_enabled = False
    await engine.dispose()  # 清除上一事件循环遗留的连接池
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as db:
        doc_id, store_id, th_id = await _seed(db)

    doctor_token = create_access_token("991001", "doctor")
    platform_token = create_access_token("1", "platform")
    patient_token = create_access_token("2", "patient")
    store_token = create_access_token("3", "store", store_id=store_id)
    H = lambda t: {"Authorization": f"Bearer {t}"}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # ---- 药品目录 ----
        r = await client.post(
            "/api/v1/ih/drugs",
            json={"name": "SEED-布洛芬", "otc_type": "otc", "price": 1000},
            headers=H(platform_token),
        )
        assert r.status_code == 200, r.text
        r = await client.get("/api/v1/ih/drugs?keyword=SEED", headers=H(platform_token))
        assert r.status_code == 200
        assert r.json()["data"]["total"] >= 1

        # ---- 合规采集审核 ----
        r = await client.post(
            "/api/v1/plat/compliance/submit",
            json={"category": "license", "subject_type": "doctor", "subject_id": doc_id, "title": "执业证"},
            headers=H(patient_token),
        )
        assert r.status_code == 200, r.text
        item_id = r.json()["data"]["id"]
        r = await client.get("/api/v1/plat/compliance", headers=H(patient_token))
        assert r.status_code == 200
        r = await client.post(f"/api/v1/plat/compliance/{item_id}/approve", json={}, headers=H(platform_token))
        assert r.status_code == 200, r.text
        assert r.json()["data"]["status"] == "approved"

        # ---- 医生排班 ----
        r = await client.post(
            "/api/v1/ih/schedules",
            json={"work_date": "2026-08-01", "start_time": "09:00", "end_time": "12:00", "capacity": 2},
            headers=H(doctor_token),
        )
        assert r.status_code == 200, r.text
        r = await client.get("/api/v1/ih/schedules", headers=H(doctor_token))
        assert r.status_code == 200

        # ---- 调理师排班 + 标签 ----
        r = await client.post(
            f"/api/v1/mt/therapists/{th_id}/schedules",
            json={"work_date": "2026-08-01", "start_time": "09:00", "end_time": "12:00"},
            headers=H(store_token),
        )
        assert r.status_code == 200, r.text
        r = await client.get(f"/api/v1/mt/therapists/{th_id}/schedules", headers=H(store_token))
        assert r.status_code == 200

        r = await client.post(
            "/api/v1/mt/therapist-tags",
            json={"name": f"SEED-TAG-{os.getpid()}", "category": "skill"},
            headers=H(platform_token),
        )
        assert r.status_code == 200, r.text
        tag_id = r.json()["data"]["id"]
        r = await client.post(f"/api/v1/mt/therapists/{th_id}/tags", json={"tag_id": tag_id}, headers=H(store_token))
        assert r.status_code == 200, r.text
        r = await client.get(f"/api/v1/mt/therapists/{th_id}/tags", headers=H(store_token))
        assert r.status_code == 200
        assert r.json()["data"][0]["tag_id"] == tag_id


@pytest.mark.skipif(not _db_available(), reason="需要可达的 Postgres")
def test_p6_crud_e2e():
    asyncio.run(_run())
