"""
LLM Factory - Creates LLM instances using LiteLLM for multi-provider support.
"""
from langchain_litellm import ChatLiteLLM
import litellm

# Global litellm configuration to suppress unnecessary debug logs
litellm.set_verbose = False
litellm.suppress_debug_info = True

from app.config import settings
from app.utils.logger import get_logger
from app.models.base import SessionLocal
from app.models.model_config import ModelConfig
from app.utils.crypto import decrypt_api_key

logger = get_logger(__name__)


def _get_active_config(config_type: str):
    """Get active config from DB, or fallback to default settings."""
    db = SessionLocal()
    try:
        config = db.query(ModelConfig).filter(
            ModelConfig.config_type == config_type,
            ModelConfig.is_active == True
        ).first()

        if config:
            # Found in DB
            api_key = decrypt_api_key(config.api_key_encrypted) if config.api_key_encrypted else None
            return {
                "provider": config.provider,
                "model_name": config.model_name,
                "api_key": api_key,
                "api_base": config.api_base,
                "extra_params": config.extra_params or {}
            }
        else:
            # Fallback to defaults from env vars
            if config_type == "vision":
                model_name = settings.openai_vision_model
            elif config_type == "embedding":
                model_name = settings.openai_embedding_model
            else:
                model_name = settings.openai_model
                
            return {
                "provider": settings.llm_provider,
                "model_name": model_name,
                "api_key": settings.openai_api_key,
                "api_base": None,
                "extra_params": {}
            }
    except Exception as e:
        logger.error(f"Error fetching active {config_type} config: {e}")
        # absolute fallback
        return {
            "provider": settings.llm_provider,
            "model_name": settings.openai_model,
            "api_key": settings.openai_api_key,
            "api_base": None,
            "extra_params": {}
        }
    finally:
        db.close()


def get_llm(
    use_vision: bool = False,
    require_primary: bool = True,
    allow_alternate: bool = False
):
    """
    Get LLM instance using LiteLLM (multi-provider support).
    
    Args:
        use_vision: Whether to use vision-capable model
        require_primary: Not strictly used for OpenAI anymore, but kept for compatibility
        allow_alternate: Kept for compatibility
    
    Returns:
        ChatLiteLLM instance
    """
    config_type = "vision" if use_vision else "llm"
    config = _get_active_config(config_type)
    
    if not config["api_key"] and config["provider"] != "ollama":
        if require_primary:
            raise ValueError(f"API key not configured for provider {config['provider']}")
        else:
            raise ValueError(f"API key not configured for provider {config['provider']}")
    
    # Format model string for LiteLLM: "provider/model_name"
    model_string = f"{config['provider']}/{config['model_name']}"
    
    logger.info(f"[LLM_FACTORY] Using LiteLLM model: {model_string} (vision: {use_vision})")
    
    # Build params dynamically
    params = {
        "model": model_string,
        "temperature": settings.llm_temperature,
        "max_tokens": settings.llm_max_tokens,
    }
    
    if config["api_key"]:
        params["api_key"] = config["api_key"]
    if config["api_base"]:
        params["api_base"] = config["api_base"]
    if config["extra_params"]:
        params.update(config["extra_params"])
        
    return ChatLiteLLM(**params)
