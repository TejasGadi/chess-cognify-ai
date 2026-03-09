"""
Embedding utilities. Uses LiteLLM for multi-provider embedding support.
"""
from typing import Union, List
from langchain_core.embeddings import Embeddings
import litellm
from app.utils.logger import get_logger
from app.utils.llm_factory import _get_active_config

logger = get_logger(__name__)

class LiteLLMEmbeddings(Embeddings):
    """Custom LangChain Embeddings wrapper native to LiteLLM."""
    
    def __init__(self, model: str, api_key: str = None, api_base: str = None):
        self.model = model
        self.api_key = api_key
        self.api_base = api_base

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # Handle empty lists gracefully
        if not texts:
            return []
        
        response = litellm.embedding(
            model=self.model, 
            input=texts, 
            api_key=self.api_key, 
            api_base=self.api_base
        )
        return [data["embedding"] for data in response.data]

    def embed_query(self, text: str) -> List[float]:
        response = litellm.embedding(
            model=self.model, 
            input=[text], 
            api_key=self.api_key, 
            api_base=self.api_base
        )
        return response.data[0]["embedding"]

# Global embeddings instance
_embeddings: Union[LiteLLMEmbeddings, None] = None


def get_embeddings() -> LiteLLMEmbeddings:
    """Get or create LiteLLM embeddings instance (shared with RAG)."""
    global _embeddings
    if _embeddings is None:
        config = _get_active_config("embedding")
        model_string = f"{config['provider']}/{config['model_name']}"
        
        # Some providers like Ollama don't use 'provider/' prefix in LiteLLM for standard routing
        if config['provider'] == 'ollama':
            model_string = f"ollama/{config['model_name']}"
            
        params = {
            "model": model_string,
        }
        
        if config["api_key"]:
            params["api_key"] = config["api_key"]
        if config["api_base"]:
            params["api_base"] = config["api_base"]
            
        _embeddings = LiteLLMEmbeddings(**params)
        logger.info(f"Initialized LiteLLM embeddings with model: {model_string}")
        
    return _embeddings
