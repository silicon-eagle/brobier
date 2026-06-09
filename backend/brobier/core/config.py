from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DATABASE_URL = 'postgresql+psycopg://<user>:<password>@brobier-db-dev:5432/brobier_dev'


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file_encoding='utf-8', case_sensitive=True, extra='ignore')
    db_host: str = Field(default='localhost', alias='DB_HOST')
    db_name: str = Field(default='brobier_dev', alias='DB_NAME')
    db_port: str = Field(default='5432', alias='DB_PORT')
    postgres_app_user: str | None = Field(default=None, alias='POSTGRES_APP_USER')
    postgres_app_password: str | None = Field(default=None, alias='POSTGRES_APP_PASSWORD')
    postgres_admin_user: str | None = Field(default=None, alias='POSTGRES_ADMIN_USER')
    postgres_admin_password: str | None = Field(default=None, alias='POSTGRES_ADMIN_PASSWORD')

    beer_encryption_key: str | None = Field(default=None, alias='BEER_ENCRYPTION_KEY')

    jwt_secret: str = Field(default='a cold beer a day keeps the doctor away, but two keeps the bugs at bay', alias='JWT_SECRET')

    jwt_access_expire_minutes: int = Field(default=60, alias='JWT_ACCESS_EXPIRE_MINUTES')
    jwt_refresh_expire_days: int = Field(default=7, alias='JWT_REFRESH_EXPIRE_DAYS')
    jwt_refresh_cookie_name: str = Field(default='brobier_refresh', alias='JWT_REFRESH_COOKIE_NAME')

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

    def _build_database_url(self, user: str | None, password: str | None) -> str:
        return f'postgresql+psycopg://{user}:{password}@{self.db_host}:{self.db_port}/{self.db_name}'

    @property
    def app_database_url(self) -> str:
        return self._build_database_url(self.postgres_app_user, self.postgres_app_password)

    @property
    def admin_database_url(self) -> str:
        return self._build_database_url(self.postgres_admin_user, self.postgres_admin_password)

    @property
    def database_url(self) -> str:
        return self.app_database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
