"""幂等种子数据（P3 生产就绪 + P4 双因子演示账号）。

为健康数据中台提供真实门店 / 调理师，为 plat 资产 / 模型目录预置记录，并为后台
预置账号（含双因子 TOTP，便于真跑登录链路）。可重复执行（按唯一键去重）。

运行：
    cd code/backend && python -m app.db.seed
"""
from __future__ import annotations

from sqlalchemy import select

from app.db.session import SessionLocal
from app.core.security import gen_totp_secret, hash_password, totp_provisioning_uri
from app.models.mt_models import MtStore, MtTherapist
from app.models.plat_models import PlatAiModel, PlatDataAsset, PlatAccount
from app.models.ih_models import (
    IhUser,
    IhPharmacist,
    IhDrug,
    IhPharmacy,
    IhDrugStock,
    IhDepartment,
    IhComplaint,
)

# 演示账号（⚠️ 仅本地 dev，生产须经密钥管理下发并强制改密）
SEED_PASSWORD = "Ihm@2026!dev"
ACCOUNTS = [
    {"username": "platform_admin", "role": "platform", "two_factor": True},
    {"username": "xingyao_admin", "role": "xingyao", "two_factor": False},
    {"username": "store_admin", "role": "store", "two_factor": False},
    {"username": "therapist_admin", "role": "therapist", "two_factor": False},
]


# ---- 预置数据 ----

STORES = [
    {"name": "星耀疼痛调理中心（北京朝阳店）", "region": "华北", "city": "北京", "type": "flagship"},
    {"name": "星耀康复门店（上海浦东店）", "region": "华东", "city": "上海", "type": "standard"},
    {"name": "星耀调理馆（广州天河店）", "region": "华南", "city": "广州", "type": "standard"},
]

THERAPISTS = {
    "星耀疼痛调理中心（北京朝阳店）": [
        {"name": "李慧", "license_no": "TH-BJ-0001", "skill_tags": {"推拿": 5, "艾灸": 4}},
        {"name": "王磊", "license_no": "TH-BJ-0002", "skill_tags": {"理疗": 4, "筋膜": 3}},
    ],
    "星耀康复门店（上海浦东店）": [
        {"name": "张敏", "license_no": "TH-SH-0001", "skill_tags": {"康复": 5, "运动": 4}},
        {"name": "陈静", "license_no": "TH-SH-0002", "skill_tags": {"针灸": 4, "推拿": 3}},
    ],
    "星耀调理馆（广州天河店）": [
        {"name": "黄强", "license_no": "TH-GZ-0001", "skill_tags": {"调理": 5, "药膳": 3}},
    ],
}

AI_MODELS = [
    {
        "name": "复购预测模型",
        "version": "v1.0.0",
        "algo_type": "xgboost",
        "metrics_json": {"next_visit_auc": 0.86, "repurchase_auc": 0.83, "sample_size": 120000},
        "status": "online",
    },
    {
        "name": "健康风险画像模型",
        "version": "v0.9.0",
        "algo_type": "gradient_boosting",
        "metrics_json": {"pain_risk_auc": 0.81, "comorbidity_auc": 0.79, "sample_size": 95000},
        "status": "online",
    },
    {
        "name": "调理方案推荐模型",
        "version": "v0.8.0",
        "algo_type": "llm+ranking",
        "metrics_json": {"ctr": 0.27, "adopt_rate": 0.34, "sample_size": 60000},
        "status": "online",
    },
]

DATA_ASSETS = [
    {
        "name": "客户画像资产",
        "owner": "健康数据中台",
        "sensitivity_level": "L2",
        "usage_scope": "客户分群、精准运营（脱敏后）",
        "quality_score": 0.92,
        "update_freq": "T+1",
        "lineage_json": {"source": ["mt_customer", "ih_user"], "transform": "脱敏+特征工程"},
    },
    {
        "name": "治疗效果数据集",
        "owner": "健康数据中台",
        "sensitivity_level": "L3",
        "usage_scope": "模型训练（联邦学习，原始不出域）",
        "quality_score": 0.88,
        "update_freq": "T+1",
        "lineage_json": {"source": ["mt_pain_assessment", "mt_effect_tracking", "mt_treatment_record"], "transform": "隐私计算"},
    },
    {
        "name": "调理方案库",
        "owner": "星耀产业资本",
        "sensitivity_level": "L2",
        "usage_scope": "方案推荐、知识沉淀",
        "quality_score": 0.85,
        "update_freq": "周级",
        "lineage_json": {"source": ["mt_care_plan"], "transform": "人工审核沉淀"},
    },
    {
        "name": "门店经营宽表",
        "owner": "平台运营",
        "sensitivity_level": "L2",
        "usage_scope": "经营分析、Grafana 看板",
        "quality_score": 0.90,
        "update_freq": "T+1",
        "lineage_json": {"source": ["mt_treatment_record", "mt_store_metrics"], "transform": "预聚合"},
    },
]

# 药师（迭代 A · S2 药师审核工作台）：先建 ih_user，再关联 ih_pharmacist
PHARMACISTS = [
    {"openid": "dev_pharmacist_zhao", "license_no": "PH-DEV-0001", "title": "主任药师"},
    {"openid": "dev_pharmacist_qian", "license_no": "PH-DEV-0002", "title": "执业药师"},
]


async def _upsert_store(db, data: dict) -> int:
    existing = (
        await db.scalar(select(MtStore).where(MtStore.name == data["name"], MtStore.is_deleted.is_(False)))
    )
    if existing:
        return existing.id
    store = MtStore(**data)
    db.add(store)
    await db.flush()
    return store.id


async def _upsert_therapist(db, store_id: int, data: dict) -> None:
    existing = (
        await db.scalar(
            select(MtTherapist).where(MtTherapist.license_no == data["license_no"], MtTherapist.is_deleted.is_(False))
        )
    )
    if existing:
        return
    db.add(MtTherapist(store_id=store_id, **data))


async def _upsert_ai_model(db, data: dict) -> None:
    existing = (
        await db.scalar(
            select(PlatAiModel).where(
                PlatAiModel.name == data["name"], PlatAiModel.version == data["version"], PlatAiModel.is_deleted.is_(False)
            )
        )
    )
    if existing:
        return
    db.add(PlatAiModel(**data))


async def _upsert_data_asset(db, data: dict) -> None:
    existing = (
        await db.scalar(select(PlatDataAsset).where(PlatDataAsset.name == data["name"], PlatDataAsset.is_deleted.is_(False)))
    )
    if existing:
        return
    db.add(PlatDataAsset(**data))


async def _upsert_pharmacist(db, data: dict) -> None:
    existing = (
        await db.scalar(
            select(IhPharmacist).where(
                IhPharmacist.license_no == data["license_no"], IhPharmacist.is_deleted.is_(False)
            )
        )
    )
    if existing:
        return
    user = (
        await db.scalar(select(IhUser).where(IhUser.openid == data["openid"], IhUser.is_deleted.is_(False)))
    )
    if user is None:
        user = IhUser(openid=data["openid"])
        db.add(user)
        await db.flush()
    db.add(IhPharmacist(user_id=user.id, license_no=data["license_no"], title=data.get("title")))


async def _upsert_account(db, data: dict) -> bool:
    existing = (
        await db.scalar(
            select(PlatAccount).where(PlatAccount.username == data["username"], PlatAccount.is_deleted.is_(False))
        )
    )
    if existing:
        return False
    ph, salt = hash_password(SEED_PASSWORD)
    acc = PlatAccount(
        username=data["username"],
        role=data["role"],
        store_id=data.get("store_id"),
        password_hash=ph,
        password_salt=salt,
        status="active",
    )
    if data.get("two_factor"):
        secret = gen_totp_secret()
        acc.totp_secret = secret
        acc.two_factor_enabled = True
        print(
            f"[seed] {data['username']} 已开通双因子，otpauth_uri（导入 Google/微信令牌）:\n"
            f"       {totp_provisioning_uri(secret, account=data['username'])}"
        )
    db.add(acc)
    return True


async def seed_all() -> dict:
    summary = {
        "stores": 0,
        "therapists": 0,
        "ai_models": 0,
        "data_assets": 0,
        "accounts": 0,
        "pharmacists": 0,
        "ih_drugs": 0,
        "pharmacies": 0,
        "drug_stocks": 0,
        "departments": 0,
        "complaints": 0,
    }
    async with SessionLocal() as db:
        store_ids: dict[str, int] = {}
        for s in STORES:
            sid = await _upsert_store(db, s)
            store_ids[s["name"]] = sid
            summary["stores"] += 1
        for store_name, therapists in THERAPISTS.items():
            for t in therapists:
                await _upsert_therapist(db, store_ids[store_name], t)
                summary["therapists"] += 1
        for m in AI_MODELS:
            await _upsert_ai_model(db, m)
            summary["ai_models"] += 1
        for a in DATA_ASSETS:
            await _upsert_data_asset(db, a)
            summary["data_assets"] += 1
        for p in PHARMACISTS:
            await _upsert_pharmacist(db, p)
            summary["pharmacists"] += 1
        first_store_id = next(iter(store_ids.values()), None)
        for acc in ACCOUNTS:
            acc_copy = dict(acc)
            if acc["role"] == "store":
                acc_copy["store_id"] = first_store_id
            if await _upsert_account(db, acc_copy):
                summary["accounts"] += 1
        # ---- P3 双缺模块演示数据（幂等，按唯一键去重） ----
        await _seed_p3_modules(db, summary)
        await db.commit()
    return summary


async def _seed_p3_modules(db, summary: dict) -> None:
    # 演示药品（供库存维度关联）
    demo_drug = await db.scalar(select(IhDrug).where(IhDrug.name == "示例布洛芬片", IhDrug.is_deleted.is_(False)))
    if not demo_drug:
        demo_drug = IhDrug(name="示例布洛芬片", otc_type="otc", spec="0.2g*24片", manufacturer="示例药业", status="on")
        db.add(demo_drug)
        await db.flush()
        summary["ih_drugs"] += 1

    # 演示药房
    demo_pharmacy = await db.scalar(
        select(IhPharmacy).where(IhPharmacy.name == "示例合作药房-海淀店", IhPharmacy.is_deleted.is_(False))
    )
    if not demo_pharmacy:
        demo_pharmacy = IhPharmacy(
            name="示例合作药房-海淀店", region="北京海淀", license_no="YLJYZZ-DEMO-001", status="active"
        )
        db.add(demo_pharmacy)
        await db.flush()
        summary["pharmacies"] += 1

    # 演示库存（药品×药房维度）
    if not await db.scalar(
        select(IhDrugStock).where(
            IhDrugStock.drug_id == demo_drug.id,
            IhDrugStock.pharmacy_id == demo_pharmacy.id,
            IhDrugStock.is_deleted.is_(False),
        )
    ):
        db.add(
            IhDrugStock(drug_id=demo_drug.id, pharmacy_id=demo_pharmacy.id, stock=500, safety_stock=100)
        )
        summary["drug_stocks"] += 1

    # 演示科室
    if not await db.scalar(
        select(IhDepartment).where(IhDepartment.name == "示例康复医学科", IhDepartment.is_deleted.is_(False))
    ):
        db.add(IhDepartment(name="示例康复医学科", head="示例主任医师", remark="演示科室，可编辑/删除"))
        summary["departments"] += 1

    # 演示投诉（关联演示订单/用户，脱敏展示）
    if not await db.scalar(
        select(IhComplaint).where(IhComplaint.content == "示例：药品包装破损反馈", IhComplaint.is_deleted.is_(False))
    ):
        db.add(
            IhComplaint(
                order_id=1,
                user_id=1,
                type="quality",
                content="示例：药品包装破损反馈",
                status="resolved",
                reply="已联系药房补发，已处理",
            )
        )
        summary["complaints"] += 1


def main() -> None:
    import asyncio

    count = asyncio.run(seed_all())
    print(
        f"[seed] done: stores={count['stores']} therapists={count['therapists']} "
        f"ai_models={count['ai_models']} data_assets={count['data_assets']} "
        f"accounts={count['accounts']} pharmacists={count['pharmacists']} "
        f"ih_drugs={count['ih_drugs']} pharmacies={count['pharmacies']} "
        f"drug_stocks={count['drug_stocks']} departments={count['departments']} "
        f"complaints={count['complaints']}"
    )
    print(f"[seed] 后台演示账号密码（本地 dev）：{SEED_PASSWORD}")


if __name__ == "__main__":
    main()
