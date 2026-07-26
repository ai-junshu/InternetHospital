"""合理用药引擎包：抽象层 + Mock + Http 骨架 + 工厂。

工厂依据 settings.rx_engine_provider 选择实现（默认 mock），便于无缝切换真实供应商。
"""
from __future__ import annotations

from app.core.config import settings
from app.services.rx_engine.base import RxEngine, RxResult
from app.services.rx_engine.http import HttpRxEngine
from app.services.rx_engine.mock import MockRxEngine

__all__ = ["RxEngine", "RxResult", "MockRxEngine", "HttpRxEngine", "get_rx_engine"]


def get_rx_engine() -> RxEngine:
    """按配置返回合理用药引擎实例（默认 mock）。"""
    provider = getattr(settings, "rx_engine_provider", "mock")
    if provider == "http":
        return HttpRxEngine(getattr(settings, "rx_engine_base_url", ""))
    return MockRxEngine()
