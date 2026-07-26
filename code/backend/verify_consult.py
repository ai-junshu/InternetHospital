"""在线复诊闭环端到端验证（仅本地验证用，跑完删除）。"""
import httpx, time

BASE = "http://127.0.0.1:8000/api/v1"
fails = []
UID = str(int(time.time() * 1000))


def check(name, cond, detail=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {name} {detail}")
    if not cond:
        fails.append(name)


with httpx.Client(timeout=30) as c:
    # 1. 患者注册
    r = c.post(f"{BASE}/ih/users", json={"openid": f"dev_pat_{UID}", "user_type": "patient"})
    check("create patient", r.status_code == 200, r.text[:120])
    patient_id = r.json()["data"]["id"]

    # 2. 医师注册
    r = c.post(f"{BASE}/ih/users", json={"openid": f"dev_doc_{UID}", "user_type": "doctor"})
    doc_user_id = r.json()["data"]["id"]
    r = c.post(f"{BASE}/ih/doctors", json={"user_id": doc_user_id, "license_no": f"LIC-{UID}", "title": "主治"})
    check("create doctor", r.status_code == 200, r.text[:120])
    doctor_id = r.json()["data"]["id"]

    # 3. 创建问诊会话
    r = c.post(f"{BASE}/ih/consultations", json={
        "patient_id": patient_id, "doctor_id": doctor_id, "chief_complaint": "复诊配药"
    })
    check("create consultation", r.status_code == 200, r.text[:160])
    cid = r.json()["data"]["id"]
    check("consult status open", r.json()["data"]["status"] == "open")

    # 4. 列表查询
    r = c.get(f"{BASE}/ih/consultations", params={"patient_id": patient_id})
    check("list consultations", r.status_code == 200 and r.json()["data"]["total"] >= 1)

    # 5. 发送消息（患者→医师）
    r = c.post(f"{BASE}/ih/consultations/{cid}/messages", json={
        "sender_role": "patient", "sender_id": patient_id, "msg_type": "text", "content": "医生我复查结果"
    })
    check("send msg patient", r.status_code == 200)
    r = c.post(f"{BASE}/ih/consultations/{cid}/messages", json={
        "sender_role": "doctor", "sender_id": doctor_id, "msg_type": "text", "content": "好的，请稍候开方"
    })
    check("send msg doctor", r.status_code == 200)

    # 6. 消息列表
    r = c.get(f"{BASE}/ih/consultations/{cid}/messages")
    check("list messages", r.status_code == 200 and r.json()["data"]["total"] == 2)

    # 7. 医师接诊
    r = c.patch(f"{BASE}/ih/consultations/{cid}/start", params={"doctor_id": doctor_id})
    check("start consultation", r.status_code == 200 and r.json()["data"]["status"] == "ongoing")

    # 8. 结束后不可再发消息
    r = c.patch(f"{BASE}/ih/consultations/{cid}/end", params={"doctor_id": doctor_id})
    check("end consultation", r.status_code == 200 and r.json()["data"]["status"] == "ended")
    r = c.post(f"{BASE}/ih/consultations/{cid}/messages", json={
        "sender_role": "patient", "sender_id": patient_id, "msg_type": "text", "content": "x"
    })
    check("block msg after end", r.status_code == 200 and r.json().get("code") != 0, r.text[:120])

    # 9. 异常：非法 msg_type
    r2 = c.post(f"{BASE}/ih/consultations/{cid}/messages", json={
        "sender_role": "patient", "sender_id": patient_id, "msg_type": "video", "content": "x"
    })
    check("reject bad msg_type", r2.status_code == 200 and r2.json().get("code") != 0, f"status={r2.status_code}")

print("\n=== RESULT:", "ALL PASS" if not fails else f"FAILED {fails}")
