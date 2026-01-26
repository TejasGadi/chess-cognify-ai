"""
Application configuration using Pydantic Settings.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "chess-cognify-ai"
    app_env: str = "development"
    debug: bool = True
    log_level: str = "INFO"
    secret_key: str = "change-me-in-production"

    # Database
    database_url: str = "postgresql://chess_user:chess_password@localhost:5432/chess_cognify"
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_cache_ttl: int = 86400  # 24 hours

    # Stockfish Engine
    stockfish_path: str = "/usr/local/bin/stockfish"  # Can be overridden via STOCKFISH_PATH env var
    stockfish_depth: int = 18
    stockfish_threads: int = 4
    stockfish_hash: int = 256  # MB
    stockfish_timeout: int = 30  # seconds

    # LLM Providers - Groq (primary and alternative with different models)
    llm_provider: str = "groq"  # groq (primary)
    groq_api_key: Optional[str] = None
    groq_model: str = "llama-3.1-70b-versatile"  # Primary model
    groq_alternative_model: str = "mixtral-8x7b-32768"  # Alternative model

    # LLM Settings
    llm_temperature: float = 0.7
    llm_max_tokens: int = 500

    # Vector Database (Books) - Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: Optional[str] = None
    qdrant_collection_name: str = "chess_books"

    # Embedding Model - Ollama (Local)
    ollama_base_url: str = "http://localhost:11434"
    ollama_embedding_model: str = "bge-m3"

    # Security
    api_key_expiration_hours: int = 24

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:8000"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins string into list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


# Global settings instance
settings = Settings()
