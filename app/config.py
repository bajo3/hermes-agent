from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "hermes-secretario"
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/hermes",
        alias="DATABASE_URL",
    )
    secret_key: str = Field(default="change_me", alias="SECRET_KEY")
    env: str = Field(default="development", alias="ENV")
    telegram_bot_token: Optional[str] = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    admin_telegram_id: Optional[int] = Field(default=None, alias="ADMIN_TELEGRAM_ID")
    timezone: str = Field(default="America/Argentina/Buenos_Aires", alias="TIMEZONE")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql://", 1)
        return value

    @field_validator("admin_telegram_id", mode="before")
    @classmethod
    def empty_admin_id_is_none(cls, value: object) -> object:
        if value == "":
            return None
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()

