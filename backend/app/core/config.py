from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True
    )

    database_url: str = Field(alias="DATABASE_URL")

    session_cookie_name: str = Field(
        default="brobier_session", alias="SESSION_COOKIE_NAME"
    )
    session_secret: str = Field(alias="SESSION_SECRET")
    session_expire_seconds: int = Field(default=604800, alias="SESSION_EXPIRE_SECONDS")

    beer_encryption_key: str = Field(alias="BEER_ENCRYPTION_KEY")

    smtp_host: str = Field(default="mailpit", alias="SMTP_HOST")
    smtp_port: int = Field(default=1025, alias="SMTP_PORT")
    smtp_from: str = Field(alias="SMTP_FROM")
    smtp_use_tls: bool = Field(default=False, alias="SMTP_USE_TLS")

    login_code_expire_minutes: int = Field(
        default=10, alias="LOGIN_CODE_EXPIRE_MINUTES"
    )

    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost"], alias="CORS_ORIGINS"
    )

    environment: Literal["development", "test", "production"] = Field(
        default="development", alias="ENVIRONMENT"
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        return [origin.strip() for origin in value.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
