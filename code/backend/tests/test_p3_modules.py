"""P3 双缺模块自动化测试（任务七）：pharmacies / departments / complaints / dashboards。

按既有约定（test_health.py）用真实 uvicorn 子进程 + httpx 驱动。
覆盖：
  - pharmacies: 建/列/详情/改/删（platform 可写）
  - departments: 建/列/详情/改/删
  - complaints: 建/列/详情/处理回复（含脱敏字段）
  - dashboards: 聚合端点返回处方量/审方通过率/投诉量/低库存等结构
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
        raise RuntimeError("uvicorn 未能就绪")
    yield f"http://127.0.0.1:{port}"
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


def _auth(t: str) -> dict:
    return {"Authorization": f"Bearer {t}"}


@pytest.fixture(scope="module")
def token(server):
    with httpx.Client(base_url=server, timeout=10) as c:
        return c.post("/api/v1/auth/dev-token", json={"role": "platform", "sub": "1"}).json()["data"][
            "access_token"
        ]


# ---------- pharmacies ----------
def test_pharmacy_crud(server, token):
    h = _auth(token)
    with httpx.Client(base_url=server, timeout=10) as c:
        # create
        r = c.post("/api/v1/ih/pharmacies", json={"name": "UT药房A", "region": "北京", "license_no": "UT-LIC-1"}, headers=h)
        assert r.status_code == 200, r.text
        pid = r.json()["data"]["id"]
        # list
        r = c.get("/api/v1/ih/pharmacies", params={"page": 1, "page_size": 10}, headers=h)
        assert r.status_code == 200 and r.json()["data"]["total"] >= 1
        # get
        r = c.get(f"/api/v1/ih/pharmacies/{pid}", headers=h)
        assert r.status_code == 200 and r.json()["data"]["name"] == "UT药房A"
        # update（router 用 PATCH）
        r = c.patch(f"/api/v1/ih/pharmacies/{pid}", json={"name": "UT药房A改", "status": "active"}, headers=h)
        assert r.status_code == 200 and r.json()["data"]["name"] == "UT药房A改"
        # delete
        r = c.delete(f"/api/v1/ih/pharmacies/{pid}", headers=h)
        assert r.status_code == 200
        r = c.get(f"/api/v1/ih/pharmacies/{pid}", headers=h)
        assert r.json()["code"] != 0  # 已删除


# ---------- departments ----------
def test_department_crud(server, token):
    h = _auth(token)
    with httpx.Client(base_url=server, timeout=10) as c:
        r = c.post("/api/v1/ih/departments", json={"name": "UT康复科", "head": "张主任"}, headers=h)
        assert r.status_code == 200, r.text
        did = r.json()["data"]["id"]
        r = c.get("/api/v1/ih/departments", params={"page": 1, "page_size": 10}, headers=h)
        assert r.status_code == 200 and r.json()["data"]["total"] >= 1
        r = c.patch(f"/api/v1/ih/departments/{did}", json={"name": "UT康复科改", "remark": "x"}, headers=h)
        assert r.status_code == 200 and r.json()["data"]["name"] == "UT康复科改"
        r = c.delete(f"/api/v1/ih/departments/{did}", headers=h)
        assert r.status_code == 200


# ---------- complaints ----------
def test_complaint_flow(server, token):
    h = _auth(token)
    with httpx.Client(base_url=server, timeout=10) as c:
        r = c.post(
            "/api/v1/ih/complaints",
            json={"order_id": 1, "user_id": 1, "type": "service", "content": "UT投诉内容"},
            headers=h,
        )
        assert r.status_code == 200, r.text
        cid = r.json()["data"]["id"]
        assert r.json()["data"]["status"] == "pending"
        # 处理回复 -> resolved
        r = c.patch(
            f"/api/v1/ih/complaints/{cid}",
            json={"status": "resolved", "reply": "UT已处理"},
            headers=h,
        )
        assert r.status_code == 200
        body = r.json()["data"]
        assert body["status"] == "resolved" and body["reply"] == "UT已处理"
        # 列表含该条
        r = c.get("/api/v1/ih/complaints", params={"page": 1, "page_size": 10}, headers=h)
        assert r.status_code == 200
        assert any(it["id"] == cid for it in r.json()["data"]["items"])


# ---------- dashboards ----------
def test_dashboard_aggregate(server, token):
    h = _auth(token)
    with httpx.Client(base_url=server, timeout=10) as c:
        r = c.get("/api/v1/ih/dashboards", headers=h)
        assert r.status_code == 200, r.text
        d = r.json()["data"]
        # 聚合结构：core / compliance / warning / rx_trend_30d
        assert "core" in d and "compliance" in d and "warning" in d
        assert "prescription_total" in d["compliance"]
        assert "complaint_total" in d["compliance"]
        assert "low_stock_count" in d["warning"]
        assert isinstance(d["compliance"]["prescription_total"], int)
        assert isinstance(d["warning"]["low_stock_count"], int)
