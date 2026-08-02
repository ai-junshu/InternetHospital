"""审计脱敏测试（P2-审计脱敏对齐）。

验证 write_audit 落库前对 before/after_json 敏感字段掩码，
且 verify_audit_chain 哈希链仍自洽。
使用 asyncio.run 包裹（与项目约定一致）。
"""
import asyncio

from app.services import audit
from app.utils.mask import mask_json, mask_id_card, mask_phone, mask_name


def test_mask_json_id_card_and_phone_and_name():
    obj = {
        "id_card": "110101199003071234",
        "phone": "13800138000",
        "real_name": "张三",
        "region": "华东",
        "nested": {"patient_name": "李四", "age": 30},
        "list": [{"mobile": "13912345678"}],
    }
    m = mask_json(obj)
    assert m["id_card"] == mask_id_card("110101199003071234")
    assert m["phone"] == mask_phone("13800138000")
    assert m["real_name"] == mask_name("张三")
    assert m["region"] == "华东"  # 非敏感保持
    assert m["nested"]["patient_name"] == mask_name("李四")
    assert m["nested"]["age"] == 30
    assert m["list"][0]["mobile"] == mask_phone("13912345678")
    # 原对象不被修改
    assert obj["id_card"] == "110101199003071234"


def test_mask_value_side_fallback():
    # 键未命中但值形如身份证/手机，仍兜底脱敏
    obj = {"field_x": "13800138000", "field_y": "110101199003071234"}
    m = mask_json(obj)
    assert m["field_x"] == mask_phone("13800138000")
    assert m["field_y"] == mask_id_card("110101199003071234")


def test_write_audit_masks_and_chain_consistent():
    from app.db.session import SessionLocal
    from app.services.audit import verify_audit_chain

    async def _run():
        async with SessionLocal() as db:
            await audit.write_audit(
                db,
                action="update_patient",
                resource="patient:123",
                role="doctor",
                actor_id=1,
                before={"id_card": "110101199003071234", "real_name": "张三", "region": "华东"},
                after={"real_name": "张三丰", "region": "华东"},
                ip="127.0.0.1",
            )
            await db.commit()
            # 读回最后一条，确认敏感字段已脱敏
            from app.models.plat_models import PlatAuditLog
            from sqlalchemy import select
            last = (await db.execute(
                select(PlatAuditLog).order_by(PlatAuditLog.id.desc()).limit(1)
            )).scalar_one()
            assert last.before_json["id_card"] != "110101199003071234"
            assert last.before_json["real_name"] == mask_name("张三")
            assert last.after_json["real_name"] == mask_name("张三丰")
            assert last.before_json["region"] == "华东"  # 非敏感保持
            # 哈希链整体自洽
            ok, broken = await verify_audit_chain(db)
            assert ok is True, f"审计哈希链断裂于 seq_no={broken}"
            # 清理刚才写入的这条测试记录，避免污染
            await db.delete(last)
            await db.commit()

    asyncio.run(_run())
