"""P1 复购预测回写验证：调用 AI 服务 → 落 mt_repurchase_prediction → 列表查询。"""
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

    # 1) 触发 AI 复购预测并回写
    r = c.post(
        "/mt/repurchase-predictions",
        json={"customer_id": 1, "age": 52, "visit_freq": 2.5, "last_gap_days": 45.0},
    )
    data = ok(r, "POST 复购预测")
    print("  复购概率:", data.get("repurchase_prob"), "复诊概率:", data.get("next_visit_prob"),
          "风险等级:", data.get("risk_level"), "模型版本:", data.get("model_version"))

    # 2) 列表查询
    r2 = c.get("/mt/repurchase-predictions", params={"customer_id": 1})
    d2 = ok(r2, "GET 列表")
    print("  列表总数:", d2.get("total"), "条目数:", len(d2.get("items", [])))
    assert d2.get("total") >= 1

    print("\n=== 复购预测回写 P1 验证 ALL PASS ===")


if __name__ == "__main__":
    main()
