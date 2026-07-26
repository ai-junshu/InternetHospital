"""审计哈希链完整性校验脚本（P4 防篡改证据，等保三级第8.1.4章）。

遍历 plat_audit_log 全量记录，逐一比对 hash 与 prev_hash 链式关系，定位首个断裂点。
既是运行时自检工具，也可作为测评机构"审计记录防篡改"的验证入口。

运行：
    cd code/backend && python -m app.verify_audit_chain
"""
from __future__ import annotations

import asyncio

from app.db.session import SessionLocal
from app.services.audit import verify_audit_chain


async def run() -> bool:
    async with SessionLocal() as db:
        ok, broken_at = await verify_audit_chain(db)
    if ok:
        print("[audit] 哈希链完整，未发现篡改。")
    else:
        print(f"[audit] 哈希链断裂，首个异常记录 seq_no={broken_at}（疑似被篡改）。")
    return ok


def main() -> None:
    ok = asyncio.run(run())
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
