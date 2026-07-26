"""P1 风险画像回写验证（进程内 TestClient，直连 app + 真实 ai-service:8001）。"""
from fastapi.testclient import TestClient

from app.main import app

BASE = "/api/v1"


def main():
    with TestClient(app) as c:
        # 1) AI 风险画像 → 回写 mt_risk_profile
        r = c.post(
            f"{BASE}/mt/risk-profiles",
            json={"customer_id": 1, "age": 65, "bmi": 30.0, "comorbidity_count": 3},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("code") == 0, body
        data = body["data"]
        print("[POST 风险画像]", data)
        print("  疼痛风险:", data.get("pain_risk"), "共病风险:", data.get("comorbidity_risk"),
              "模型版本:", data.get("model_version"))
        assert data.get("pain_risk") in ("high", "medium", "low")
        assert data.get("comorbidity_risk") in ("high", "medium", "low")

        # 2) 列表查询
        r2 = c.get(f"{BASE}/mt/risk-profiles", params={"customer_id": 1})
        assert r2.status_code == 200, r2.text
        d2 = r2.json()["data"]
        print("[GET 列表] total:", d2["total"], "items:", len(d2["items"]))
        assert d2["total"] >= 1

    print("\n=== 风险画像回写 P1 验证 ALL PASS (TestClient) ===")


if __name__ == "__main__":
    main()
