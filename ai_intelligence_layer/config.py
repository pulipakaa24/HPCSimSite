"""
Configuration management for AI Intelligence Layer.
Uses pydantic-settings for environment variable validation.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Gemini API Configuration
    gemini_api_key: str
    gemini_model: str = "gemini-1.5-pro"
    
    # Service Configuration
    ai_service_port: int = 9000
    ai_service_host: str = "0.0.0.0"
    
    # Enrichment Service Integration
    enrichment_service_url: str = "http://localhost:8000"
    enrichment_fetch_limit: int = 10
    
    # Demo Mode
    demo_mode: bool = False
    
    # Fast Mode (shorter prompts)
    fast_mode: bool = True
    
    # Performance Settings
    brainstorm_timeout: int = 30
    analyze_timeout: int = 60
    gemini_max_retries: int = 3
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Global settings instance
settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create settings instance."""
    global settings
    if settings is None:
        settings = Settings()
    return settings
