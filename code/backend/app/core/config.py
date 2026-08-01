"""全局配置（技术架构第10/11/14章）。

从 .env 读取，真实密钥经环境变量注入，禁止硬编码（第14.5章）。
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 始终从 backend 项目根目录解析 .env，避免依赖进程启动 cwd（Windows uvicorn 子进程 cwd 易漂移）
# config.py 位于 app/core/config.py -> parent(core).parent(app).parent(backend)
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_BACKEND_ROOT / ".env"), extra="ignore")

    # 基础
    app_name: str = "互联网医疗中心平台后端"
    api_v1_prefix: str = "/api/v1"
    debug: bool = False

    # 数据库
    postgres_uri: str = "postgresql+asyncpg://ihm:ihm_dev_pwd@localhost:5432/ihm"
    redis_uri: str = "redis://localhost:6379/0"
    mongo_uri: str = "mongodb://ihm:ihm_dev_pwd@localhost:27017/ihm?authSource=admin"
    clickhouse_uri: str = "clickhouse://ihm:ihm_dev_pwd@localhost:8123/ihm"

    # 鉴权（JWT）
    # ⚠️ 仅本地 dev 占位：32 字节强随机串（HS256 安全下限，技术架构第14.5章）。
    # 生产环境必须经由环境变量 JWT_SECRET 注入真实密钥，禁止直接使用该默认值。
    jwt_secret: str = "9f2a7c4e1b8d6a3f5c0e9d2b7a4f1c8e3b6d9a2f5c8e1b4d7a0f3c6e9b2d5a8f"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # 防重放
    replay_window_seconds: int = 300

    # 双因子（TOTP / RFC 6238，P4 安全增强）
    totp_issuer: str = "互联网医疗中心"

    # ---------------- 落库加密（KMS 信封加密，本次增强） ----------------
    # kms_provider: local（默认，本地 KMS 信封加密）/ aws（生产真实 KMS 适配器）。
    kms_provider: str = "local"
    # 主密钥(KEK)经环境变量 KMS_MASTER_KEY 注入（第14.5章，禁止硬编码）。
    # dev 占位仅本地调试；生产必须注入真实强密钥。任意字符串经 SHA-256 派生 32 字节 KEK。
    kms_master_key: str = "dev-only-kms-master-key-change-in-production-32b+"
    # 仅 kms_provider=aws 时使用：KMS Key Id（arn/alias）。
    kms_aws_key_id: str = ""

    # 合理用药引擎（第14章第三方对接）：默认 mock，生产可切换 http 并配置 base_url
    rx_engine_provider: str = "mock"
    rx_engine_base_url: str = ""

    # ---------------- P5 性能容灾：Redis 缓存 / 接口限流 ----------------
    # 缓存默认 TTL（秒）；仅缓存脱敏/聚合/参考类只读数据，绝不缓存 PII 与密文。
    cache_default_ttl: int = 60
    # 接口限流总开关（P5）。Redis 不可用时自动放行，不阻断业务。
    rate_limit_enabled: bool = True
    # 固定窗口：每 60s 窗口内允许的最大请求数。
    rate_limit_window_seconds: int = 60
    rate_limit_per_ip_per_min: int = 120
    rate_limit_per_user_per_min: int = 300
    # 限流白名单路径（逗号分隔，精确前缀匹配），默认放行探活/文档。
    rate_limit_whitelist_paths: str = "/health,/docs,/redoc,/openapi.json"

    # 微信小程序登录（第14章）
    wx_appid: str = ""
    wx_secret: str = ""

    # ---------------- 微信支付（第14章 APIv3 JSAPI，迭代 A · S5） ----------------
    # ⚠️ 以下均为 dev 占位；生产必须经由环境变量注入真实商户凭证，禁止硬编码（第14.5章）。
    wxpay_mch_id: str = ""            # 商户号
    wxpay_api_v3_key: str = ""        # APIv3 密钥（AES-GCM 解密回调用）
    wxpay_cert_serial: str = ""       # 商户证书序列号（请求签名用）
    wxpay_notify_base_url: str = ""   # 支付回调基础地址，如 https://api.example.com
    wxpay_appid: str = ""             # 拉起支付的小程序 appid（一般同 wx_appid）
    # 商户 API 私钥（pem，PKCS#8，含 -----BEGIN PRIVATE KEY-----）。
    # 经环境变量 WXPAY_PRIVATE_KEY_PATH 注入文件路径；禁止硬编码（第14.5章）。
    wxpay_private_key_path: str = ""
    # 平台证书缓存目录（自动下载的微信平台证书按 serial 缓存为 pem，避免重复下载）。
    # 默认 {backend_root}/.cache/wxpay_certs/，可用 WXPAY_CERT_CACHE_DIR 覆盖。
    wxpay_cert_cache_dir: str = str(_BACKEND_ROOT / ".cache" / "wxpay_certs")
    # dev 沙箱开关：True 时跳过真实微信调用与回调验签，用模拟 prepay/模拟回调跑通状态机。
    # 生产必须置 False 并配置真实商户凭证。
    wxpay_dev_sandbox: bool = True

    # ai-service 内部调用（第12章 MLOps）
    ai_service_base_url: str = "http://127.0.0.1:8001"

    # ---------------- P3 数据中台扩展组件连接（惰性，未编排不报错） ----------------
    iceberg_rest_uri: str = "http://localhost:8181"
    iceberg_warehouse: str = "s3://iceberg/"
    iceberg_namespace: str = "ihm"
    iceberg_s3_endpoint: str = "http://localhost:9000"
    iceberg_s3_access_key: str = "ihm"
    iceberg_s3_secret_key: str = "ihm_dev_pwd"
    milvus_uri: str = "http://localhost:19530"
    milvus_token: str = ""
    milvus_dimension: int = 768  # 与 ai-service embedding 维度对齐

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:10086"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def rate_limit_whitelist_list(self) -> list[str]:
        return [p.strip() for p in self.rate_limit_whitelist_paths.split(",") if p.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
