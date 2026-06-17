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
    admin_whatsapp_number: Optional[str] = Field(default=None, alias="ADMIN_WHATSAPP_NUMBER")
    whatsapp_bridge_token: str = Field(default="change_me_bridge_token", alias="WHATSAPP_BRIDGE_TOKEN")
    bridge_url: str = Field(default="http://host.docker.internal:8765", alias="BRIDGE_URL")
    bridge_token: str = Field(default="change_me_windows_bridge_token", alias="BRIDGE_TOKEN")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    default_clients_folder: str = Field(default=r"C:\Hermes\Clientes", alias="DEFAULT_CLIENTS_FOLDER")
    default_backup_folder: str = Field(default=r"C:\Hermes\Backups", alias="DEFAULT_BACKUP_FOLDER")
    default_exports_folder: str = Field(default=r"C:\Hermes\Exports", alias="DEFAULT_EXPORTS_FOLDER")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-5.4-mini", alias="OPENAI_MODEL")
    ai_enabled: bool = Field(default=True, alias="AI_ENABLED")
    ai_provider: str = Field(default="openai", alias="AI_PROVIDER")
    hermes_cli_path: str = Field(default="/home/bajo31/.local/bin/hermes", alias="HERMES_CLI_PATH")
    hermes_cli_command: Optional[str] = Field(default=None, alias="HERMES_CLI_COMMAND")
    hermes_cli_provider: str = Field(default="openai-codex", alias="HERMES_CLI_PROVIDER")
    hermes_cli_model: str = Field(default="gpt-5.5", alias="HERMES_CLI_MODEL")
    hermes_cli_timeout: int = Field(default=120, alias="HERMES_CLI_TIMEOUT")
    hermes_cli_cwd: str = Field(default="/home/bajo31/.hermes/hermes-agent", alias="HERMES_CLI_CWD")
    hermes_cli_bridge_url: str = Field(default="http://host.docker.internal:8766/interpret", alias="HERMES_CLI_BRIDGE_URL")
    hermes_cli_bridge_token: Optional[str] = Field(default=None, alias="HERMES_CLI_BRIDGE_TOKEN")
    timezone: str = Field(default="America/Argentina/Buenos_Aires", alias="TIMEZONE")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
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
