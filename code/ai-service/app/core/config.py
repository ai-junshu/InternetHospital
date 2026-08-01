"""AI 服务配置（技术架构第6/15.4章）。"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "互联网医疗中心平台 AI 服务"
    debug: bool = False

    # MLflow registry：默认文件型存储（sqlite），开箱即用的 registry 加载闭环，
    # 无需启动 server。生产环境通过环境变量 MLFLOW_TRACKING_URI 指向 server。
    mlflow_tracking_uri: str = "sqlite:///tracking.db"
    model_registry_stage: str = "Production"
    service_port: int = 8001

    internal_token: str = "change-me-internal"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
