"""
Pydantic schemas for Model Configuration API.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class ModelConfigCreate(BaseModel):
    """Schema for creating/updating a model config."""
    config_type: str = Field(..., description="One of: llm, embedding, vision")
    provider: str = Field(..., description="Provider name: openai, gemini, groq, ollama, anthropic, deepseek")
    model_name: str = Field(..., description="Model identifier e.g. gpt-4o-mini")
    api_key: Optional[str] = Field(None, description="API key (will be encrypted)")
    api_base: Optional[str] = Field(None, description="Custom base URL")
    extra_params: Optional[Dict[str, Any]] = Field(None, description="Additional parameters")


class ModelConfigResponse(BaseModel):
    """Schema for returning a model config (API key masked)."""
    id: int
    config_type: str
    provider: str
    model_name: str
    api_key_masked: Optional[str] = None
    api_base: Optional[str] = None
    extra_params: Optional[Dict[str, Any]] = None
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ActiveModelsResponse(BaseModel):
    """Schema for returning the currently active models."""
    llm: Optional[ModelConfigResponse] = None
    embedding: Optional[ModelConfigResponse] = None
    vision: Optional[ModelConfigResponse] = None


class ProviderField(BaseModel):
    """Describes a field required by a provider."""
    name: str
    label: str
    type: str = "text"  # "text", "password", "url"
    required: bool = True
    placeholder: str = ""
    help_text: str = ""


class ProviderInfo(BaseModel):
    """Describes a supported provider and its capabilities."""
    id: str
    name: str
    description: str
    supports_llm: bool = False
    supports_embedding: bool = False
    supports_vision: bool = False
    fields: List[ProviderField] = []
    default_llm_models: List[str] = []
    default_embedding_models: List[str] = []
    default_vision_models: List[str] = []


class TestConnectionRequest(BaseModel):
    """Schema for testing a provider connection."""
    provider: str
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    model_name: str
    config_type: str = "llm"
