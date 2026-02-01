# Documentation: Chess Cognify AI

Welcome to the Chess Cognify AI project. This guide covers setup, development, and operational details.

## 1. Quick Start (Docker)

The easiest way to run the entire stack is using Docker Compose.

### Prerequisites
- Docker and Docker Compose installed.
- An OpenAI API Key.

### Steps
1.  **Configure Environment**:
    Create a `docker.env` file (see `docker.env.example` if available, or use existing `docker.env`).
    Ensure `OPENAI_API_KEY` is set.
2.  **Start the Stack**:
    ```bash
    docker-compose up --build -d
    ```
3.  **Access the App**:
    - Frontend: `http://localhost:3000`
    - Backend API: `http://localhost:8000`
    - API Documentation: `http://localhost:8000/docs`

## 2. Development Setup

If you want to run the backend or frontend outside of Docker (for faster hot-reloading).

### Peripheral Services
Start only the databases and vector store:
```bash
docker-compose -f docker-compose.dev.yml up -d
```

### Backend Setup
1.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
2.  Run migrations:
    ```bash
    alembic upgrade head
    ```
3.  Start Uvicorn:
    ```bash
    uvicorn app.main:app --reload
    ```

### Frontend Setup
1.  Navigate to UI folder:
    ```bash
    cd chess-cognify-ui
    ```
2.  Install packages:
    ```bash
    npm install
    ```
3.  Start Vite dev server:
    ```bash
    npm run dev
    ```

## 3. Core Components

### Stockfish Service (`app/services/stockfish_service.py`)
Responsible for UCI communication. 
- **Important**: In Docker, the path is `/usr/games/stockfish`. Locally (Mac), it's often `/opt/homebrew/bin/stockfish`.
- **Management**: The service uses a lock to ensure only one engine process interacts with the CPU at a time, preventing container crashes.

### RAG Service (`app/services/rag_service.py`)
Handles retrieval from Qdrant.
- Uses `Ollama` (local) or `OpenAI` (cloud) for embeddings.
- Ranks chunks based on relevance before passing them to the LLM.

### Game Review (`app/services/engine_analysis_service.py`)
Orchestrates full-game analysis. It calculates "Eval Delta" (the change in evaluation between two moves) to identify critical moments.

## 4. API Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/evaluate` | POST | Gets Stockfish evaluation for a FEN. |
| `/api/games` | GET/POST | Manages stored chess games. |
| `/api/chat` | POST | Interacts with the AI Chess Coach. |
| `/api/books` | GET/POST | Manages the chess book library. |

## 5. Troubleshooting

- **Database Issues**: If you see "relation does not exist", run `alembic upgrade head`.
- **Stockfish Not Found**: Check the `STOCKFISH_PATH` in your `.env` or `docker.env`.
- **Backend Crash (Exit 137)**: Usually indicates OOM. Ensure you are using the Singleton `StockfishService` and not spawning hundreds of processes.
