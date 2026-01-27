# Quick Test Guide

## Option 1: Run Unit Tests (No API Key Required)

Test the core functionality without LLM calls:

```bash
# Activate virtual environment
source venv/bin/activate

# Run position extraction/validation tests
pytest tests/test_position_extraction.py -v

# Run theme analysis tests
pytest tests/test_theme_analysis.py -v

# Run all tests
pytest tests/ -v
```

## Option 2: Run Full Integration Test (Requires OpenAI API Key)

Test the complete flow including LLM calls:

```bash
# Activate virtual environment
source venv/bin/activate

# Run the comprehensive test script
python3 test_implementation.py
```

Or use the helper script:
```bash
./run_tests.sh
```

## Option 3: Test via API (Full End-to-End)

1. **Start the server**:
   ```bash
   source venv/bin/activate
   uvicorn app.main:app --reload
   ```

2. **Upload a PGN via Streamlit**:
   - Open `http://localhost:8501`
   - Upload a PGN file
   - Click "Analyze Game"
   - Check the explanations for quality

3. **Or use the API directly**:
   ```bash
   curl -X POST http://localhost:8000/api/games/analyze \
     -H "Content-Type: application/json" \
     -d '{
       "pgn": "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6",
       "metadata": {"White": "Test", "Black": "Test"}
     }'
   ```

## What to Check

### ✅ Success Indicators

1. **Position Extraction**:
   - Logs show: `[AGENT] PositionExtractionAgent - Extracting position`
   - Confidence scores > 0.8
   - Piece positions match actual FEN

2. **Position Validation**:
   - Logs show: `[VALIDATOR] Validation complete: valid=True`
   - Most positions validate successfully
   - Discrepancies are caught and logged

3. **Theme Analysis**:
   - Material, mobility, space, king safety calculated
   - Tactical patterns detected
   - Results are reasonable for the position

4. **Explanation Quality**:
   - Explanations reference verified positions
   - Explanations mention specific themes
   - No position hallucinations
   - More specific than generic statements

### 📊 Expected Output

When running `test_implementation.py`, you should see:

```
TEST 1: Position Extraction Agent
✅ Extraction successful!
   Active color: White
   Confidence: 0.95
   White pieces extracted:
     King: e1
     Queen: d1
     ...

TEST 2: Position Validator
✅ Validation complete!
   Is valid: True
   Confidence score: 0.95
   ✅ No discrepancies - extraction is accurate!

TEST 3: Theme Analysis Service
✅ Theme analysis complete!
   Material: White: 39, Black: 39, Balance: 0
   Mobility: White moves: 20, Black moves: 20
   ...

TEST 4: Tactical Pattern Detector
✅ Tactical pattern detection complete!
   Patterns found: 0

TEST 5: Full Explanation Generation Flow
✅ Explanation generated successfully!
   Explanation: White played e4. This is the best move...
```

## Troubleshooting

### Issue: ModuleNotFoundError
**Solution**: Activate virtual environment first:
```bash
source venv/bin/activate
```

### Issue: OPENAI_API_KEY not configured
**Solution**: Set in `.env` file:
```bash
OPENAI_API_KEY=sk-...
```

### Issue: Redis connection error
**Solution**: Start Redis or tests will still work (caching just won't work):
```bash
redis-server
# Or use Docker: docker run -d -p 6379:6379 redis
```

### Issue: Stockfish not found
**Solution**: Install Stockfish or set path in `.env`:
```bash
# macOS
brew install stockfish

# Or set in .env
STOCKFISH_PATH=/path/to/stockfish
```

## Next Steps After Testing

1. ✅ Verify all tests pass
2. ✅ Check explanation quality in actual games
3. ✅ Monitor position extraction accuracy
4. ✅ Review theme analysis relevance
5. ✅ Proceed to Phase 3 if everything works
