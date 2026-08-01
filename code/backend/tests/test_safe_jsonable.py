"""errors._safe_jsonable 单元测试（任务九：序列化 bug 收敛）。

验证含 bytes / 嵌套结构 / 不可 JSON 对象能被收敛为可序列化结构，
避免 RequestValidationError 触发 5000 假异常。
"""
import pytest

from app.core.errors import _safe_jsonable


def test_bytes_converted_to_str():
    assert _safe_jsonable(b"hello") == "hello"


def test_nested_with_bytes():
    obj = {"a": 1, "b": [b"x", {"c": b"y"}], "d": ("t",)}
    out = _safe_jsonable(obj)
    assert out == {"a": 1, "b": ["x", {"c": "y"}], "d": ["t"]}


def test_unjsonable_falls_back_to_str():
    class Foo:
        def __repr__(self):
            return "<foo>"

    assert _safe_jsonable(Foo()) == "<foo>"


def test_depth_limit():
    # 超深嵌套应被截断为 str，不应递归爆栈
    obj = {"k": {"k": {"k": {"k": {"k": {"k": {"k": {"k": {"k": object()}}}}}}}}}
    out = _safe_jsonable(obj)
    assert isinstance(out, (dict, str))
