# ♟️ Chess Cognify AI

**The Ultimate AI Chess Companion.**  

Chess Cognify AI blends the tactical precision of **Stockfish 17.1** with the pedagogical depth of **Generative AI** and **RAG (Retrieval-Augmented Generation)**. It doesn't just evaluate positions; it coaches you by consulting elite chess literature to explain the strategic "why" behind every move.

---

## 🌟 Premium Features

### ♟️ Self-Analysis Board
A professional-grade interactive sandbox for deep exploration.
- **Stockfish 17.1 Integration**: Real-time evaluations directly in your browser.
- **Configurable Multi-PV**: Analyze up to 10 engine lines simultaneously to find hidden resources.
- **Live Eval Bar**: Visual feedback on material and positional advantage.
- **Seamless PGN/FEN Support**: Copy FENs, share PGNs, or download your entire analysis for later review.
- **Adaptive Board Controls**: Keyboard navigation and intuitive drag-and-drop gameplay.

### 📈 Intelligent Game Review
Transform your games into learning opportunities with our automated coach.
- **Advanced Classification**: Every move is labeled using standard terminology (Brilliant, Best, Great, Inaccuracy, Mistake, Blunder).
- **Accuracy Metrics**: Receive an overall performance percentage for each player.
- **Elo Estimation**: A simulated rating based on the complexity and accuracy of your play.
- **Pattern Recognition**: Identify recurring weaknesses like tactical oversights or endgame mismanagement.
- **Visual Insights**: A color-coded timeline of the game's momentum shifts.

### 📖 AI Chess Coach (RAG)
Your personal grandmaster mentor, grounded in high-quality literature.
- **Interactive Book Chat**: Upload chess PDFs and talk directly to your books.
- **Vision-Language Integration**: Using GPT-4o Vision to "see" and interpret board diagrams within book pages.
- **Grounded Advice**: The coach cites specific book sections, providing page numbers and context for every strategic tip.
- **LangGraph Orchestration**: A sophisticated 10-step AI pipeline ensures responses are precise and technical.

---

## 🐳 Docker Deployment

The fastest and most reliable way to run the full stack is using Docker Compose.

### 1️⃣ Prerequisites
- **Docker & Docker Compose** installed.
- **OpenAI API Key**: Required for the AI Coach and VLM features.
- **Ollama** (Optional): If running embeddings locally.

### 2️⃣ Environment Setup
Create a `docker.env` file in the root directory (you can copy from `docker.env.example` if available):

```env
OPENAI_API_KEY=sk-your-key-here
LANGFUSE_PUBLIC_KEY=your_key (optional)
LANGFUSE_SECRET_KEY=your_key (optional)
LANGFUSE_HOST=https://cloud.langfuse.com
```

### 3️⃣ Launch the Application
Run the following command to build and start all services (Frontend, Backend, DBs):

```bash
docker-compose up --build -d
```

### 4️⃣ Verify Services
Once the containers are running, you can access the application at:
- **Frontend UI**: [http://localhost:3000](http://localhost:3000)
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🛠️ Local Development Setup

If you want to contribute or run the frontend and backend separately for faster iteration.

### 1. Prerequisite: Infrastructure
Start the supporting services (Postgres, Redis, Qdrant) in the background:
```bash
docker-compose -f docker-compose.dev.yml up -d
```

### 2. Backend Setup
1.  **Environment**: Create a `.env` file in the root using `.env.example`.
2.  **Install Stockfish**: Ensure Stockfish is installed on your OS and the path is set in `.env`.
3.  **Run migrations** (required once per DB; creates `books`, `games`, etc.):
    ```bash
    alembic upgrade head
    ```
4.  **Run Development Server**:
    ```bash
    # Create and activate venv
    python -m venv venv
    source venv/bin/activate

    # Install dependencies
    pip install -r requirements.txt

    # Start FastAPI with reload
    python -m uvicorn app.main:app --reload --port 8000
    ```

### 3. Frontend Setup
1.  **Install & Start**:
    ```bash
    cd chess-cognify-ui
    npm install
    npm run dev
    ```
    The UI will be available at [http://localhost:5173](http://localhost:5173).

---

| Component | Technology |
| :--- | :--- |
| **Frontend** | React 18, Vite, Radix UI, Chessground |
| **Backend** | FastAPI (Python 3.11), SQLAlchemy, Alembic |
| **AI / LLM** | OpenAI GPT-4o, LangChain, LangGraph |
| **Vector Search** | Qdrant (RAG Architecture) |
| **Databases** | PostgreSQL, Redis (Caching) |
| **Engines** | Stockfish 17.1 (System Binary) |
| **Orchestration** | Docker, Nginx |

---

## 📂 Project Structure

```text
chess-cognify-ai/
├── app/                  # FastAPI Backend (Services, API, Models)
├── chess-cognify-ui/    # React Frontend (Vite & Tailwind)
├── docs/                 # Detailed Feature Documentation
├── uploads/              # Storage for Book PDFs and Diagram Images
├── docker-compose.yml    # Full-stack production orchestration
└── docker.env            # Container-specific environment variables
```

---

## 📖 Technical Documentation

For deep dives into specific subsystems, refer to our detailed guides:

- 🏛️ **[Detailed Architecture](docs/architecture.md)**: System design and data flow.
- ♟️ **[Self Analysis Deep-Dive](docs/self_analysis_feature.md)**: Engine management and real-time logic.
- 📈 **[Game Review Deep-Dive](docs/game_review_feature.md)**: Classification logic and accuracy mapping.
- 📖 **[AI Coach Deep-Dive](docs/book_companion_feature.md)**: LangGraph RAG and VLM pipeline details.
- 🛠️ **[Developer Manual](docs/documentation.md)**: Manual setup and troubleshooting.

---

## 🛡️ License
Distributed under the **MIT License**. See `LICENSE` for more information.
