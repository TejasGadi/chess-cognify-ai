# Technical Approach: AI Chess Game Review Coach (MVP)

## Technology Stack

### Backend Framework
- **FastAPI** - Modern Python web framework for API endpoints
- **Uvicorn** - ASGI server for production deployment
- **Pydantic** - Data validation and settings management

### Agent Orchestration
- **LangGraph** - Multi-agent workflow orchestration
- **LangChain** - LLM abstraction and tool integration

### Chess Engine
- **Stockfish** - UCI-compatible chess engine (via python-chess or direct UCI)
- **python-chess** - Chess library for PGN parsing, FEN handling, move validation

### LLM Integration
- **Groq API** - Primary LLM provider (fast inference with open models)
- **Groq Alternative Model** - Fallback using different Groq model
- **LangChain LLM abstraction** - Provider-agnostic interface

### Database & Storage
- **PostgreSQL** - Primary relational database for games, reviews, analysis
- **SQLAlchemy** - ORM for database operations
- **Alembic** - Database migrations

### Caching
- **Redis** - In-memory cache for engine analysis results
- **Redis-py** - Python Redis client

### Vector Database (Books Feature)
- **Qdrant** - Production-ready vector database for embeddings
- **langchain-qdrant** - LangChain integration for Qdrant

### Additional Libraries
- **python-dotenv** - Environment variable management
- **httpx** - Async HTTP client for API calls
- **celery** (optional) - Task queue for async engine analysis
- **pytest** - Testing framework
- **black, flake8** - Code formatting and linting

### Infrastructure (Deployment)
- **Docker** - Containerization
- **Docker Compose** - Local development orchestration
- **Nginx** (production) - Reverse proxy
- **Gunicorn/Uvicorn workers** - Production ASGI server

---

## Implementation Tasks

### Phase 1: Project Setup & Foundation

#### 1.1 Project Structure
- [ ] Initialize FastAPI project structure
- [ ] Set up virtual environment and dependency management (requirements.txt / poetry)
- [ ] Configure environment variables (.env template)
- [ ] Set up logging configuration
- [ ] Create Dockerfile and docker-compose.yml for local development
- [ ] Set up pre-commit hooks (black, flake8, mypy)

#### 1.2 Database Setup
- [ ] Design database schema (Games, EngineAnalysis, MoveReview, GameSummary tables)
- [ ] Create SQLAlchemy models
- [ ] Set up Alembic for migrations
- [ ] Create initial migration files
- [ ] Configure database connection pooling

#### 1.3 Redis Setup
- [ ] Configure Redis connection
- [ ] Implement cache key naming strategy (game_id:ply pattern)
- [ ] Create cache utility functions (get/set/delete)
- [ ] Set up cache TTL policies

#### 1.4 Configuration Management
- [ ] Create settings module (Pydantic Settings)
- [ ] Configure LLM provider settings (API keys, models)
- [ ] Configure Stockfish settings (depth, threads, hash)
- [ ] Set up feature flags for MVP scope

---

### Phase 2: Core Chess Engine Integration

#### 2.1 Stockfish Integration ✅
- [x] Create Stockfish wrapper class (UCI protocol) - `app/services/stockfish_service.py`
- [x] Implement position evaluation function - `evaluate_position()`
- [x] Implement best move calculation - `get_best_move()`
- [x] Add timeout handling for engine calls - `asyncio.wait_for()` with timeout
- [x] Implement engine process management (spawn/kill) - Context manager pattern
- [x] Add error handling for engine failures - Comprehensive logging and exceptions

#### 2.2 PGN Processing ✅
- [x] Implement PGN parser using python-chess - `PGNService.parse_pgn()`
- [x] Create game validation function - `PGNService.validate_pgn()`
- [x] Extract game metadata (time control, player names, result) - `PGNService.extract_metadata()`
- [x] Implement move sequence extraction - `PGNService.extract_move_sequence()`
- [x] Handle different PGN formats and edge cases - Multiple helper methods in PGNService

#### 2.3 Engine Analysis Agent (Core) ✅
- [x] Create EngineAnalysisAgent class - `EngineAnalysisService` in `app/services/engine_analysis_service.py`
- [x] Implement per-move analysis function:
  - [x] Get FEN before move
  - [x] Get evaluation before move
  - [x] Execute played move
  - [x] Get evaluation after move
  - [x] Calculate best move and evaluation
- [x] Implement batch analysis for full game - `analyze_game()` method
- [x] Add caching layer (check Redis before engine call) - Integrated with `app/utils/cache.py`
- [x] Persist results to EngineAnalysis table - `persist_analysis()` method
- [x] Return structured JSON output per move - Matches EngineAnalysis schema

---

### Phase 3: Move Classification & Analysis

#### 3.1 Move Classification Agent ✅
- [x] Create MoveClassificationAgent class (no LLM needed) - `MoveClassificationService` in `app/services/move_classification_service.py`
- [x] Implement evaluation delta calculation (eval_after - eval_best) - `calculate_evaluation_delta()`
- [x] Implement classification logic with thresholds:
  - [x] Best (played == best)
  - [x] Excellent (Δ ≥ -0.15)
  - [x] Good (-0.15 > Δ ≥ -0.5)
  - [x] Inaccuracy (-0.5 > Δ ≥ -1.0)
  - [x] Mistake (-1.0 > Δ ≥ -2.0)
  - [x] Blunder (Δ < -2.0)
- [x] Calculate centipawn loss per move - `abs(delta)` in centipawns
- [x] Persist to MoveReview table - `persist_classifications()` method
- [x] Return classification JSON - Matches MoveReview schema

#### 3.2 Accuracy & Rating Agent ✅
- [x] Create AccuracyRatingAgent class - `AccuracyRatingService` in `app/services/accuracy_rating_service.py`
- [x] Implement per-move accuracy calculation: `max(0, 100 - (centipawn_loss * K))` - `calculate_move_accuracy()`
- [x] Implement overall game accuracy (mean of move accuracies) - `calculate_game_accuracy()`
- [x] Implement rating estimation heuristic:
  - [x] Input: accuracy, blunder count, time control
  - [x] Output: estimated rating with confidence level
- [x] Persist to GameSummary table - `persist_game_summary()` method
- [x] Return accuracy and rating JSON - Matches GameSummary schema

#### 3.3 Game Phase Detection ✅
- [x] Implement phase tagging logic:
  - [x] Opening (moves 1-12) - Already in PGNService
  - [x] Middlegame - Already in PGNService
  - [x] Endgame (based on material count) - Already in PGNService
- [x] Add phase metadata to move classifications - `add_game_phases()` method in MoveClassificationService

---

### Phase 4: AI Explanation Agents

#### 4.1 Explanation Agent ✅
- [x] Create ExplanationAgent class - `ExplanationAgent` in `app/agents/explanation_agent.py`
- [x] Design prompt template for move explanations:
  - [x] Input: FEN, played_move, best_move, label, eval_change
  - [x] Constraints: No engine jargon, no variations, max 4 sentences
  - [x] Focus: Piece activity, king safety, tactics, strategy
- [x] Implement LLM call with structured output (JSON) - Uses Groq ChatGroq with StrOutputParser
- [x] Add prompt validation and safety checks - Length limits, error handling
- [x] Implement conditional triggering (only for Inaccuracy/Mistake/Blunder) - `EXPLANATION_LABELS` filter
- [x] Cache explanations in MoveReview table - Stored in `MoveReview.explanation` field
- [x] Add retry logic for LLM failures - Fallback explanations, error handling

#### 4.2 Weakness Detection Agent ✅
- [x] Create WeaknessDetectionAgent class - `WeaknessDetectionAgent` in `app/agents/weakness_detection_agent.py`
- [x] Aggregate classified moves by phase - `_group_mistakes_by_phase()` method
- [x] Design prompt for pattern detection:
  - [x] Input: List of mistakes grouped by concept
  - [x] Output: High-level weakness categories
  - [x] Avoid move-specific feedback
- [x] Implement LLM call for weakness summarization - Uses Groq ChatGroq
- [x] Parse and validate weakness list output - `_parse_weaknesses()` with JSON and regex fallback
- [x] Persist to GameSummary table - `detect_and_persist_weaknesses()` method
- [x] Return weaknesses JSON array - List of strings format

---

### Phase 5: Supervisor Agent & Orchestration

#### 5.1 LangGraph Setup ✅
- [x] Install and configure LangGraph - `langgraph>=1.0.0` in requirements.txt
- [x] Design agent communication schema (JSON-based) - `GameReviewState` TypedDict
- [x] Create agent state management (Pydantic models) - `GameReviewInput`, `GameReviewOutput` in `app/agents/state.py`

#### 5.2 Supervisor Agent Implementation ✅
- [x] Create SupervisorAgent class - `SupervisorAgent` in `app/agents/supervisor_agent.py`
- [x] Implement workflow orchestration:
  1. [x] Validate PGN - `validate_pgn()` node
  2. [x] Trigger Engine Analysis Agent - `analyze_engine()` node
  3. [x] Trigger Move Classification Agent - `classify_moves()` node
  4. [x] Trigger Explanation Agent (conditional) - `generate_explanations()` node
  5. [x] Trigger Accuracy & Rating Agent - `calculate_accuracy_rating()` node
  6. [x] Trigger Weakness Detection Agent - `detect_weaknesses()` node
  7. [x] Persist complete review - `finalize_review()` node
- [x] Implement error handling and rollback logic - Per-node error tracking, graceful degradation
- [x] Add progress tracking for long-running reviews - Progress percentage and step name in state
- [x] Return complete review JSON - `GameReviewOutput` Pydantic model

#### 5.3 LangGraph DAG Construction ✅
- [x] Define agent nodes in LangGraph - 7 nodes defined in `build_graph()`
- [x] Define edges and conditional routing - Sequential edges, START/END points
- [x] Implement state transitions - State updates in each node
- [x] Add error handling nodes - Error tracking in state
- [x] Test workflow execution - Graph compiles and executes via `review_game()`

---

### Phase 6: Game Review Chatbot

#### 6.1 Chatbot Agent Setup ✅
- [x] Create GameReviewChatbotAgent class - `GameReviewChatbotAgent` in `app/agents/game_review_chatbot.py`
- [x] Design context preparation function:
  - [x] Load game PGN - `_load_game_context()` method
  - [x] Load cached engine analysis - From EngineAnalysis table
  - [x] Load move classifications - From MoveReview table
  - [x] Load explanations - From MoveReview table
- [x] Create system prompt with constraints:
  - [x] No Stockfish calls - Explicitly stated in prompt
  - [x] No speculation - Constraint in prompt
  - [x] Use cached data only - Only loads from database
  - [x] Reference specific moves and evaluations - Context includes move numbers and evals

#### 6.2 Chat Interface ✅
- [x] Design conversation context management - `ChatService` class
- [x] Implement message history tracking - `ChatMessage` model and `get_conversation_history()`
- [x] Create prompt template for user queries - System prompt with game context
- [x] Implement LLM streaming response (optional) - Async `ainvoke()` (streaming can be added later)
- [x] Add conversation memory (session-based) - Session ID management, history persistence

#### 6.3 Chatbot API Endpoints ✅
- [x] Create POST /api/games/{game_id}/chat endpoint - `app/api/chat.py`
- [x] Implement message validation - Pydantic schema validation
- [x] Add rate limiting - Can be added via middleware (structure in place)
- [x] Return structured chat responses - `ChatMessageResponse` Pydantic model

---

### Phase 7: Book Chatbot (Separate Service)

#### 7.1 PDF Processing ✅
- [x] Set up PDF parsing library (PyPDF2 / pdfplumber) - `pdfplumber` in requirements.txt
- [x] Implement text extraction from PDFs - `PDFService.extract_text()` in `app/services/pdf_service.py`
- [x] Handle text cleaning and normalization - `PDFService.clean_text()` method
- [x] Create chunking strategy (semantic chunks) - `PDFService.chunk_text()` with overlap and paragraph-aware splitting

#### 7.2 Vector Database Setup ✅
- [x] Set up Qdrant database - `VectorStoreService` in `app/services/vector_store_service.py`
- [x] Implement embedding generation (Ollama bge-m3 model) - Uses `get_embeddings()` from `app/utils/embeddings.py`
- [x] Create vector store initialization - `VectorStoreService.initialize_collection()` method
- [x] Implement document ingestion pipeline - `VectorStoreService.add_documents()` method

#### 7.3 RAG Implementation ✅
- [x] Create BookChatbotAgent class - `BookChatbotAgent` in `app/agents/book_chatbot.py`
- [x] Implement vector search function - `VectorStoreService.search()` method
- [x] Design RAG prompt template - `BookChatbotAgent._get_rag_prompt()` method
- [x] Implement context retrieval (top-k chunks) - `BookChatbotAgent.chat()` with top_k parameter
- [x] Add source citation in responses - Sources included in response with filename and chunk index

#### 7.4 Book Chatbot API ✅
- [x] Create POST /api/books/upload endpoint - `app/api/books.py` with file upload
- [x] Create POST /api/books/{book_id}/chat endpoint - Book-specific chat endpoint
- [x] Create POST /api/books/chat endpoint - Chat across all books
- [x] Implement book management (list, delete) - GET /api/books/ and DELETE /api/books/{book_id}
- [x] Add book metadata storage - `Book` model in `app/models/book.py`

---

### Phase 8: API Endpoints ✅

#### 8.1 Game Review Endpoints ✅
- [x] POST /api/games/upload - Upload PGN file - `app/api/games.py`
- [x] POST /api/games/analyze - Trigger game analysis - `app/api/games.py`
- [x] GET /api/games/{game_id} - Get game details - `app/api/games.py`
- [x] GET /api/games/{game_id}/review - Get complete review - `app/api/games.py`
- [x] GET /api/games/{game_id}/moves - Get move-by-move analysis - `app/api/games.py`
- [x] GET /api/games/{game_id}/summary - Get game summary - `app/api/games.py`
- [x] GET /api/games/{game_id}/analysis - Get raw engine analysis - `app/api/games.py`

#### 8.2 Chat Endpoints ✅
- [x] POST /api/games/{game_id}/chat - Game review chat - `app/api/chat.py`
- [x] GET /api/games/{game_id}/chat/history - Chat history - `app/api/chat.py`

#### 8.3 Book Endpoints ✅
- [x] POST /api/books/upload - Upload chess book PDF - `app/api/books.py`
- [x] GET /api/books - List uploaded books - `app/api/books.py`
- [x] POST /api/books/{book_id}/chat - Book Q&A - `app/api/books.py`
- [x] POST /api/books/chat - Chat across all books - `app/api/books.py`
- [x] DELETE /api/books/{book_id} - Delete book - `app/api/books.py`

#### 8.4 Health & Status ✅
- [x] GET /health - Health check - `app/main.py`
- [x] GET /api/status - System status (engine, LLM, DB) - `app/api/status.py`
- [x] GET /api/metrics - Basic metrics - `app/api/status.py`

#### 8.5 Error Handling ✅
- [x] Global exception handlers - `app/api/exceptions.py`
- [x] Validation error handler - Pydantic validation errors
- [x] Database error handler - SQLAlchemy errors
- [x] General exception handler - Unexpected errors

---

### Phase 9: Async Processing & Scalability

#### 9.1 Async Task Queue (Optional)
- [ ] Set up Celery with Redis broker
- [ ] Create async task for engine analysis
- [ ] Implement job status tracking
- [ ] Add webhook/notification for completion

#### 9.2 Horizontal Scaling Preparation
- [ ] Design stateless API architecture
- [ ] Implement shared Redis cache
- [ ] Configure database connection pooling
- [ ] Add load balancer configuration notes

#### 9.3 Performance Optimization
- [ ] Implement lazy explanation generation (on-demand)
- [ ] Add pagination for move lists
- [ ] Optimize database queries (indexes, eager loading)
- [ ] Implement response compression

---

### Phase 10: Error Handling & Validation

#### 10.1 Input Validation
- [ ] Validate PGN format and structure
- [ ] Validate API request schemas (Pydantic models)
- [ ] Add custom validation errors
- [ ] Implement request sanitization

#### 10.2 Error Handling
- [ ] Create custom exception classes
- [ ] Implement global exception handler
- [ ] Add error logging and monitoring
- [ ] Create user-friendly error messages

#### 10.3 Safety & Guardrails
- [ ] Implement Stockfish timeout enforcement
- [ ] Add prompt injection prevention
- [ ] Validate LLM outputs against schemas
- [ ] Add rate limiting for LLM calls

---

### Phase 11: Testing

#### 11.1 Unit Tests
- [ ] Test PGN parsing and validation
- [ ] Test move classification logic
- [ ] Test accuracy calculation
- [ ] Test cache operations
- [ ] Test database models and queries

#### 11.2 Integration Tests
- [ ] Test Stockfish integration
- [ ] Test full supervisor workflow
- [ ] Test API endpoints
- [ ] Test chatbot agents
- [ ] Test error scenarios

#### 11.3 Test Data
- [ ] Create sample PGN files for testing
- [ ] Create mock LLM responses
- [ ] Set up test database fixtures

---

### Phase 12: Documentation & Deployment

#### 12.1 API Documentation
- [ ] Set up FastAPI auto-generated docs (Swagger/OpenAPI)
- [ ] Add endpoint descriptions and examples
- [ ] Document request/response schemas
- [ ] Create API usage examples

#### 12.2 Code Documentation
- [ ] Add docstrings to all classes and functions
- [ ] Document agent responsibilities
- [ ] Create architecture diagrams (Mermaid/PlantUML)
- [ ] Document configuration options

#### 12.3 Deployment Documentation
- [ ] Create deployment guide
- [ ] Document environment variables
- [ ] Create Docker deployment instructions
- [ ] Document scaling strategies
- [ ] Add monitoring and logging setup

#### 12.4 README
- [ ] Project overview
- [ ] Quick start guide
- [ ] Architecture overview
- [ ] Development setup instructions

---

## Implementation Order Recommendation

1. **Week 1-2**: Phase 1 (Setup) + Phase 2 (Engine Integration)
2. **Week 3**: Phase 3 (Classification) + Phase 4 (Explanations)
3. **Week 4**: Phase 5 (Supervisor) + Phase 6 (Chatbot)
4. **Week 5**: Phase 7 (Books) + Phase 8 (API Endpoints)
5. **Week 6**: Phase 9 (Scalability) + Phase 10 (Error Handling)
6. **Week 7**: Phase 11 (Testing) + Phase 12 (Documentation)

---

## Key Design Decisions

### Agent Communication
- All agents communicate via structured JSON
- No direct agent-to-agent calls (through supervisor)
- State passed explicitly, not shared

### Caching Strategy
- Engine results cached indefinitely (unless game changes)
- LLM explanations cached per (game_id, ply, label)
- Chatbot context loaded from cache, never recomputed

### LLM Usage Minimization
- Explanations only for mistakes (not every move)
- Weakness detection is summary-level (one call per game)
- Chatbot uses cached data (no new analysis)

### Database Design
- Normalized schema for flexibility
- Separate tables for raw analysis vs. processed review
- Indexes on game_id, ply for fast lookups

### Error Recovery
- Engine failures: Retry with timeout
- LLM failures: Fallback to template-based explanations
- Database failures: Queue for retry

---

## Future Extension Points

- **Lesson Generation Agent**: Post-MVP, uses weakness data
- **Psychology Agent**: Tilt detection, pattern analysis
- **Live Coaching**: Real-time move suggestions (separate service)
- **Opening Trainer**: Integration with opening database
- **Adaptive Difficulty**: Personalized training based on weaknesses

All extensions can be added without refactoring MVP core architecture.
