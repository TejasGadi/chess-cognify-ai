"""
Embedding utilities using Ollama.
"""
from langchain_ollama import OllamaEmbeddings
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Global embeddings instance
_embeddings: OllamaEmbeddings | None = None


def get_embeddings() -> OllamaEmbeddings:
    """Get or create Ollama embeddings instance."""
    global _embeddings
    if _embeddings is None:
        _embeddings = OllamaEmbeddings(
            model=settings.ollama_embedding_model,
            base_url=settings.ollama_base_url,
        )
        logger.info(
            f"Initialized Ollama embeddings with model: {settings.ollama_embedding_model}"
        )
    return _embeddings
