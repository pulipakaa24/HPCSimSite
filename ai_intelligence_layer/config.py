"""
Configuration management for AI Intelligence Layer.
Uses pydantic-settings for environment variable validation.
Environment variables are loaded via load_dotenv() in main.py.
Automatically adapts URLs for development vs production environments.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Environment Configuration
    environment: str = "development"  # "development" or "production"
    production_url: Optional[str] = None  # e.g., "https://your-app.onrender.com"
    
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
    
    # Strategy Generation Settings
    strategy_count: int = 3  # Number of strategies to generate (3 for testing, 20 for production)
    
    # Performance Settings
    brainstorm_timeout: int = 30
    analyze_timeout: int = 60
    gemini_max_retries: int = 3
    
    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore"
    )
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"
    
    @property
    def base_url(self) -> str:
        """Get the base URL for the application."""
        if self.is_production and self.production_url:
            return self.production_url
        return f"http://localhost:{self.ai_service_port}"
    
    @property
    def websocket_url(self) -> str:
        """Get the WebSocket URL for the application."""
        if self.is_production and self.production_url:
            # Replace https:// with wss:// or http:// with ws://
            return self.production_url.replace("https://", "wss://").replace("http://", "ws://")
        return f"ws://localhost:{self.ai_service_port}"
    
    @property
    def internal_enrichment_url(self) -> str:
        """Get the enrichment service URL (internal on Render)."""
        if self.is_production:
            # On Render, services communicate internally via localhost
            return "http://localhost:8000"
        return self.enrichment_service_url


# Global settings instance
settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create settings instance."""
    global settings
    if settings is None:
        settings = Settings()
    return settings
