"""幂等中间件集成测试（任务十九：订单等关键写接口挂载幂等）。

按既有约定用真实 uvicorn 子进程 + httpx 驱动。
验证：
  - 带相同 Idempotency-Key 的重复写请求，第二次返回首次缓存结果（Idempotency-Replay: true）
  - 不同 Key 视为不同请求（各自创建）
  - 4xx 响应不缓存（允许换 Key 重试）
"""
import httpx
import pytest
import socket
import subprocess
import sys
import time


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="module")
def server():
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}/health"
    for _ in range(60):
        try:
            if httpx.get(url, timeout=1).status_code == 200:
                break
        except Exception:
            time.sleep(0.2)
    else:
        proc.terminate()
        raise RuntimeError("uvicorn 未能就绪")
    yield f"http://127.0.0.1:{port}"
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


@pytest.fixture(scope="module")
def token(server):
    with httpx.Client(base_url=server, timeout=10) as c:
        return c.post("/api/v1/auth/dev-token", json={"role": "platform", "sub": "1"}).json()["data"][
            "access_token"
        ]


def _key(prefix: str) -> str:
    return f"{prefix}-{int(time.time()*1000)}-{id(prefix)}"


def test_idempotent_replay(server, token):
    h = {"Authorization": f"Bearer {token}"}
    with httpx.Client(base_url=server, timeout=10) as c:
        body = {"name": "幂等药房", "region": "北京", "license_no": "IDEM-LIC-1"}
        k = _key("replay")
        # 首次
        r1 = c.post("/api/v1/ih/pharmacies", json=body, headers={**h, "Idempotency-Key": k})
        assert r1.status_code == 200
        first_id = r1.json()["data"]["id"]
        # 重复（同 Key）
        r2 = c.post("/api/v1/ih/pharmacies", json=body, headers={**h, "Idempotency-Key": k})
        assert r2.status_code == 200
        assert r2.headers.get("Idempotency-Replay") == "true"
        assert r2.json()["data"]["id"] == first_id  # 返回首次结果，未新建


def test_different_key_creates_new(server, token):
    h = {"Authorization": f"Bearer {token}"}
    with httpx.Client(base_url=server, timeout=10) as c:
        body = {"name": "幂等药房B", "region": "北京", "license_no": "IDEM-LIC-2"}
        r1 = c.post("/api/v1/ih/pharmacies", json=body, headers={**h, "Idempotency-Key": _key("d1")})
        r2 = c.post("/api/v1/ih/pharmacies", json=body, headers={**h, "Idempotency-Key": _key("d2")})
        assert r1.json()["data"]["id"] != r2.json()["data"]["id"]


def test_error_not_cached(server, token):
    """业务失败（统一错误模型下 HTTP 200 + code!=0）不缓存，允许同 Key 重试。"""
    h = {"Authorization": f"Bearer {token}"}
    with httpx.Client(base_url=server, timeout=10) as c:
        k = _key("err")
        # 缺必填 name -> 参数校验失败（code!=0）
        r1 = c.post("/api/v1/ih/pharmacies", json={"region": "北京"}, headers={**h, "Idempotency-Key": k})
        assert r1.status_code == 200 and r1.json()["code"] != 0
        assert r1.headers.get("Idempotency-Replay") is None
        # 同 Key 仍返回校验失败（错误未缓存），说明可重试
        r2 = c.post("/api/v1/ih/pharmacies", json={"region": "北京"}, headers={**h, "Idempotency-Key": k})
        assert r2.json()["code"] != 0
        assert r2.headers.get("Idempotency-Replay") is None
