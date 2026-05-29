from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DATABASE_URL = 'postgresql+psycopg://<user>:<password>@brobier-db-dev:5432/brobier_dev'


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', case_sensitive=True)
    db_host: str = Field(default='localhost', alias='DB_HOST')
    db_name: str = Field(default='brobier_dev', alias='DB_NAME')
    db_port: str = Field(default='5432', alias='DB_PORT')
    db_user: str | None = Field(default=None, alias='DB_USER')
    db_password: str | None = Field(default=None, alias='DB_PASSWORD')

    beer_encryption_key: str | None = Field(default=None, alias='BEER_ENCRYPTION_KEY')

    jwt_secret: str = Field(default='a cold beer a day keeps the doctor away, but two keeps the bugs at bay', alias='JWT_SECRET')

    session_expire_seconds: int = Field(default=604800, alias='SESSION_EXPIRE_SECONDS')

    smtp_host: str = Field(default='mailpit', alias='SMTP_HOST')
    smtp_port: int = Field(default=1025, alias='SMTP_PORT')
    smtp_from: str = Field(default='noreply@brobier.local', alias='SMTP_FROM')
    smtp_use_tls: bool = Field(default=False, alias='SMTP_USE_TLS')

    login_code_expire_minutes: int = Field(default=10, alias='LOGIN_CODE_EXPIRE_MINUTES')

    cors_origins: list[str] = Field(default_factory=lambda: ['http://localhost'], alias='CORS_ORIGINS')

    env: Literal['dev', 'tst', 'prd'] = Field(default='dev', alias='ENV')

    # Set DB_RECREATE=true to drop and recreate all tables on startup.
    # Never use in production — all data will be lost. Only use in dev or test.
    db_overwrite: bool = Field(default=False, alias='DB_OVERWRITE')

    @field_validator('cors_origins', mode='before')
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        return [origin.strip() for origin in value.split(',') if origin.strip()]

    @property
    def database_url(self) -> str:
        return f'postgresql+psycopg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}'


@lru_cache
def get_settings() -> Settings:
    return Settings()
