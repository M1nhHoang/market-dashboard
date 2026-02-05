"""
Market Intelligence Dashboard - Configuration
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Paths
    BASE_DIR: Path = Path(__file__).parent
    DATA_DIR: Path = Field(default_factory=lambda: Path(__file__).parent / "data")
    DATABASE_PATH: Path = Field(default_factory=lambda: Path(__file__).parent / "data" / "market.db")
    
    # API Keys
    ANTHROPIC_API_KEY: str = Field(default="", description="Claude API key")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO")
    
    # Crawler
    CRAWLER_INTERVAL_HOURS: int = Field(default=1)
    CRAWLERS_ENABLE_SSL: bool = Field(default=True, description="Enable SSL verification for crawlers")
    
    # LLM
    LLM_MODEL: str = Field(default="claude-sonnet-4-20250514")
    CONTEXT_LOOKBACK_DAYS: int = Field(default=7)
    
    # API
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=8000)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Global settings instance
settings = Settings()


def ensure_directories():
    """Ensure all required directories exist."""
    dirs = [
        settings.DATA_DIR,
        settings.DATA_DIR / "raw",
        settings.DATA_DIR / "processed",
        settings.DATA_DIR / "context",
    ]
    for dir_path in dirs:
        dir_path.mkdir(parents=True, exist_ok=True)
