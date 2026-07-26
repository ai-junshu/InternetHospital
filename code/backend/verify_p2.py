"""P2 收尾机制级验证（不依赖外部 PG/ClickHouse 运行时）。

覆盖：
1. 新文件语法编译（backend + ai-service）。
2. RAG 可解释：retrieve / build_rationale 纯逻辑（ai-service 子进程，避免 app 包冲突）。
3. 反馈闭环：路由已注册；compute_metrics_row 纯函数正确。
4. 经营宽表：路由已注册；compute_metrics_row 幂等构造正确。

说明：pred_log 落库 / ClickHouse 写入需在 Postgres+ClickHouse 运行时验证；
本脚本验证逻辑与接线正确性，相关服务均已做降级（失败仅告警，不阻断主链路）。
"""
import os
import subprocess
import sys
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))
AI_ROOT = os.path.join(os.path.dirname(ROOT), "ai-service")

RESULTS = []


def record(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {name} {detail}")


def check_compile():
    files = [
        "app/api/v1/mt/care_plans.py",
        "app/api/v1/mt/repurchase_predictions.py",
        "app/api/v1/mt/risk_profiles.py",
        "app/api/v1/plat/model_pred_logs.py",
        "app/api/v1/mt/store_metrics.py",
        "app/api/v1/plat/__init__.py",
        "app/api/v1/mt/__init__.py",
        "app/services/pred_log.py",
        "app/services/store_metrics.py",
        "app/models/plat_models.py",
        "app/schemas/plat.py",
        "app/schemas/mt.py",
        "../ai-service/app/api/plan_recommend.py",
        "../ai-service/app/rag/retriever.py",
    ]
    ok = True
    for f in files:
        p = os.path.join(ROOT, f)
        if not os.path.exists(p):
            record(f"compile {f}", False, "文件不存在")
            ok = False
            continue
        r = subprocess.run([sys.executable, "-m", "py_compile", p], capture_output=True, text=True)
        if r.returncode != 0:
            record(f"compile {f}", False, r.stderr.strip().splitlines()[-1])
            ok = False
    if ok:
        record("compile 全部新文件", True)
    return ok


def check_rag_subprocess():
    code = (
        "from app.rag.retriever import build_query, build_rationale, retrieve\n"
        "q = build_query('腰椎', 8, 1, 65)\n"
        "hits = retrieve(q, top_k=3)\n"
        "rat = build_rationale({'version':'v1','age':65,'pain_score':8,'chronic_count':1,'pain_type':'腰椎'}, "
        "{'plan_id':'P2','title':'腰椎调理方案'}, hits)\n"
        "assert hits, '无命中'\n"
        "assert '腰椎调理方案' in rat, rat\n"
        "assert '占位' not in rat, '占位文案泄漏'\n"
        "print('RAG_OK', len(hits))\n"
    )
    r = subprocess.run(
        [sys.executable, "-c", code], cwd=AI_ROOT, capture_output=True, text=True
    )
    ok = r.returncode == 0 and "RAG_OK" in r.stdout
    record("RAG 可解释(retrieve+build_rationale)", ok, r.stdout.strip() or r.stderr.strip().splitlines()[-1])
    return ok


def check_routes_and_pure():
    import app.main  # noqa: F401
    from app.services.store_metrics import compute_metrics_row

    paths = [getattr(rt, "path", "") for rt in app.main.app.routes]
    need = [
        "/api/v1/plat/model-pred-logs",
        "/api/v1/mt/store-metrics",
    ]
    ok_routes = all(n in paths for n in need)
    record("反馈闭环+经营宽表 路由已注册", ok_routes, str([n for n in need if n not in paths]) or "ok")
    record("路由总数增加(>48)", len(paths) > 48, f"count={len(paths)}")

    row = compute_metrics_row(date(2026, 7, 26), 1, "门店A", "华东", 10, 5, 4.5, 3)
    ok_row = (
        row[0] == date(2026, 7, 26)
        and row[1] == 1
        and row[4] == 10
        and row[6] == 5
        and row[7] == 0.0
        and row[9] == 3
        and row[10] == 4.5
    )
    record("compute_metrics_row 构造正确", ok_row, str(row))
    return ok_routes and row is not None


def main():
    check_compile()
    check_rag_subprocess()
    check_routes_and_pure()
    fails = [n for n, ok, _ in RESULTS if not ok]
    print("\n==== P2 验证汇总 ====")
    print(f"总项: {len(RESULTS)}  通过: {len(RESULTS)-len(fails)}  失败: {len(fails)}")
    if fails:
        print("失败项:", fails)
        sys.exit(1)
    print("全部通过 (PASS)")


if __name__ == "__main__":
    main()
