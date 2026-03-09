"""
Model Configuration database model.
Stores provider configs for LLM, Embedding, and Vision models.
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from app.models.base import Base


class ModelConfig(Base):
    """Stores model provider configurations with encrypted API keys."""

    __tablename__ = "model_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_type = Column(String, nullable=False, index=True)  # "llm", "embedding", "vision"
    provider = Column(String, nullable=False)  # "openai", "gemini", "groq", "ollama", "anthropic", "deepseek"
    model_name = Column(String, nullable=False)  # e.g. "gpt-4o-mini"
    api_key_encrypted = Column(Text, nullable=True)  # Fernet-encrypted API key
    api_base = Column(String, nullable=True)  # Custom base URL (e.g. Ollama)
    extra_params = Column(JSON, nullable=True)  # Additional params (api_version, etc.)
    is_active = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<ModelConfig(id={self.id}, type={self.config_type}, provider={self.provider}, model={self.model_name}, active={self.is_active})>"
