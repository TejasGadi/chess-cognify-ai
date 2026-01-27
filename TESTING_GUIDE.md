# Testing Guide: Multi-Step Reasoning & Theme Analysis

This guide explains how to test the new implementation of multi-step reasoning and theme analysis.

## Prerequisites

1. **Environment Setup**:
   ```bash
   # Activate virtual environment
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Ensure dependencies are installed
   pip install -r requirements.txt
   ```

2. **Required Services**:
   - PostgreSQL (for database)
   - Redis (for caching)
   - Stockfish (for engine analysis)
   - OpenAI API Key (for LLM calls)

3. **Environment Variables**:
   Create a `.env` file with:
   ```bash
   OPENAI_API_KEY=your_api_key_here
   DATABASE_URL=postgresql://chess_user:chess_password@localhost:5432/chess_cognify
   REDIS_URL=redis://localhost:6379/0
   STOCKFISH_PATH=/usr/local/bin/stockfish
   ```

## Quick Test Script

Run the comprehensive test script:

```bash
python test_implementation.py
```

This script tests:
1. ✅ Position Extraction Agent
2. ✅ Position Validator
3. ✅ Theme Analysis Service
4. ✅ Tactical Pattern Detector
5. ✅ Full Explanation Generation Flow
6. ✅ Retry Logic with Error Feedback

## Individual Component Tests

### 1. Test Position Extraction

```python
import asyncio
from app.agents.position_extraction_agent import PositionExtractionAgent

async def test():
    agent = PositionExtractionAgent()
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    extraction = await agent.extract_position(fen=fen)
    print(f"Extracted: {extraction.white_pieces}, {extraction.black_pieces}")

asyncio.run(test())
```

### 2. Test Position Validation

```python
from app.utils.position_validator import PositionValidator
from app.schemas.llm_output import PositionExtractionOutput

validator = PositionValidator()
extraction = PositionExtractionOutput(...)  # Your extraction
result = validator.validate_extraction(extraction, fen)
print(f"Valid: {result.is_valid}, Confidence: {result.confidence_score}")
```

### 3. Test Theme Analysis

```python
import chess
from app.services.theme_analysis_service import ThemeAnalysisService

board = chess.Board()
board.push_san("e4")
themes = ThemeAnalysisService.analyze_position_themes(board)
print(f"Material: {themes['material']}")
print(f"Mobility: {themes['mobility']}")
```

### 4. Test Tactical Patterns

```python
import chess
from app.utils.tactical_patterns import TacticalPatternDetector

board = chess.Board()
patterns = TacticalPatternDetector.identify_tactical_patterns(board)
print(f"Patterns: {patterns}")
```

### 5. Test Full Explanation

```python
import asyncio
from app.agents.explanation_agent import ExplanationAgent

async def test():
    agent = ExplanationAgent()
    explanation = await agent.generate_explanation(
        fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        played_move="e2e4",
        best_move="e2e4",
        label="Best",
        eval_change="+0.0 -> +0.3"
    )
    print(explanation)

asyncio.run(test())
```

## Unit Tests

Run the pytest test suite:

```bash
# Run all tests
pytest

# Run specific test files
pytest tests/test_position_extraction.py
pytest tests/test_theme_analysis.py

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=app tests/
```

## Integration Test via API

1. **Start the FastAPI server**:
   ```bash
   uvicorn app.main:app --reload
   ```

2. **Upload a PGN and analyze**:
   ```bash
   # Use the Streamlit UI or API directly
   curl -X POST http://localhost:8000/api/games/analyze \
     -H "Content-Type: application/json" \
     -d '{"pgn": "1. e4 e5 2. Nf3 Nc6"}'
   ```

3. **Check logs** for:
   - `[AGENT] ExplanationAgent - Step 1: Extracting and validating position`
   - `[AGENT] ExplanationAgent - Step 2: Analyzing positional themes`
   - `[AGENT] ExplanationAgent - Step 3: Invoking LLM chain for move analysis`

## What to Look For

### ✅ Success Indicators

1. **Position Extraction**:
   - Logs show extraction attempts
   - Confidence scores > 0.8
   - Verified piece positions match actual FEN

2. **Position Validation**:
   - Most extractions pass validation (confidence >= 0.9)
   - Discrepancies are caught and logged
   - Retry logic triggers when validation fails

3. **Theme Analysis**:
   - Material, mobility, space, king safety calculated
   - Tactical patterns detected when present
   - Results cached for repeated positions

4. **Explanation Quality**:
   - Explanations reference verified positions
   - Explanations mention specific themes (material, mobility, etc.)
   - Explanations identify tactical patterns when present
   - No position hallucinations (wrong piece locations)

### ⚠️ Common Issues

1. **OpenAI API Key Missing**:
   - Error: `OPENAI_API_KEY not configured`
   - Fix: Set `OPENAI_API_KEY` in `.env` file

2. **Redis Not Running**:
   - Warning: `Cache get error`
   - Fix: Start Redis: `redis-server` or use Docker

3. **Stockfish Not Found**:
   - Error: `Stockfish not found`
   - Fix: Install Stockfish or set `STOCKFISH_PATH` in `.env`

4. **Position Extraction Fails**:
   - Check OpenAI API key and quota
   - Check network connectivity
   - Review logs for LLM errors

## Performance Benchmarks

Expected performance:
- Position extraction: ~2-5 seconds per position
- Theme analysis: <1 second (cached: <0.1 seconds)
- Full explanation: ~5-10 seconds per move
- Retry logic: Adds ~2-5 seconds if validation fails

## Debugging

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Or set in `.env`:
```
LOG_LEVEL=DEBUG
```

Check logs for:
- `[AGENT]` - Agent operations
- `[VALIDATOR]` - Validation results
- `[THEME]` - Theme analysis (if added)

## Next Steps

After testing:
1. Review explanation quality in actual game reviews
2. Monitor position extraction accuracy
3. Check theme analysis relevance
4. Optimize performance if needed
5. Proceed to Phase 3 (Integration and Optimization)
