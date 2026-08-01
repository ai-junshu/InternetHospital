"""药品库存 adjust delta 增减语义集成测试（P3 / 库存语义改造）。

按既有约定（test_health.py）用真实 uvicorn 子进程 + httpx 驱动，
避免 TestClient 在 Windows 下与异步 Redis/DB 连接池 event loop 冲突。

覆盖：
  - 建药房 / 建药品 / 建库存（stock=100）
  - +30 入库 -> 130
  - -50 出库 -> 80
  - 同步 safety_stock=30 -> 库存不变、阈值更新
  - -200 超额出库 -> 拒绝（PARAM_INVALID，提示当前库存）
  - delta 缺失 -> 参数校验失败返回 1001，不再触发 5000 假异常（验证 errors._safe_jsonable）
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


def _auth(t: str) -> dict:
    return {"Authorization": f"Bearer {t}"}


def _seed(c: httpx.Client, token: str):
    h = _auth(token)
    ph = c.post("/api/v1/ih/pharmacies", json={"name": "UT药房"}, headers=h).json()["data"]
    drug = c.post("/api/v1/ih/drugs", json={"name": "UT药A", "otc_type": "otc"}, headers=h).json()["data"]
    st = c.post(
        "/api/v1/ih/drug-stocks",
        json={"drug_id": drug["id"], "pharmacy_id": ph["id"], "stock": 100, "safety_stock": 20},
        headers=h,
    ).json()["data"]
    return st["id"]


def test_adjust_delta_semantics(server):
    with httpx.Client(base_url=server, timeout=10) as c:
        tok = c.post("/api/v1/auth/dev-token", json={"role": "platform", "sub": "1"}).json()["data"][
            "access_token"
        ]
        h = _auth(tok)
        sid = _seed(c, tok)

        # +30 入库
        r = c.patch(f"/api/v1/ih/drug-stocks/{sid}", json={"delta_stock": 30, "reason": "采购入库"}, headers=h)
        assert r.status_code == 200, r.text
        assert r.json()["data"]["stock"] == 130

        # -50 出库
        r = c.patch(f"/api/v1/ih/drug-stocks/{sid}", json={"delta_stock": -50, "reason": "销售出库"}, headers=h)
        assert r.status_code == 200, r.text
        assert r.json()["data"]["stock"] == 80

        # 同步安全库存阈值（设值语义，不影响 stock）
        r = c.patch(
            f"/api/v1/ih/drug-stocks/{sid}", json={"delta_stock": 0, "safety_stock": 30}, headers=h
        )
        assert r.status_code == 200, r.text
        d = r.json()["data"]
        assert d["stock"] == 80 and d["safety_stock"] == 30

        # 超额出库 -200：当前 80，应拒绝并提示当前库存
        r = c.patch(f"/api/v1/ih/drug-stocks/{sid}", json={"delta_stock": -200}, headers=h)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["code"] != 0
        assert "当前" in (body.get("message") or "")


def test_adjust_invalid_param_no_crash(server):
    """参数校验失败应正常返回 PARAM_INVALID，不触发 5000 假异常。"""
    with httpx.Client(base_url=server, timeout=10) as c:
        tok = c.post("/api/v1/auth/dev-token", json={"role": "platform", "sub": "1"}).json()["data"][
            "access_token"
        ]
        h = _auth(tok)
        sid = _seed(c, tok)
        # delta_stock 缺失 -> 参数校验失败，应返回 code=1001 而非 5000
        r = c.patch(f"/api/v1/ih/drug-stocks/{sid}", json={}, headers=h)
        assert r.status_code == 200, r.text
        assert r.json()["code"] == 1001, r.text
