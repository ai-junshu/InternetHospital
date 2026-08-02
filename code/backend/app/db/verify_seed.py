"""种子数据实证脚本（只读核对，不写入）。

解决的问题：seed.py 虽幂等，但「是否真正跑过、关键实体是否落地」长期未实证。
本脚本连库只读核对关键不变量，输出可读报告，并支持 --json 供 CI 消费，
校验失败时非零退出（默认 exit 1，--strict 时）。

核对项：
- 门店 / 调理师 / 药师 / 后台账号 / AI 模型 / 数据资产 均非空
- P3 演示模块：药品 / 药房 / 库存 / 科室 / 投诉 均非空
- platform_admin 账号存在且 two_factor_enabled=True 且已注入 totp_secret
- 演示账号密码哈希非空（说明 password_hash 已落库）

用法：
    python -m app.db.verify_seed            # 控制台报告
    python -m app.db.verify_seed --json     # 输出 JSON
    python -m app.db.verify_seed --strict   # 任一失败即 exit 1
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.ih_models import (
    IhComplaint,
    IhDepartment,
    IhDrug,
    IhDrugStock,
    IhPharmacy,
    IhPharmacist,
)
from app.models.mt_models import MtStore, MtTherapist
from app.models.plat_models import PlatAccount, PlatAiModel, PlatDataAsset


async def verify() -> dict:
    report: dict = {"ok": True, "checks": []}

    async def _count(model) -> int:
        async with SessionLocal() as db:
            return (await db.scalar(select(func.count()).select_from(model))) or 0

    table_specs = [
        ("stores", MtStore),
        ("therapists", MtTherapist),
        ("pharmacists", IhPharmacist),
        ("accounts", PlatAccount),
        ("ai_models", PlatAiModel),
        ("data_assets", PlatDataAsset),
        ("ih_drugs", IhDrug),
        ("pharmacies", IhPharmacy),
        ("drug_stocks", IhDrugStock),
        ("departments", IhDepartment),
        ("complaints", IhComplaint),
    ]

    for name, model in table_specs:
        cnt = await _count(model)
        passed = cnt > 0
        report["checks"].append(
            {"name": f"table_non_empty:{name}", "passed": passed, "count": cnt}
        )
        if not passed:
            report["ok"] = False

    # platform_admin 双因子实证
    async with SessionLocal() as db:
        acc = (
            await db.scalar(
                select(PlatAccount).where(PlatAccount.username == "platform_admin")
            )
        )
        if acc is None:
            report["checks"].append(
                {"name": "platform_admin_exists", "passed": False, "detail": "账号不存在"}
            )
            report["ok"] = False
        else:
            two_fa = bool(acc.two_factor_enabled)
            has_secret = bool(acc.totp_secret)
            has_hash = bool(acc.password_hash)
            passed = two_fa and has_secret and has_hash
            report["checks"].append(
                {
                    "name": "platform_admin_2fa",
                    "passed": passed,
                    "two_factor_enabled": two_fa,
                    "totp_secret_injected": has_secret,
                    "password_hash_present": has_hash,
                }
            )
            if not passed:
                report["ok"] = False

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="种子数据实证（只读核对）")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出")
    parser.add_argument("--strict", action="store_true", help="任一校验失败则 exit 1")
    args = parser.parse_args()

    report = asyncio.run(verify())

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("=" * 56)
        print("种子数据实证报告")
        print("=" * 56)
        for c in report["checks"]:
            mark = "[PASS]" if c["passed"] else "[FAIL]"
            extra = {k: v for k, v in c.items() if k not in ("name", "passed")}
            print(f"  {mark} {c['name']}  {extra}")
        print("-" * 56)
        print("Overall: " + ("PASS" if report["ok"] else "FAIL"))

    if args.strict and not report["ok"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
