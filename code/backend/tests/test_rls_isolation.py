"""多租户行级隔离（RLS）越权测试 —— 对抗式验证「注入 ≠ 生效」。

背景：mt 域多处端点虽已 Depends(store_scope) 注入作用域，但函数体内未用于
WHERE 过滤（死参数），导致任意门店可读写全量数据。本测试用两个真实门店的
令牌交叉访问，证明隔离**确实生效**，而非仅仅"注入了参数"。

覆盖：
- mt/risk-profiles：读过滤 + 写侧归属校验
- mt/effect-tracking：读过滤 + 写侧归属校验
- mt/therapists/{id}/schedules：跨店调理师操作应 FORBIDDEN
- platform 角色：不下钻可见全量；下钻 scope_store_id 后仅见该店

DB 不可达时端到端用例自动 skip；纯逻辑用例（依赖签名/守卫开关）必跑。
复用 test_mt_compliance.py 的 ASGI + token + skip 模式。
"""
import asyncio
import inspect

import httpx
import pytest
from sqlalchemy import text

from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import SessionLocal, engine
from app.models.base import Base

# 种子固定高位 id，避免与业务/其它用例冲突
STORE_A = 994010
STORE_B = 994011
CUST_A = 994001
CUST_B = 994002
THERAPIST_A = 994020
THERAPIST_B = 994021


# ===================== 无外部依赖：必跑 =====================
def test_rls_endpoints_inject_store_scope():
    """静态断言：曾缺失 scope 注入的端点，签名中必须含 scope 参数。

    这是"注入"层面的回归防线；"生效"由下方端到端用例保证。
    """
    from app.api.v1.mt import effect_tracking, risk_profiles, scheduling

    targets = [
        risk_profiles.predict_risk,
        risk_profiles.list_risk_profiles,
        effect_tracking.create_effect_tracking,
        effect_tracking.list_effect_tracking,
        scheduling.create_therapist_schedule,
        scheduling.list_therapist_schedules,
        scheduling.update_therapist_schedule,
        scheduling.delete_therapist_schedule,
        scheduling.list_therapist_tags,
        scheduling.assign_therapist_tag,
        scheduling.unassign_therapist_tag,
    ]
    for fn in targets:
        assert "scope" in inspect.signature(fn).parameters, (
            f"{fn.__module__}.{fn.__name__} 缺少 store_scope 注入（RLS 隔离缺口）"
        )


def test_load_therapist_takes_scope_not_session():
    """_load_therapist 曾误将 AsyncSession 当作 scope_store_id 传入 store_scope。

    修复后应直接接收已解析的 scope（int | None），不再手工调用 store_scope。
    """
    from app.api.v1.mt.scheduling import _load_therapist

    params = list(inspect.signature(_load_therapist).parameters)
    assert params == ["db", "therapist_id", "scope"], f"参数签名异常: {params}"

    src = inspect.getsource(_load_therapist)
    assert "store_scope(" not in src, "不应在函数体内手工调用 store_scope"


def test_dev_auto_profile_disabled_by_default():
    """合规红线：执业档案自动建档开关默认必须关闭。"""
    assert settings.allow_dev_auto_profile is False, (
        "allow_dev_auto_profile 默认必须为 False，否则任意用户可伪造医师/药师身份"
    )


def test_wx_login_rejects_doctor_without_profile_source():
    """守卫存在性断言：无档案且开关关闭时应抛 FORBIDDEN 而非自动建档。"""
    from app.api.v1.ih.users import _resolve_subject

    src = inspect.getsource(_resolve_subject)
    assert "allow_dev_auto_profile" in src, "自动建档未受开关守卫"
    assert src.count("allow_dev_auto_profile") >= 2, "医师与药师分支都应受守卫"


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
    """清理并重建两店/两客户/两调理师，保证用例可重复运行。"""
    cust_ids = (CUST_A, CUST_B)
    await db.execute(
        text("delete from mt_risk_profile where customer_id = any(:c)"), {"c": list(cust_ids)}
    )
    await db.execute(
        text("delete from mt_effect_tracking where customer_id = any(:c)"), {"c": list(cust_ids)}
    )
    await db.execute(
        text("delete from mt_therapist_schedule where therapist_id = any(:t)"),
        {"t": [THERAPIST_A, THERAPIST_B]},
    )
    await db.execute(
        text("delete from mt_therapist where id = any(:t)"), {"t": [THERAPIST_A, THERAPIST_B]}
    )
    await db.execute(text("delete from mt_customer where id = any(:c)"), {"c": list(cust_ids)})
    await db.execute(
        text("delete from mt_store where id = any(:s)"), {"s": [STORE_A, STORE_B]}
    )
    await db.commit()

    from app.models.mt_models import MtCustomer, MtStore, MtTherapist

    db.add_all(
        [
            MtStore(id=STORE_A, name="RLS门店A", region="华东", city="上海", type="direct", status="active"),
            MtStore(id=STORE_B, name="RLS门店B", region="华南", city="深圳", type="direct", status="active"),
            MtCustomer(id=CUST_A, source_store_id=STORE_A, auth_status="authorized"),
            MtCustomer(id=CUST_B, source_store_id=STORE_B, auth_status="authorized"),
            MtTherapist(id=THERAPIST_A, store_id=STORE_A, name="调理师A", status="active"),
            MtTherapist(id=THERAPIST_B, store_id=STORE_B, name="调理师B", status="active"),
        ]
    )
    await db.commit()


async def _run():
    from app.main import app

    settings.rate_limit_enabled = False
    await engine.dispose()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as db:
        await _seed(db)

    tok_a = create_access_token(str(STORE_A), "store", store_id=STORE_A)
    tok_b = create_access_token(str(STORE_B), "store", store_id=STORE_B)
    tok_platform = create_access_token("1", "platform")

    def H(t):
        return {"Authorization": f"Bearer {t}"}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=30.0) as client:
        # ---------- 准备：各店为自己的客户建效果跟踪 ----------
        for tok, cust in ((tok_a, CUST_A), (tok_b, CUST_B)):
            r = await client.post(
                "/api/v1/mt/effect-tracking",
                json={"customer_id": cust, "baseline_pain": 8, "latest_pain": 2, "nps": 9},
                headers=H(tok),
            )
            assert r.json()["code"] == 0, f"本店写入应成功: {r.text}"

        # ---------- 1. effect-tracking 写越权：A 店不得为 B 店客户写入 ----------
        r = await client.post(
            "/api/v1/mt/effect-tracking",
            json={"customer_id": CUST_B, "baseline_pain": 8, "latest_pain": 2},
            headers=H(tok_a),
        )
        assert r.json()["code"] != 0, f"A店为B店客户写效果跟踪应被拒: {r.text}"

        # ---------- 2. effect-tracking 读越权：A 店列表不得含 B 店客户 ----------
        r = await client.get("/api/v1/mt/effect-tracking?page_size=200", headers=H(tok_a))
        assert r.json()["code"] == 0, r.text
        seen = {i["customer_id"] for i in r.json()["data"]["items"]}
        assert CUST_B not in seen, f"A店读到了B店客户数据（RLS 未生效）: {seen}"

        # 显式指定 B 店客户 id 也必须为空（防止 customer_id 参数绕过 scope）
        r = await client.get(
            f"/api/v1/mt/effect-tracking?customer_id={CUST_B}", headers=H(tok_a)
        )
        assert r.json()["code"] == 0, r.text
        assert r.json()["data"]["total"] == 0, "指定他店 customer_id 竟能绕过隔离"

        # ---------- 3. risk-profiles 写越权 ----------
        r = await client.post(
            "/api/v1/mt/risk-profiles",
            json={"customer_id": CUST_B, "age": 40, "bmi": 24.0, "comorbidity_count": 1},
            headers=H(tok_a),
        )
        assert r.json()["code"] != 0, f"A店为B店客户生成风险画像应被拒: {r.text}"

        # 本店写入应成功（确认守卫未误伤）
        r = await client.post(
            "/api/v1/mt/risk-profiles",
            json={"customer_id": CUST_A, "age": 40, "bmi": 24.0, "comorbidity_count": 1},
            headers=H(tok_a),
        )
        assert r.json()["code"] == 0, f"本店写入不应被拒: {r.text}"

        # ---------- 4. risk-profiles 读越权 ----------
        r = await client.get(
            f"/api/v1/mt/risk-profiles?customer_id={CUST_A}", headers=H(tok_b)
        )
        assert r.json()["code"] == 0, r.text
        assert r.json()["data"]["total"] == 0, "B店读到了A店风险画像（RLS 未生效）"

        # ---------- 5. 调理师排班跨店操作 ----------
        r = await client.get(
            f"/api/v1/mt/therapists/{THERAPIST_B}/schedules", headers=H(tok_a)
        )
        assert r.json()["code"] != 0, f"A店查B店调理师排班应被拒: {r.text}"

        r = await client.post(
            f"/api/v1/mt/therapists/{THERAPIST_B}/schedules",
            json={
                "work_date": "2026-09-01",
                "am_pm": "morning",
                "start_time": "09:00:00",
                "end_time": "12:00:00",
            },
            headers=H(tok_a),
        )
        assert r.json()["code"] != 0, f"A店给B店调理师排班应被拒: {r.text}"

        # 本店调理师应可正常访问（确认修复未误伤 —— 旧代码此处会误 403）
        r = await client.get(
            f"/api/v1/mt/therapists/{THERAPIST_A}/schedules", headers=H(tok_a)
        )
        assert r.json()["code"] == 0, f"本店调理师排班查询不应被拒: {r.text}"

        # ---------- 6. platform 角色：不下钻可见全量，下钻后仅见该店 ----------
        r = await client.get(
            "/api/v1/mt/effect-tracking?page_size=200", headers=H(tok_platform)
        )
        assert r.json()["code"] == 0, r.text
        seen_all = {i["customer_id"] for i in r.json()["data"]["items"]}
        assert {CUST_A, CUST_B} <= seen_all, f"平台角色应可见全量: {seen_all}"

        r = await client.get(
            f"/api/v1/mt/effect-tracking?scope_store_id={STORE_B}&page_size=200",
            headers=H(tok_platform),
        )
        assert r.json()["code"] == 0, r.text
        seen_b = {i["customer_id"] for i in r.json()["data"]["items"]}
        assert CUST_A not in seen_b, f"平台下钻B店不应含A店数据: {seen_b}"

        # platform 下钻到 B 店后，操作 A 店调理师应被拒
        r = await client.get(
            f"/api/v1/mt/therapists/{THERAPIST_A}/schedules?scope_store_id={STORE_B}",
            headers=H(tok_platform),
        )
        assert r.json()["code"] != 0, "平台下钻B店后不应能访问A店调理师"

    await engine.dispose()


@pytest.mark.skipif(not _db_available(), reason="需要可达的 Postgres")
def test_rls_isolation_e2e():
    asyncio.run(_run())
