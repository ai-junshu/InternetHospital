"""AI 服务配置（技术架构第6/15.4章）。"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "互联网医疗中心平台 AI 服务"
    debug: bool = False

    mlflow_tracking_uri: str = "http://localhost:5000"
    model_registry_stage: str = "Production"
    service_port: int = 8001

    internal_token: str = "change-me-internal"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
