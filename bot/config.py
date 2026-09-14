from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')
    bot_token: str = Field('', validation_alias='BOT_TOKEN')
    admin_ids: str = Field('', validation_alias='ADMIN_IDS')
    database_url: str = Field('sqlite+aiosqlite:///Database.db', validation_alias='DATABASE_URL')
    source_base_url: str = Field('https://cosplaytele.com', validation_alias='SOURCE_BASE_URL')
    source_user_agent: str = Field('CosplayTeleBot/1.0', validation_alias='SOURCE_USER_AGENT')
    request_timeout: float = Field(20, validation_alias='REQUEST_TIMEOUT')
    max_retries: int = Field(2, validation_alias='MAX_RETRIES')
    run_mode: str = Field('polling', validation_alias='RUN_MODE')
    api_host: str = Field('0.0.0.0', validation_alias='API_HOST')
    api_port: int = Field(8080, validation_alias='API_PORT')
    webhook_base_url: str = Field('', validation_alias='WEBHOOK_BASE_URL')
    webhook_path: str = Field('/webhook', validation_alias='WEBHOOK_PATH')
    webhook_secret: str = Field('', validation_alias='WEBHOOK_SECRET')
    session_ttl: int = Field(1800, validation_alias='SESSION_TTL')
    items_per_page: int = Field(6, validation_alias='ITEMS_PER_PAGE')
    default_delivery_mode: str = Field('single', validation_alias='DEFAULT_DELIVERY_MODE')
    auto_delete_enabled: bool = Field(True, validation_alias='AUTO_DELETE_ENABLED')
    auto_delete_ttl_minutes: int = Field(30, validation_alias='AUTO_DELETE_TTL_MINUTES')
    log_level: str = Field('INFO', validation_alias='LOG_LEVEL')
    @property
    def admin_id_list(self) -> list[int]:
        return [int(x.strip()) for x in self.admin_ids.split(',') if x.strip().isdigit()]

settings = Settings()
