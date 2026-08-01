"""限流 XFF 信任策略单元测试（任务八：防 XFF 伪造绕过 per_ip 限流）。

验证 _is_trusted_proxy：
  - 默认空 cidr -> 任何直连 IP 都不信任（直连场景伪造 XFF 无效）
  - 命中受信 CIDR -> 信任（生产反代后启用 XFF 首段）
  - 直连 localhost/unknown -> 永不可信
  - 非法 CIDR 字符串 -> 跳过不报错
"""
import pytest

from app.core.config import settings
from app.middleware.rate_limit import _is_trusted_proxy


def _with_cidrs(tmp, monkeypatch):
    monkeypatch.setattr(settings, "trusted_proxy_cidrs", tmp)


def test_empty_cidr_no_trust(monkeypatch):
    _with_cidrs("", monkeypatch)
    assert _is_trusted_proxy("203.0.113.5") is False


def test_localhost_never_trusted(monkeypatch):
    _with_cidrs("0.0.0.0/0", monkeypatch)
    assert _is_trusted_proxy("127.0.0.1") is False
    assert _is_trusted_proxy("::1") is False
    assert _is_trusted_proxy("unknown") is False


def test_hit_cidr_trusted(monkeypatch):
    _with_cidrs("10.0.0.0/8,172.16.0.0/12", monkeypatch)
    assert _is_trusted_proxy("10.1.2.3") is True
    assert _is_trusted_proxy("172.16.5.5") is True


def test_miss_cidr_not_trusted(monkeypatch):
    _with_cidrs("10.0.0.0/8", monkeypatch)
    assert _is_trusted_proxy("203.0.113.9") is False


def test_invalid_cidr_skipped(monkeypatch):
    _with_cidrs("not-a-cidr,10.0.0.0/8", monkeypatch)
    # 非法 cidr 被跳过，合法段仍生效
    assert _is_trusted_proxy("10.0.0.1") is True
    assert _is_trusted_proxy("8.8.8.8") is False


def test_malformed_ip_not_trusted(monkeypatch):
    _with_cidrs("10.0.0.0/8", monkeypatch)
    assert _is_trusted_proxy("999.1.1.1") is False
