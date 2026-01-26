# AI Chess Game Review Coach

An intelligent chess game analysis system that combines Stockfish engine evaluation with AI-powered explanations and interactive coaching.

## Features

- **Engine-Backed Analysis**: Stockfish-powered move evaluation
- **AI Explanations**: Human-readable explanations for mistakes
- **Interactive Chatbot**: Chat with your game review
- **Weakness Detection**: Automatic identification of recurring patterns
- **Book Q&A**: Ask questions about chess concepts from uploaded books

## Tech Stack

- **Backend**: FastAPI
- **Agents**: LangGraph v1.0, LangChain v1.0
- **LLM**: Groq (fast inference with open models)
- **Embeddings**: Ollama (local, bge-m3 model)
- **Chess Engine**: Stockfish (via python-chess)
- **Database**: PostgreSQL
- **Cache**: Redis
- **Vector DB**: Qdrant (for books)

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL
- Redis
- Qdrant (vector database)
- Ollama (local, with bge-m3 model)
- Stockfish (install separately)

### Installation

1. Clone the repository
2. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Copy environment file:
   ```bash
   cp .env.example .env
   ```

5. Update `.env` with your configuration (API keys, database URLs, etc.)

6. Set up database:
   ```bash
   alembic upgrade head
   ```

7. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```

## Project Structure

```
chess-cognify-ai/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── agents/              # LangGraph agents
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic
│   ├── api/                 # API routes
│   └── utils/               # Utilities
├── alembic/                 # Database migrations
├── tests/                   # Test files
├── requirements.txt
├── .env.example
└── README.md
```

## Development

See `TECHNICAL_APPROACH.md` for detailed implementation plan.

## License

MIT
