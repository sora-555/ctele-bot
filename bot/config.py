"""Runtime configuration, loaded from `.env` (see `.env.example`)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    bot_token: str = ""
    admin_ids: str = ""
    log_channel_id: str = ""
    database_url: str = "sqlite+aiosqlite:///Database.db"

    source_base_url: str = "https://cosplaytele.com"
    source_referer: str = ""
    source_user_agent: str = ""
    request_timeout: float = 20.0
    max_retries: int = 2
    source_concurrency: int = 8

    run_mode: str = "polling"
    api_host: str = "0.0.0.0"
    api_port: int = 8080
    webhook_base_url: str = ""
    webhook_path: str = "/webhook"
    webhook_secret: str = ""
    webhook_drop_pending: bool = True
    webhook_delete_on_shutdown: bool = False

    set_commands_on_startup: bool = True
    command_scope_admins: bool = True

    throttle_rate: int = 6
    throttle_period: float = 10.0
    items_per_page: int = 6
    images_per_page: int = 5
    default_delivery_mode: str = "album"
    search_select_target: str = "gallery"
    search_thumbnails: bool = True
    image_fallback_upload: bool = True
    age_gate: bool = True
    maintenance: bool = False

    listing_cache_ttl: int = 300
    post_cache_ttl: int = 86400
    category_cache_ttl: int = 21600
    session_ttl: int = 1800

    auto_delete_enabled: bool = True
    auto_delete_ttl_minutes: int = 30
    auto_delete_scope: str = "media"
    auto_delete_sweep_interval: int = 60

    broadcast_rate: int = 20
    log_level: str = "INFO"
    log_dir: str = "logs"

    @property
    def log_channel(self) -> int | None:
        """LOG_CHANNEL_ID accepts an empty value in .env; parse it leniently."""
        raw = self.log_channel_id.strip()
        if not raw:
            return None
        try:
            return int(raw)
        except ValueError:
            return None

    @property
    def owner_ids(self) -> list[int]:
        ids: list[int] = []
        for chunk in self.admin_ids.replace(";", ",").split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            try:
                ids.append(int(chunk))
            except ValueError:
                continue
        return ids

    @property
    def resolved_referer(self) -> str:
        return self.source_referer or f"{self.source_base_url.rstrip('/')}/"

    @property
    def is_webhook(self) -> bool:
        return self.run_mode.strip().lower() == "webhook"

    @property
    def webhook_url(self) -> str:
        if not self.webhook_base_url:
            return ""
        path = self.webhook_path if self.webhook_path.startswith("/") else f"/{self.webhook_path}"
        return f"{self.webhook_base_url.rstrip('/')}{path}"

    def validate_runtime(self) -> list[str]:
        """Pre-flight checks. Returns a list of fatal problems."""
        problems: list[str] = []
        if not self.bot_token or ":" not in self.bot_token:
            problems.append("BOT_TOKEN is missing or malformed")
        if self.is_webhook and not self.webhook_url:
            problems.append("RUN_MODE=webhook requires WEBHOOK_BASE_URL")
        if self.api_port <= 0 or self.api_port > 65535:
            problems.append("API_PORT is out of range")
        return problems

    def warnings(self) -> list[str]:
        notes: list[str] = []
        if not self.owner_ids:
            notes.append("ADMIN_IDS is empty - nobody can reach the admin commands")
        if self.log_channel is None:
            notes.append("LOG_CHANNEL_ID is not set - admin actions are DB-only")
        return notes


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()