"""合理用药引擎包：抽象层 + 本地真引擎 + Mock 基准 + Http 骨架 + 工厂。

工厂依据 settings.rx_engine_provider 选择实现，优先级 http > local > mock：
- http：对接外部合理用药供应商（base_url 可配）
- local：内置本地临床知识库真引擎（推荐默认，零外部依赖，覆盖相互作用/禁忌/
         重复用药/特殊人群/剂量告警）
- mock：内置最小规则集（降级基准，仅作兜底与单测对照）
"""
from __future__ import annotations

from app.core.config import settings
from app.services.rx_engine.base import RxEngine, RxResult
from app.services.rx_engine.http import HttpRxEngine
from app.services.rx_engine.local import LocalRxEngine
from app.services.rx_engine.mock import MockRxEngine

__all__ = [
    "RxEngine",
    "RxResult",
    "MockRxEngine",
    "HttpRxEngine",
    "LocalRxEngine",
    "get_rx_engine",
]


def get_rx_engine() -> RxEngine:
    """按配置返回合理用药引擎实例（默认 local）。"""
    provider = getattr(settings, "rx_engine_provider", "local")
    if provider == "http":
        return HttpRxEngine(getattr(settings, "rx_engine_base_url", ""))
    if provider == "mock":
        return MockRxEngine()
    # local 或未知值一律回退本地真引擎，保证「真引擎」可用
    return LocalRxEngine(getattr(settings, "rx_engine_kb_path", None) or None)

