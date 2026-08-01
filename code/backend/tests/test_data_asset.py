"""P1 数据资产闭环测试：血缘/估值/生命周期/导出/采集。

无依赖用例（路由注册）必跑；端到端用例需 Postgres，不可达自动 skip。
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
def test_asset_new_routes_registered():
    from app.main import app

    paths = {getattr(r, "path", "") for r in app.routes}
    for p in [
        "/api/v1/plat/data-assets/{asset_id}/lineage",
        "/api/v1/plat/data-assets/{asset_id}/valuation",
        "/api/v1/plat/data-assets/{asset_id}/lifecycle",
        "/api/v1/plat/data-assets/export",
        "/api/v1/plat/data-assets/{asset_id}/collect",
    ]:
        assert p in paths, f"缺少路由 {p}"


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
    await db.execute(text("delete from plat_data_asset where name=:n"), {"n": "SEED治疗效果数据集"})
    await db.execute(text("delete from plat_data_lineage where upstream_asset_id=:a or downstream_asset_id=:a"), {"a": 994001})
    await db.execute(text("delete from plat_data_asset where id=:a"), {"a": 994001})
    await db.execute(text("delete from plat_data_asset where id=:b"), {"b": 994002})
    await db.commit()

    from app.models.plat_models import PlatDataAsset, PlatDataLineage

    a1 = PlatDataAsset(
        id=994001, name="SEED治疗效果数据集", owner="xingyao",
        sensitivity_level="L3", usage_scope="融资估值/模型训练",
        quality_score=0.5, update_freq="daily", lifecycle_status="collected",
    )
    a2 = PlatDataAsset(
        id=994002, name="SEED客户档案", owner="xingyao",
        sensitivity_level="L2", usage_scope="门店经营",
        quality_score=0.7, update_freq="daily", lifecycle_status="stored",
    )
    db.add_all([a1, a2])
    db.add(PlatDataLineage(upstream_asset_id=994002, downstream_asset_id=994001,
                           transform_logic="客户档案→治疗效果数据集：按疗效四档聚合"))
    await db.commit()
    return 994001, 994002


async def _run():
    from app.main import app

    settings.rate_limit_enabled = False
    await engine.dispose()
    # 测试库整体重建，确保新增列（lifecycle_status 等）生效
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as db:
        a1, a2 = await _seed(db)

    token = create_access_token("1", "xingyao")
    H = lambda t: {"Authorization": f"Bearer {t}"}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # ---- 血缘查询 ----
        r = await client.get(f"/api/v1/plat/data-assets/{a1}/lineage", headers=H(token))
        assert r.json()["code"] == 0, r.text
        assert len(r.json()["data"]["upstream"]) == 1
        assert r.json()["data"]["upstream"][0]["upstream_asset_id"] == a2

        # ---- 新增血缘（须以当前资产为端点）----
        r = await client.post(
            f"/api/v1/plat/data-assets/{a1}/lineage",
            json={"upstream_asset_id": 999999, "downstream_asset_id": 999998},
            headers=H(token),
        )
        assert r.json()["code"] != 0, "非端点血缘应被拒"

        # ---- 估值计算（L3 系数 2.5）----
        r = await client.get(f"/api/v1/plat/data-assets/{a1}/valuation", headers=H(token))
        assert r.json()["code"] == 0, r.text
        val = r.json()["data"]
        assert val["sensitivity_factor"] == 2.5
        assert val["estimated_value"] == 0.0  # 数据量 0 × 系数

        # ---- 生命周期流转 ----
        r = await client.post(f"/api/v1/plat/data-assets/{a1}/lifecycle", headers=H(token))
        assert r.json()["code"] == 0, r.text
        assert r.json()["data"]["lifecycle_status"] == "cleaned"

        # ---- 导出脱敏（不含 lineage/valuation 明细）----
        r = await client.get("/api/v1/plat/data-assets/export", headers=H(token))
        assert r.json()["code"] == 0, r.text
        items = r.json()["data"]
        assert any(it["id"] == a1 for it in items)
        assert all("lineage_json" not in it for it in items)
        assert all("valuation_json" not in it for it in items)

        # ---- 采集（治疗效果数据集 → 聚合数据量/质量分）----
        r = await client.post(f"/api/v1/plat/data-assets/{a1}/collect", headers=H(token))
        assert r.json()["code"] == 0, r.text
        # 当前业务表无数据，data_volume 应被回写为 0（采集器运行过）
        assert r.json()["data"]["data_volume"] == 0


@pytest.mark.skipif(not _db_available(), reason="需要可达的 Postgres")
def test_data_asset_e2e():
    asyncio.run(_run())
