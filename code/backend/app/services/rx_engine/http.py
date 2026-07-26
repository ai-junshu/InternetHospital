"""真实合理用药引擎对接骨架（第三方供应商，技术架构第14章）。

预留 HTTP 对接点：通过 settings.rx_engine_base_url 指向供应商端点，
调用其处方审核接口并返回 RxResult 同构结果。

当前为骨架（默认不启用）；启用需配置 RX_ENGINE_PROVIDER=http 与 RX_ENGINE_BASE_URL，
并由供应商提供接口契约。调用失败应由调用方降级处理（参考 prescriptions.create）。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.rx_engine.base import RxEngine, RxResult


class HttpRxEngine(RxEngine):
    provider = "http"

    def __init__(self, base_url: str, timeout: float = 3.0) -> None:
        self.base_url = base_url
        self.timeout = timeout

    def check(self, prescription: dict) -> RxResult:
        # TODO(P3-外部对接): 调用供应商 /v1/rx-check 接口，将响应映射为 RxResult。
        # 示例：
        #   import httpx
        #   resp = httpx.post(f"{self.base_url}/v1/rx-check",
        #                     json=prescription, timeout=self.timeout)
        #   resp.raise_for_status()
        #   data = resp.json()
        #   return RxResult(provider=self.provider, **data)
        raise NotImplementedError(
            "HttpRxEngine 尚未接入真实供应商，请在配置 RX_ENGINE_BASE_URL 后实现映射逻辑"
        )

    def _empty(self) -> RxResult:
        return RxResult(
            provider=self.provider,
            conflicts=[],
            contraindications=[],
            dosage_warnings=[],
            checked_at=datetime.now(timezone.utc).isoformat(),
        )
