"""Configuration management for the TNR Tracker."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql://tnr_user:tnr_secure_password_2024@localhost:5432/tnr_tracker"
    db_pool_size: int = 5
    db_max_overflow: int = 10

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = False
    api_title: str = "NK-Russia TNR Tracker API"
    api_version: str = "0.1.0"

    # External APIs
    data_go_kr_api_key: str = "55620ffd8bd0d266e4981c0d47122317349e75f35cc7b855ada3b9f0453f1c4e"
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

    # ETL Configuration
    etl_batch_size: int = 100
    etl_retry_attempts: int = 3
    etl_retry_delay_seconds: int = 5

    # PDF Processing
    pdf_output_dir: str = "./data/processed"
    chunk_size_tokens: int = 500
    chunk_overlap_tokens: int = 50

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
