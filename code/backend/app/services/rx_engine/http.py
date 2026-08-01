"""真实合理用药引擎对接骨架（第三方供应商，技术架构第14章）。

预留 HTTP 对接点：通过 settings.rx_engine_base_url 指向供应商端点，
调用其处方审核接口并返回 RxResult 同构结果。

当前为骨架（默认不启用）；启用需配置 RX_ENGINE_PROVIDER=http 与 RX_ENGINE_BASE_URL，
并由供应商提供接口契约。调用失败应由调用方降级处理（参考 prescriptions.create）。
"""
from __future__ import annotations

import httpx
from datetime import datetime, timezone
from typing import Any

from app.services.rx_engine.base import RxEngine, RxResult


class HttpRxEngine(RxEngine):
    """对接真实合理用药供应商（HTTP）。

    契约：POST {base_url}/v1/rx-check，请求体为处方 dict（与 MockRxEngine 同构输入），
    响应为 RxResult 同构 JSON：{conflicts, contraindications, dosage_warnings}。
    生产环境只需将 settings.rx_engine_base_url 指向真实供应商即可，调用方已对异常降级。
    """

    provider = "http"

    def __init__(self, base_url: str, timeout: float = 3.0) -> None:
        self.base_url = (base_url or "").rstrip("/")
        self.timeout = timeout

    def check(self, prescription: dict) -> RxResult:
        if not self.base_url:
            raise ValueError("HttpRxEngine 未配置 rx_engine_base_url")
        resp = httpx.post(
            f"{self.base_url}/v1/rx-check",
            json=prescription,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json() or {}
        return RxResult(
            provider=self.provider,
            conflicts=[dict(c) for c in (data.get("conflicts") or [])],
            contraindications=[dict(c) for c in (data.get("contraindications") or [])],
            dosage_warnings=[dict(d) for d in (data.get("dosage_warnings") or [])],
            checked_at=datetime.now(timezone.utc).isoformat(),
        )
