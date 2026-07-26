"""健康检查测试（统一响应 + isAssist 校验，第10.3章）。"""
from fastapi.testclient import TestClient

from app.main import app


def test_health():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["status"] == "ok"


def test_repurchase_is_assist():
    client = TestClient(app)
    resp = client.get("/repurchase-prediction?customer_id=1")
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["isAssist"] is True
