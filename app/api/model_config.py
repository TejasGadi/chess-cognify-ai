"""
API endpoints for Model Configuration management.
Allows users to configure LLM, Embedding, and Vision model providers via the UI.
"""
from typing import List
from fastapi import APIRouter, HTTPException
from app.models.base import SessionLocal
from app.models.model_config import ModelConfig
from app.schemas.model_config import (
    ModelConfigCreate,
    ModelConfigResponse,
    ActiveModelsResponse,
    ProviderInfo,
    ProviderField,
    TestConnectionRequest,
)
from app.utils.crypto import encrypt_api_key, decrypt_api_key, mask_api_key
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/model-config", tags=["Model Configuration"])

# ──────────────────────────────────────────────
# Provider registry
# ──────────────────────────────────────────────
PROVIDERS: List[ProviderInfo] = [
    ProviderInfo(
        id="openai",
        name="OpenAI",
        description="GPT-4o, GPT-4o-mini, text-embedding-3-small and more",
        supports_llm=True, supports_embedding=True, supports_vision=True,
        fields=[
            ProviderField(name="api_key", label="API Key", type="password", required=True, placeholder="sk-..."),
            ProviderField(name="api_base", label="Base URL", type="url", required=False, placeholder="https://api.openai.com/v1", help_text="Leave blank for default"),
        ],
        default_llm_models=["gpt-4o", "gpt-4o-mini", "gpt-4.1-nano", "gpt-4.1-mini", "gpt-4.1"],
        default_embedding_models=["text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"],
        default_vision_models=["gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini"],
    ),
    ProviderInfo(
        id="gemini",
        name="Google Gemini",
        description="Gemini 2.0 Flash, Gemini 1.5 Pro and more",
        supports_llm=True, supports_embedding=True, supports_vision=True,
        fields=[
            ProviderField(name="api_key", label="API Key", type="password", required=True, placeholder="AI..."),
        ],
        default_llm_models=["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.5-flash-preview-04-17"],
        default_embedding_models=["text-embedding-004"],
        default_vision_models=["gemini-2.0-flash", "gemini-1.5-pro"],
    ),
    ProviderInfo(
        id="groq",
        name="Groq",
        description="Ultra-fast inference for Llama, Mixtral and more",
        supports_llm=True, supports_embedding=False, supports_vision=False,
        fields=[
            ProviderField(name="api_key", label="API Key", type="password", required=True, placeholder="gsk_..."),
        ],
        default_llm_models=["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "meta-llama/llama-4-scout-17b-16e-instruct"],
        default_embedding_models=[],
        default_vision_models=[],
    ),
    ProviderInfo(
        id="ollama",
        name="Ollama",
        description="Run models locally — Llama, Mistral, Phi, etc.",
        supports_llm=True, supports_embedding=True, supports_vision=True,
        fields=[
            ProviderField(name="api_base", label="Ollama URL", type="url", required=True, placeholder="http://localhost:11434", help_text="URL where Ollama is running"),
        ],
        default_llm_models=["llama3.1", "llama3", "mistral", "phi3", "qwen2.5"],
        default_embedding_models=["bge-m3", "nomic-embed-text", "all-minilm"],
        default_vision_models=["llava", "llama3.2-vision"],
    ),
    ProviderInfo(
        id="anthropic",
        name="Anthropic",
        description="Claude 3.5 Sonnet, Claude 3 Opus and more",
        supports_llm=True, supports_embedding=False, supports_vision=True,
        fields=[
            ProviderField(name="api_key", label="API Key", type="password", required=True, placeholder="sk-ant-..."),
        ],
        default_llm_models=["claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"],
        default_embedding_models=[],
        default_vision_models=["claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022"],
    ),
    ProviderInfo(
        id="deepseek",
        name="DeepSeek",
        description="DeepSeek V3, DeepSeek Coder and more",
        supports_llm=True, supports_embedding=False, supports_vision=False,
        fields=[
            ProviderField(name="api_key", label="API Key", type="password", required=True, placeholder="sk-..."),
            ProviderField(name="api_base", label="Base URL", type="url", required=False, placeholder="https://api.deepseek.com", help_text="Leave blank for default"),
        ],
        default_llm_models=["deepseek-chat", "deepseek-coder"],
        default_embedding_models=[],
        default_vision_models=[],
    ),
]


def _to_response(config: ModelConfig) -> ModelConfigResponse:
    """Convert DB model to response schema with masked API key."""
    api_key_masked = None
    if config.api_key_encrypted:
        try:
            plain = decrypt_api_key(config.api_key_encrypted)
            api_key_masked = mask_api_key(plain)
        except Exception:
            api_key_masked = "****"
    return ModelConfigResponse(
        id=config.id,
        config_type=config.config_type,
        provider=config.provider,
        model_name=config.model_name,
        api_key_masked=api_key_masked,
        api_base=config.api_base,
        extra_params=config.extra_params,
        is_active=config.is_active,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────

@router.get("/providers", response_model=List[ProviderInfo])
async def list_providers():
    """List all supported model providers with their capabilities and required fields."""
    return PROVIDERS


@router.get("", response_model=List[ModelConfigResponse])
async def list_configs():
    """List all saved model configurations (API keys masked)."""
    db = SessionLocal()
    try:
        configs = db.query(ModelConfig).order_by(ModelConfig.config_type, ModelConfig.provider).all()
        return [_to_response(c) for c in configs]
    finally:
        db.close()


@router.get("/active", response_model=ActiveModelsResponse)
async def get_active_models():
    """Get the currently active model for each config type."""
    db = SessionLocal()
    try:
        result = {}
        for config_type in ["llm", "embedding", "vision"]:
            config = db.query(ModelConfig).filter(
                ModelConfig.config_type == config_type,
                ModelConfig.is_active == True
            ).first()
            result[config_type] = _to_response(config) if config else None
        return ActiveModelsResponse(**result)
    finally:
        db.close()


@router.post("", response_model=ModelConfigResponse)
async def create_or_update_config(payload: ModelConfigCreate):
    """Create or update a model configuration for a provider + config_type combo."""
    if payload.config_type not in ("llm", "embedding", "vision"):
        raise HTTPException(status_code=400, detail="config_type must be one of: llm, embedding, vision")

    # Validate provider
    valid_providers = {p.id for p in PROVIDERS}
    if payload.provider not in valid_providers:
        raise HTTPException(status_code=400, detail=f"Provider must be one of: {', '.join(valid_providers)}")

    db = SessionLocal()
    try:
        # Check if config already exists for this provider + type
        existing = db.query(ModelConfig).filter(
            ModelConfig.config_type == payload.config_type,
            ModelConfig.provider == payload.provider,
        ).first()

        encrypted_key = encrypt_api_key(payload.api_key) if payload.api_key else None

        if existing:
            existing.model_name = payload.model_name
            if encrypted_key:
                existing.api_key_encrypted = encrypted_key
            if payload.api_base is not None:
                existing.api_base = payload.api_base
            if payload.extra_params is not None:
                existing.extra_params = payload.extra_params
            db.commit()
            db.refresh(existing)
            logger.info(f"Updated model config: {payload.config_type}/{payload.provider}/{payload.model_name}")
            return _to_response(existing)
        else:
            new_config = ModelConfig(
                config_type=payload.config_type,
                provider=payload.provider,
                model_name=payload.model_name,
                api_key_encrypted=encrypted_key,
                api_base=payload.api_base,
                extra_params=payload.extra_params,
                is_active=False,
            )
            db.add(new_config)
            db.commit()
            db.refresh(new_config)
            logger.info(f"Created model config: {payload.config_type}/{payload.provider}/{payload.model_name}")
            return _to_response(new_config)
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating/updating model config: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/{config_id}/activate", response_model=ModelConfigResponse)
async def activate_config(config_id: int):
    """Set a config as the active one for its config_type. Deactivates all others of the same type."""
    db = SessionLocal()
    try:
        config = db.query(ModelConfig).filter(ModelConfig.id == config_id).first()
        if not config:
            raise HTTPException(status_code=404, detail="Configuration not found")

        # Deactivate all same-type configs
        db.query(ModelConfig).filter(
            ModelConfig.config_type == config.config_type
        ).update({"is_active": False})

        # Activate selected
        config.is_active = True
        db.commit()
        db.refresh(config)

        logger.info(f"Activated model config: {config.config_type}/{config.provider}/{config.model_name}")
        return _to_response(config)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error activating model config: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.delete("/{config_id}")
async def delete_config(config_id: int):
    """Delete a model configuration."""
    db = SessionLocal()
    try:
        config = db.query(ModelConfig).filter(ModelConfig.id == config_id).first()
        if not config:
            raise HTTPException(status_code=404, detail="Configuration not found")
        if config.is_active:
            raise HTTPException(status_code=400, detail="Cannot delete the active configuration. Activate a different one first.")

        db.delete(config)
        db.commit()
        logger.info(f"Deleted model config: {config.config_type}/{config.provider}/{config.model_name}")
        return {"message": "Configuration deleted"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/test")
async def test_connection(payload: TestConnectionRequest):
    """Test connectivity for a provider configuration."""
    try:
        import litellm

        model_string = f"{payload.provider}/{payload.model_name}"
        logger.info(f"Testing connection to: {model_string}")

        # Use litellm.completion for a simple test
        response = litellm.completion(
            model=model_string,
            messages=[{"role": "user", "content": "Say 'ok' in one word."}],
            api_key=payload.api_key or None,
            api_base=payload.api_base or None,
            max_tokens=5,
            timeout=15,
        )

        return {
            "success": True,
            "message": f"Successfully connected to {payload.provider}/{payload.model_name}",
            "model": response.model if hasattr(response, 'model') else model_string,
        }
    except Exception as e:
        logger.error(f"Connection test failed for {payload.provider}/{payload.model_name}: {e}")
        return {
            "success": False,
            "message": f"Connection failed: {str(e)}",
        }
