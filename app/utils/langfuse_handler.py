"""
Langfuse Callback Handler for LangChain/LangGraph observability.
"""
from typing import Optional
from langfuse import Langfuse, get_client
from langfuse.langchain import CallbackHandler
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Global Langfuse client instance
_langfuse_client: Optional[Langfuse] = None
_langfuse_handler: Optional[CallbackHandler] = None


def initialize_langfuse() -> Optional[Langfuse]:
    """
    Initialize Langfuse client if enabled and keys are configured.
    
    Returns:
        Langfuse client instance or None if disabled/misconfigured
    """
    global _langfuse_client
    
    if not settings.langfuse_enabled:
        logger.debug("[LANGFUSE] Langfuse is disabled in settings")
        return None
    
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        logger.warning("[LANGFUSE] Langfuse keys not configured - tracing disabled")
        return None
    
    try:
        _langfuse_client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_base_url,
        )
        logger.info(f"[LANGFUSE] Initialized Langfuse client (base_url: {settings.langfuse_base_url})")
        return _langfuse_client
    except Exception as e:
        logger.error(f"[LANGFUSE] Failed to initialize Langfuse client: {e}")
        return None


def get_langfuse_handler() -> Optional[CallbackHandler]:
    """
    Get or create Langfuse CallbackHandler for LangChain/LangGraph.
    
    Returns:
        CallbackHandler instance or None if Langfuse is disabled
    """
    global _langfuse_handler
    
    if not settings.langfuse_enabled:
        return None
    
    # Initialize client if not already done
    if _langfuse_client is None:
        initialize_langfuse()
    
    # If client initialization failed, return None
    if _langfuse_client is None:
        return None
    
    # Create handler if not already created
    if _langfuse_handler is None:
        try:
            _langfuse_handler = CallbackHandler()
            logger.debug("[LANGFUSE] Created CallbackHandler")
        except Exception as e:
            logger.error(f"[LANGFUSE] Failed to create CallbackHandler: {e}")
            return None
    
    return _langfuse_handler


def flush_langfuse() -> None:
    """
    Flush pending Langfuse events.
    Useful for short-lived scripts or before shutdown.
    """
    global _langfuse_client
    
    if _langfuse_client is not None:
        try:
            client = get_client()
            if client:
                client.flush()
                logger.debug("[LANGFUSE] Flushed pending events")
        except Exception as e:
            logger.warning(f"[LANGFUSE] Failed to flush events: {e}")


def shutdown_langfuse() -> None:
    """
    Shutdown Langfuse client and flush pending events.
    """
    global _langfuse_client, _langfuse_handler
    
    if _langfuse_client is not None:
        try:
            client = get_client()
            if client:
                client.shutdown()
                logger.info("[LANGFUSE] Shutdown Langfuse client")
        except Exception as e:
            logger.warning(f"[LANGFUSE] Failed to shutdown client: {e}")
    
    _langfuse_client = None
    _langfuse_handler = None
