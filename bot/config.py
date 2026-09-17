from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    bot_token: str = Field('', validation_alias='BOT_TOKEN')
    bot_username: str = Field('', validation_alias='BOT_USERNAME')
    admin_ids: str = Field('', validation_alias='ADMIN_IDS')
    log_channel_id: str = Field('', validation_alias='LOG_CHANNEL_ID')

    database_url: str = Field('sqlite+aiosqlite:///Database.db', validation_alias='DATABASE_URL')

    source_base_url: str = Field('https://cosplaytele.com', validation_alias='SOURCE_BASE_URL')
    source_user_agent: str = Field('CosplayTeleBot/1.0', validation_alias='SOURCE_USER_AGENT')
    source_referer: str = Field('', validation_alias='SOURCE_REFERER')
    request_timeout: float = Field(20, validation_alias='REQUEST_TIMEOUT')
    max_retries: int = Field(2, validation_alias='MAX_RETRIES')
    source_concurrency: int = Field(8, validation_alias='SOURCE_CONCURRENCY')

    run_mode: str = Field('polling', validation_alias='RUN_MODE')
    api_host: str = Field('0.0.0.0', validation_alias='API_HOST')
    api_port: int = Field(8080, validation_alias='API_PORT')
    webhook_base_url: str = Field('', validation_alias='WEBHOOK_BASE_URL')
    webhook_path: str = Field('/webhook', validation_alias='WEBHOOK_PATH')
    webhook_secret: str = Field('', validation_alias='WEBHOOK_SECRET')
    webhook_drop_pending: bool = Field(True, validation_alias='WEBHOOK_DROP_PENDING')
    webhook_delete_on_shutdown: bool = Field(False, validation_alias='WEBHOOK_DELETE_ON_SHUTDOWN')

    session_ttl: int = Field(1800, validation_alias='SESSION_TTL')
    items_per_page: int = Field(6, validation_alias='ITEMS_PER_PAGE')
    images_per_page: int = Field(5, validation_alias='IMAGES_PER_PAGE')
    default_delivery_mode: str = Field('single', validation_alias='DEFAULT_DELIVERY_MODE')
    search_thumbnails: bool = Field(True, validation_alias='SEARCH_THUMBNAILS')
    age_gate: bool = Field(False, validation_alias='AGE_GATE')
    maintenance: bool = Field(False, validation_alias='MAINTENANCE')

    throttle_rate: int = Field(6, validation_alias='THROTTLE_RATE')
    throttle_period: float = Field(10, validation_alias='THROTTLE_PERIOD')

    nav_window_size: int = Field(5, validation_alias='NAV_WINDOW_SIZE')
    nav_short_list_threshold: int = Field(7, validation_alias='NAV_SHORT_LIST_THRESHOLD')
    nav_numbers_per_row: int = Field(5, validation_alias='NAV_NUMBERS_PER_ROW')
    nav_page_jump: bool = Field(True, validation_alias='NAV_PAGE_JUMP')

    listing_cache_ttl: int = Field(300, validation_alias='LISTING_CACHE_TTL')
    post_cache_ttl: int = Field(86400, validation_alias='POST_CACHE_TTL')
    category_cache_ttl: int = Field(21600, validation_alias='CATEGORY_CACHE_TTL')

    auto_delete_enabled: bool = Field(True, validation_alias='AUTO_DELETE_ENABLED')
    auto_delete_ttl_minutes: int = Field(30, validation_alias='AUTO_DELETE_TTL_MINUTES')
    auto_delete_sweep_interval: int = Field(60, validation_alias='AUTO_DELETE_SWEEP_INTERVAL')

    broadcast_rate: int = Field(20, validation_alias='BROADCAST_RATE')

    set_commands_on_startup: bool = Field(True, validation_alias='SET_COMMANDS_ON_STARTUP')
    command_scope_admins: bool = Field(True, validation_alias='COMMAND_SCOPE_ADMINS')

    log_level: str = Field('INFO', validation_alias='LOG_LEVEL')
    log_dir: str = Field('logs', validation_alias='LOG_DIR')

    @property
    def admin_id_list(self) -> list[int]:
        return [int(x.strip()) for x in self.admin_ids.split(',') if x.strip().lstrip('-').isdigit()]

    @property
    def log_channel(self) -> int | None:
        value = self.log_channel_id.strip()
        return int(value) if value.lstrip('-').isdigit() else None


settings = Settings()
