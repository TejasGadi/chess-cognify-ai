"""
LLM Factory - Creates LLM instances using OpenAI.
"""
from langchain_openai import ChatOpenAI
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def get_llm(
    use_vision: bool = False,
    require_primary: bool = True,
    allow_alternate: bool = False  # No alternate provider
):
    """
    Get LLM instance using OpenAI.
    
    Args:
        use_vision: Whether to use vision-capable model
        require_primary: If True, raise error if OpenAI not configured
        allow_alternate: Not used (kept for compatibility)
    
    Returns:
        ChatOpenAI instance
    
    Raises:
        ValueError: If OpenAI API key not configured
    """
    if not settings.openai_api_key:
        if require_primary:
            raise ValueError("OPENAI_API_KEY not configured")
        else:
            raise ValueError("OPENAI_API_KEY not configured")
    
    model = settings.openai_vision_model if use_vision else settings.openai_model
    logger.info(f"[LLM_FACTORY] Using OpenAI model: {model} (vision: {use_vision})")
    return ChatOpenAI(
        model=model,
        api_key=settings.openai_api_key,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
    )
