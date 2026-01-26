# Testing Guide - Phase 1

## ✅ What You CAN Test Now

### 1. Basic FastAPI Application ✅

The FastAPI app is ready to run and test. You can test:
- Root endpoint (`/`)
- Health check endpoint (`/health`)

**Note**: These endpoints work **without** database or Redis connections.

---

## 🚀 Quick Test Steps

### Step 1: Create `.env` file

```bash
cp .env.example .env
```

**For basic testing, you only need minimal configuration:**

```env
# Minimal .env for testing (without DB/Redis)
APP_NAME=chess-cognify-ai
APP_ENV=development
DEBUG=true
LOG_LEVEL=INFO

# These can be dummy values for basic testing
DATABASE_URL=postgresql://dummy:dummy@localhost:5432/dummy
REDIS_URL=redis://localhost:6379/0

# Stockfish (not needed yet)
STOCKFISH_PATH=/usr/local/bin/stockfish

# LLM (not needed yet, but required by config)
GROQ_API_KEY=dummy_key
GROQ_MODEL=llama-3.1-70b-versatile
GROQ_ALTERNATIVE_MODEL=mixtral-8x7b-32768
LLM_PROVIDER=groq
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=500

# Other required fields
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
QDRANT_COLLECTION_NAME=chess_books
SECRET_KEY=test_secret_key
API_KEY_EXPIRATION_HOURS=24
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

### Step 2: Run the Application

```bash
# Activate your virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Run the FastAPI server
uvicorn app.main:app --reload
```

You should see output like:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Step 3: Test the Endpoints

#### Test Root Endpoint
```bash
curl http://localhost:8000/
```

**Expected Response:**
```json
{
  "message": "AI Chess Game Review Coach API",
  "version": "0.1.0",
  "status": "running"
}
```

#### Test Health Endpoint
```bash
curl http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "healthy"
}
```

#### Test in Browser
Open: http://localhost:8000/docs

You'll see the FastAPI automatic interactive API documentation (Swagger UI).

---

## ❌ What You CANNOT Test Yet

- **Database operations** - Need migrations first
- **Redis cache** - Not implemented yet (but won't break the app)
- **Stockfish integration** - Phase 2
- **Game analysis** - Phase 2+
- **API endpoints for games** - Phase 8

---

## 🔍 Troubleshooting

### Issue: Import errors
**Solution**: Make sure you're in the project root directory and virtual environment is activated.

### Issue: Module not found
**Solution**: Ensure all dependencies are installed:
```bash
pip install -r requirements.txt
```

### Issue: Configuration errors
**Solution**: Make sure `.env` file exists and has all required fields (even if dummy values).

---

## ✅ Success Criteria

If you can:
1. ✅ Start the FastAPI server without errors
2. ✅ Access `http://localhost:8000/` and see the JSON response
3. ✅ Access `http://localhost:8000/health` and see `{"status": "healthy"}`
4. ✅ See the Swagger docs at `http://localhost:8000/docs`

Then **Phase 1 is working correctly!** 🎉

---

## Next Steps

Once basic testing is successful, we can proceed to:
- **Phase 2**: Stockfish integration (will require actual Stockfish installation)
- Database setup (will require PostgreSQL running)
