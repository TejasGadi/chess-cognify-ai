"""
Embedding utilities. Uses OpenAI embeddings (same as RAG); Ollama was removed from requirements.
"""
from typing import Union

from langchain_openai import OpenAIEmbeddings

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Global embeddings instance (OpenAI; used by VectorStoreService, book_service, book_chatbot)
_embeddings: Union[OpenAIEmbeddings, None] = None


def get_embeddings() -> OpenAIEmbeddings:
    """Get or create OpenAI embeddings instance (shared with RAG)."""
    global _embeddings
    if _embeddings is None:
        _embeddings = OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            api_key=settings.openai_api_key,
            max_retries=3,
        )
        logger.info(
            f"Initialized OpenAI embeddings with model: {settings.openai_embedding_model}"
        )
    return _embeddings
