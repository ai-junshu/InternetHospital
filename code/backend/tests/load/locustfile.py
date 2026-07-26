"""P5 压测 harness（locust）。

覆盖核心端点，用于容量评估与限流验证。仅 dev 依赖（pip install -e ".[dev]"）。

运行示例（headless 短脉冲）：
    locust -f tests/load/locustfile.py --headless -u 50 -r 10 -t 30s -H http://localhost:8000

说明：
  - /health 在白名单，不应触发 429，用于基线吞吐。
  - /api/v1/auth/login 与 /api/v1/ih/users/me 等受接口限流保护，
    高频压测会返回 429（可在统计中观察，验证限流生效）。
  - 需鉴权端点：设置环境变量 IHM_TOKEN（有效 JWT）后才启用。
"""
import os

from locust import HttpUser, between, task


BASE = os.getenv("IHM_BASE_URL", "http://localhost:8000")
TOKEN = os.getenv("IHM_TOKEN", "")
HEADERS = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}


class IhmUser(HttpUser):
    host = BASE
    # 思考时间：模拟真实用户间隔
    wait_time = between(0.5, 2.0)

    @task(5)
    def health(self):
        # 白名单路径，基线吞吐，预期不触发限流
        self.client.get("/health")

    @task(3)
    def login(self):
        # 受限流保护，高频将返回 429
        self.client.post(
            "/api/v1/auth/login",
            json={"username": "demo", "password": "demo"},
        )

    @task(2)
    def me(self):
        if not TOKEN:
            return
        # 命中 Redis 缓存（per-user），验证缓存命中不被打到 DB
        self.client.get("/api/v1/ih/users/me", headers=HEADERS)

    @task(2)
    def data_assets(self):
        if not TOKEN:
            return
        self.client.get("/api/v1/plat/data-assets", headers=HEADERS)
