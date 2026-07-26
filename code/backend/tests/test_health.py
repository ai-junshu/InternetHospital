"""健康检查测试（P5 升级：/health 真实探活 Redis / PostgreSQL）。

用真实 uvicorn 子进程 + httpx 验证，避免 TestClient 在 Windows 下
anyio 门户线程与异步 Redis 连接 GC 冲突导致的原生崩溃噪声。
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
    ready = False
    for _ in range(60):
        try:
            r = httpx.get(url, timeout=1)
            if r.status_code == 200:
                ready = True
                break
        except Exception:
            time.sleep(0.2)
    if not ready:
        proc.terminate()
        raise RuntimeError("uvicorn 未能在预期时间内就绪")
    yield f"http://127.0.0.1:{port}"
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


def test_health(server):
    with httpx.Client(base_url=server, timeout=5) as c:
        r = c.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["data"]["status"] == "ok"
        assert "requestId" in body
