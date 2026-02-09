"""Application configuration using Pydantic Settings"""

from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "CheziousBot"
    app_version: str = "1.0.0"
    debug: bool = False

    # Groq API Configuration
    groq_api_key: str
    groq_model: str = "llama-3.1-8b-instant"
    groq_max_tokens: int = 2048
    groq_temperature: float = 0.6

    @field_validator("groq_api_key")
    @classmethod
    def validate_groq_api_key(cls, v: str) -> str:
        """Validate that GROQ_API_KEY is configured properly."""
        if not v or v.strip() == "" or v.startswith("your_"):
            raise ValueError(
                "GROQ_API_KEY is not configured. Please set it in .env file"
            )
        return v

    # Database
    database_url: str = "sqlite+aiosqlite:///./cheziousbot.db"

    # Context Management
    context_window_size: int = 10
    max_message_length: int = 500

    # Rate Limiting
    rate_limit_per_minute: int = 20

    # Logging
    log_level: str = "INFO"

    # CORS
    allowed_origins: list[str] = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://chezious-bot.onrender.com",
        "https://chezious-bot.onrender.com/",
    ]

    # API Security
    api_key_enabled: bool = True
    api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    @lru_cache (Least Recently Used Cache) Explanation:
    ---------------------------------------------------
    This decorator caches the result of this function IN MEMORY (RAM).
    
    *   **Where is it cached?** inside the Python process itself. It is specific to this running instance of the app.
    *   **No Redis Required:** This is a standard Python feature (`functools`), not an external service.
    
    1. The FIRST time this is called, it executes `Settings()`, which reads the .env file (expensive operation).
    2. FUTURE calls return the stored `Settings` object instantly from memory.
    
    Why: Improves performance by avoiding re-reading the .env file on every request.
    """
    return Settings()


settings = get_settings()
