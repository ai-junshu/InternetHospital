"""P1 风险画像回写验证：调用 AI 服务 → 落 mt_risk_profile → 列表查询。"""
import httpx

BASE = "http://127.0.0.1:8000/api/v1"


def ok(resp, label):
    print(f"[{label}] status={resp.status_code}")
    body = resp.json()
    print("  ->", body)
    assert body.get("code") == 0, f"{label} 失败: {body}"
    return body["data"]


def main():
    c = httpx.Client(timeout=60, base_url=BASE)

    r = c.post(
        "/mt/risk-profiles",
        json={"customer_id": 1, "age": 65, "bmi": 30.0, "comorbidity_count": 3},
    )
    data = ok(r, "POST 风险画像")
    print("  疼痛风险:", data.get("pain_risk"), "共病风险:", data.get("comorbidity_risk"),
          "模型版本:", data.get("model_version"))

    r2 = c.get("/mt/risk-profiles", params={"customer_id": 1})
    d2 = ok(r2, "GET 列表")
    print("  列表总数:", d2.get("total"), "条目数:", len(d2.get("items", [])))
    assert d2.get("total") >= 1

    print("\n=== 风险画像回写 P1 验证 ALL PASS ===")


if __name__ == "__main__":
    main()
