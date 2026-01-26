# Ollama Embeddings Configuration

## Overview

The project uses **Ollama** for local embeddings with the **bge-m3** model. This provides:
- **Local processing** - No API costs
- **Privacy** - Data stays on your device
- **Fast inference** - Runs on local hardware
- **High quality** - bge-m3 is a state-of-the-art multilingual embedding model

## Setup

### Prerequisites

1. **Ollama installed** on your device
2. **bge-m3 model** already available (as mentioned)

### Verify Ollama is Running

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Or test the embedding endpoint
curl http://localhost:11434/api/embeddings -d '{
  "model": "bge-m3",
  "prompt": "test"
}'
```

### Configuration

The embedding model is configured in `.env`:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=bge-m3
```

Default values:
- **Base URL**: `http://localhost:11434` (Ollama default)
- **Model**: `bge-m3` (BAAI General Embedding model)

## Usage

### In Code

```python
from app.utils.embeddings import get_embeddings

# Get embeddings instance
embeddings = get_embeddings()

# Embed a single text
vector = embeddings.embed_query("What is a chess opening?")

# Embed multiple texts
vectors = embeddings.embed_documents([
    "Chess opening principles",
    "Middlegame tactics",
    "Endgame techniques"
])
```

### With Qdrant Vector Store

```python
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from app.utils.embeddings import get_embeddings
from app.config import settings

# Initialize Qdrant client
client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)

# Create vector store with Ollama embeddings
vector_store = QdrantVectorStore(
    client=client,
    collection_name=settings.qdrant_collection_name,
    embedding=get_embeddings(),
)
```

## bge-m3 Model Details

- **Model**: `bge-m3` (BAAI General Embedding)
- **Dimensions**: 1024
- **Languages**: Multilingual (supports 100+ languages)
- **Use Case**: General-purpose embeddings, excellent for semantic search
- **Performance**: State-of-the-art on MTEB benchmark

## Troubleshooting

### Model Not Found

If you get an error that the model is not found:

```bash
# Pull the model (if not already available)
ollama pull bge-m3
```

### Connection Error

If you can't connect to Ollama:

1. Check if Ollama is running:
   ```bash
   ollama serve
   ```

2. Verify the base URL in `.env` matches your Ollama instance

3. Check firewall settings if using a remote Ollama instance

### Performance Issues

- **CPU**: bge-m3 works well on CPU
- **GPU**: For better performance, ensure Ollama can use GPU if available
- **Memory**: bge-m3 requires ~2GB RAM

## Alternative Models

If you want to use a different Ollama embedding model:

1. Update `.env`:
   ```env
   OLLAMA_EMBEDDING_MODEL=your-model-name
   ```

2. Available alternatives:
   - `nomic-embed-text` - Smaller, faster
   - `mxbai-embed-large` - Larger, more accurate
   - `all-minilm` - Very small, very fast

## Integration with Book Chatbot

When implementing Phase 7 (Book Chatbot), the embeddings will be used to:
1. **Chunk PDF text** into semantic pieces
2. **Generate embeddings** for each chunk using Ollama
3. **Store in Qdrant** for vector search
4. **Retrieve relevant chunks** based on user queries

All embedding operations will use the local Ollama instance - no external API calls needed!
