from functools import lru_cache
from typing import Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM (OpenAI-compatible)
    LLM_API_KEY: SecretStr = Field(..., description="LLM API key (OpenAI-compatible)")
    LLM_BASE_URL: str = Field(default="https://api.deepseek.com")
    LLM_MODEL: str = Field(default="deepseek-chat")

    # MySQL
    MYSQL_HOST: str = Field(default="localhost")
    MYSQL_PORT: int = Field(default=3306)
    MYSQL_USER: str = Field(default="root")
    MYSQL_PASSWORD: SecretStr = Field(default=SecretStr("root123"))
    MYSQL_DATABASE: str = Field(default="eduagent")

    # Redis
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)

    # Qdrant
    QDRANT_HOST: str = Field(default="localhost")
    QDRANT_PORT: int = Field(default=6333)

    # App settings
    LOG_LEVEL: str = Field(default="INFO")
    ENVIRONMENT: str = Field(default="development")

    # JWT Auth
    JWT_SECRET: SecretStr = Field(default=SecretStr("eduagent-default-secret-change-in-production"))

    # Optional light LLM for Phase 2 model routing
    LIGHT_LLM_ENDPOINT: Optional[str] = Field(default=None)
    LIGHT_LLM_API_KEY: Optional[SecretStr] = Field(default=None)
    LIGHT_LLM_MODEL: Optional[str] = Field(default=None)

    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        password = self.MYSQL_PASSWORD.get_secret_value()
        return (
            f"mysql+aiomysql://{self.MYSQL_USER}:{password}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
        )

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    @property
    def QDRANT_URL(self) -> str:
        return f"http://{self.QDRANT_HOST}:{self.QDRANT_PORT}"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
