from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql://lsp_user:lsp_password@localhost:5432/lsp_swimlanes"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"
    webhook_timeout: int = 30
    webhook_retry_attempts: int = 3

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
