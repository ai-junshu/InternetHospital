"""健康数据中台 P0 三条合规强规则测试。

规则1 方案关联医师ID强制；规则2 治疗记录留痕更正；规则3 效果四档判定。
DB 不可达时端到端用例自动 skip；路由注册/字段必填等无依赖用例必跑。
复用 test_consultations.py 的 ASGI + token + skip 模式。
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
def test_effect_tracking_route_registered():
    from app.main import app

    paths = {getattr(r, "path", "") for r in app.routes}
    assert any(p == "/api/v1/mt/effect-tracking" for p in paths), "缺少效果判定路由"


def test_care_plan_requires_doctor_advice_id():
    """规则1：CarePlanCreate 必须包含 doctor_advice_id（必填，杜绝空关联）。"""
    from app.schemas.mt import CarePlanCreate

    import pydantic

    with pytest.raises(pydantic.ValidationError):
        CarePlanCreate(customer_id=1, created_by=2)  # 不传 doctor_advice_id 应报错
    ok = CarePlanCreate(customer_id=1, created_by=2, doctor_advice_id=99)
    assert ok.doctor_advice_id == 99


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
    await db.execute(text("delete from mt_treatment_record_revision where record_id in (select id from mt_treatment_record where customer_id=:c)"), {"c": 993001})
    await db.execute(text("delete from mt_effect_tracking where customer_id=:c"), {"c": 993001})
    await db.execute(text("delete from mt_care_plan where customer_id=:c"), {"c": 993001})
    await db.execute(text("delete from mt_treatment_record where customer_id=:c"), {"c": 993001})
    await db.execute(text("delete from mt_customer where id=:c"), {"c": 993001})
    await db.execute(text("delete from mt_store where id=:s"), {"s": 993010})
    await db.commit()

    from app.models.mt_models import MtCustomer, MtStore

    store = MtStore(id=993010, name="SEED门店", region="华东", city="上海", type="direct", status="active")
    cust = MtCustomer(id=993001, source_store_id=993010, auth_status="authorized")
    db.add_all([store, cust])
    await db.commit()
    return 993001, 993010


async def _run():
    from app.main import app

    settings.rate_limit_enabled = False
    await engine.dispose()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as db:
        customer_id, store_id = await _seed(db)

    store_token = create_access_token("993010", "store", store_id=993010)
    platform_token = create_access_token("1", "platform")
    H = lambda t: {"Authorization": f"Bearer {t}"}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # ---- 规则1：方案必须关联医师ID ----
        r = await client.post(
            "/api/v1/mt/care-plans",
            json={"customer_id": customer_id, "created_by": 993010},  # 缺少 doctor_advice_id
            headers=H(store_token),
        )
        # 外层 200，业务码 PARAM_INVALID(1001) 或参数校验失败
        assert r.json()["code"] != 0, f"缺少医师建议ID应被拒: {r.text}"

        r = await client.post(
            "/api/v1/mt/care-plans",
            json={"customer_id": customer_id, "created_by": 993010, "doctor_advice_id": 881001},
            headers=H(store_token),
        )
        assert r.json()["code"] == 0, r.text
        plan = r.json()["data"]
        assert plan["doctor_advice_id"] == 881001, "医师建议ID被错误覆盖为创建人"

        # ---- 规则2：治疗记录留痕更正 ----
        r = await client.post(
            "/api/v1/mt/treatment-records",
            json={"customer_id": customer_id, "store_id": store_id, "nps": 9, "remark": "初始"},
            headers=H(store_token),
        )
        assert r.json()["code"] == 0, r.text
        rec_id = r.json()["data"]["id"]

        r = await client.patch(
            f"/api/v1/mt/treatment-records/{rec_id}",
            json={"remark": "更正后", "reason": "录入错误"},
            headers=H(store_token),
        )
        assert r.json()["code"] == 0, r.text
        body = r.json()["data"]
        assert body["record"]["remark"] == "更正后"
        assert body["revision"]["before_json"]["remark"] == "初始"
        assert body["revision"]["after_json"]["remark"] == "更正后"
        # 原记录仍存在（未删除），仅留痕
        assert body["record"]["id"] == rec_id

        # ---- 规则3：效果四档判定 ----
        r = await client.post(
            "/api/v1/mt/effect-tracking",
            json={"customer_id": customer_id, "plan_id": plan["id"], "baseline_pain": 8, "latest_pain": 2, "nps": 9},
            headers=H(store_token),
        )
        assert r.json()["code"] == 0, r.text
        eff = r.json()["data"]
        assert eff["effect_level"] == "significant", f"应判显效: {eff}"
        assert eff["next_action"] is None

        r = await client.post(
            "/api/v1/mt/effect-tracking",
            json={"customer_id": customer_id, "baseline_pain": 5, "latest_pain": 5},
            headers=H(store_token),
        )
        assert r.json()["code"] == 0, r.text
        eff2 = r.json()["data"]
        assert eff2["effect_level"] == "ineffective", f"应判无效: {eff2}"
        assert eff2["next_action"] == "recommend_upgrade_or_consult"


@pytest.mark.skipif(not _db_available(), reason="需要可达的 Postgres")
def test_mt_compliance_e2e():
    asyncio.run(_run())
