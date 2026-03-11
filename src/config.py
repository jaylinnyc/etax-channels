"""Configuration management using Pydantic settings."""
from pydantic import Field

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Telegram Bot Configuration
    telegram_bot_token: str
    internal_api_key: str = Field(..., env="INTERNAL_API_KEY")

    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    
    # Invoice Service Configuration
    invoice_service_url: str = "http://etax:9443/api/v1/xml"
    settings_service_url: str
    
    # Bot Configuration
    conversation_timeout: int = 3600  # 1 hour in seconds
    invoice_history_ttl: int = 86400  # 24 hours in seconds
    max_retry_attempts: int = 3
    
    # Logging
    log_level: str = "INFO"


# Global settings instance
settings = Settings()
