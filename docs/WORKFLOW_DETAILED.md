# Complete Workflow: PGN Upload → Analysis → Explanation

## Overview
This document details the complete workflow from uploading a PGN game in Streamlit to receiving the final analysis with AI explanations.

---

## Step 1: Streamlit UI - User Input

### Location: `streamlit_app.py`

**User Action:**
- User enters PGN text OR uploads PGN file OR uses chess board
- Clicks "Analyze Game" button

**Input:**
```python
pgn_string = "..."  # PGN format string
```

**API Call:**
```python
POST /api/games/analyze
{
    "pgn": pgn_string,
    "metadata": {...}  # Optional
}
```

**Timeout:** 1800 seconds (30 minutes)

---

## Step 2: FastAPI Endpoint - `/api/games/analyze`

### Location: `app/api/games.py`

**Function:** `analyze_game(game_data: GameCreate)`

**Process:**
1. Creates `SupervisorAgent` instance
2. Creates `GameReviewInput` from PGN
3. Calls `supervisor.review_game(input_data)`
4. Waits for workflow completion
5. Loads results from database
6. Returns `GameReviewResponse`

**Output Structure:**
```python
{
    "game_id": "uuid",
    "moves": [
        {
            "ply": 1,
            "move_san": "e4",
            "quality": "Best",
            "evaluation": "+0.3",
            "top_moves": [...],
            "explanation": "..."
        },
        ...
    ],
    "summary": {
        "accuracy": 85,
        "estimated_rating": 1200,
        ...
    }
}
```

---

## Step 3: Supervisor Agent - LangGraph Workflow

### Location: `app/agents/supervisor_agent.py`

**Workflow Graph:**
```
START → validate_pgn → analyze_engine → classify_moves → 
generate_explanations → calculate_accuracy_rating → 
detect_weaknesses → finalize_review → END
```

### Node 1: `validate_pgn`

**Input State:**
```python
{
    "game_id": "uuid",
    "pgn": "...",
    "metadata": {...},
    "pgn_valid": False,
    ...
}
```

**Process:**
- Calls `PGNService.validate_pgn(pgn)`
- Validates PGN format and move legality
- Checks if game has moves

**Output State:**
```python
{
    "pgn_valid": True/False,
    "validation_error": None/"error message",
    "current_step": "validating_pgn",
    "progress_percentage": 5
}
```

**Conditional Edge:**
- If `pgn_valid == False` → `finalize_review` (error)
- If `pgn_valid == True` → `analyze_engine`

---

### Node 2: `analyze_engine`

**Input State:**
```python
{
    "game_id": "uuid",
    "pgn": "...",
    "pgn_valid": True,
    "engine_analyses": [],
    ...
}
```

**Process:**
1. Persists game to database
2. Calls `EngineAnalysisService.analyze_game(pgn, game_id)`
3. For each ply (move):
   - Gets position BEFORE move: `get_position_before_move(game, ply)`
   - Gets move at ply: `get_move_at_ply(game, ply)`
   - Validates move is legal
   - Calls Stockfish analysis:
     - Initial analysis at depth 10
     - If eval delta > 1 pawn → Re-analyze at depth 20
   - Stores FEN BEFORE move
   - Returns analysis with:
     - `fen`: FEN before move
     - `played_move`: UCI format
     - `best_move`: UCI format
     - `eval_before`: Evaluation before move
     - `eval_after`: Evaluation after move
     - `top_moves`: Top 5 moves with evaluations
     - `played_move_rank`: Rank of played move
4. Persists all analyses to database

**Output State:**
```python
{
    "engine_analyses": [
        {
            "ply": 1,
            "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "played_move": "e2e4",
            "best_move": "e2e4",
            "eval_before": "+0.0",
            "eval_after": "+0.3",
            "top_moves": [...],
            ...
        },
        ...
    ],
    "engine_analysis_complete": True,
    "current_step": "engine_analysis",
    "progress_percentage": 40
}
```

**Conditional Edge:**
- If `engine_analysis_complete == False` → `finalize_review` (error)
- If `engine_analysis_complete == True` → `classify_moves`

---

### Node 3: `classify_moves`

**Input State:**
```python
{
    "engine_analyses": [...],
    "engine_analysis_complete": True,
    ...
}
```

**Process:**
1. For each engine analysis:
   - Calculates eval delta: `abs(eval_after - eval_before)`
   - Calls `MoveClassificationService.classify_move()`:
     - Input: `played_move`, `best_move`, `eval_after`, `eval_best`
     - Uses absolute delta for classification
     - Thresholds:
       - Delta = 0 → "Best"
       - Delta < 0.3 → "Good"
       - Delta < 0.6 → "Inaccuracy"
       - Delta < 1.0 → "Mistake"
       - Delta >= 1.0 → "Blunder"
   - Creates `MoveReview` record
2. Persists classifications to database

**Output State:**
```python
{
    "classifications": [
        {
            "ply": 1,
            "label": "Best",
            "eval_delta": 0.0,
            ...
        },
        ...
    ],
    "classification_complete": True,
    "current_step": "classifying_moves",
    "progress_percentage": 50
}
```

**Conditional Edge:**
- If `classification_complete == False` → `finalize_review` (error)
- If `classification_complete == True` → `generate_explanations`

---

### Node 4: `generate_explanations`

**Input State:**
```python
{
    "classifications": [...],
    "engine_analyses": [...],
    ...
}
```

**Process:**
1. Gets all move reviews from database
2. For each move (in parallel, with semaphore limit):
   - Calls `ExplanationAgent.explain_move(game_id, ply)`
   - Explanation generation (see Step 4.1 below)
3. Updates move reviews with explanations

**Output State:**
```python
{
    "explanations": {
        1: "White played e4. This is the best move...",
        2: "Black played c5. This is a good move...",
        ...
    },
    "explanation_complete": True,
    "current_step": "generating_explanations",
    "progress_percentage": 80
}
```

**Conditional Edge:**
- If `explanation_complete == False` → `finalize_review` (error)
- If `explanation_complete == True` → `calculate_accuracy_rating`

---

#### Step 4.1: Explanation Agent - LLM Call

**Location:** `app/agents/explanation_agent.py`

**Function:** `generate_explanation()`

**Input:**
```python
{
    "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",  # BEFORE move
    "played_move": "e2e4",  # UCI
    "best_move": "e2e4",  # UCI
    "label": "Best",
    "eval_change": "+0.0 -> +0.3",
    "top_moves": [...],
    "played_move_eval": "+0.3",
    "best_move_eval": "+0.3"
}
```

**Process:**
1. **FEN Conversion:**
   - Parses FEN (before move)
   - Validates move is legal
   - Applies move: `board.push(move)`
   - Gets FEN AFTER move: `board.fen()`

2. **Position Representation:**
   - Calls `format_position_for_llm(fen_after, last_move=played_move_san)`
   - Generates:
     - ASCII board (visual representation)
     - FEN notation (standard encoding)
     - Piece list (explicit locations - AUTHORITATIVE)

3. **Active Player Detection:**
   - Calls `_get_active_player(fen_before)`
   - Determines whose turn it is (White/Black)

4. **Evaluation Interpretation:**
   - Calls `_interpret_evaluation(eval_str, active_player)`
   - Converts Stockfish eval to player's perspective
   - Example: "+4.39 after Black's move" → "terrible for Black"

5. **LLM Prompt Construction:**
   - System prompt: Instructions for chess coach
   - Human prompt: Position representation + move context

**LLM Prompt (System):**
```
You are an expert chess coach providing detailed move analysis. Your comments must be:
- SPECIFIC and TACTICAL: Explain the exact chess reason why the move is good/bad
- Focus on concrete chess concepts: piece traps, tactical sequences, weak squares, king safety
- Maximum 4 sentences, but be detailed and educational
- Use Standard Algebraic Notation (SAN) for moves
- Always identify whose turn it is (White or Black) and write from that player's perspective

EVALUATION UNDERSTANDING:
- Positive evaluation (+X.XX) = White has the advantage
- Negative evaluation (-X.XX) = Black has the advantage
- If {active_player} plays a move and evaluation becomes +4.39, this means {active_player} gave White a huge advantage (bad for {active_player})
```

**LLM Prompt (Human):**
```
Analyze this chess move using the comprehensive position representation below:

{position_representation}

Active player: {active_player} (This is {active_player}'s turn - they just played this move)
Move played: {played_move_san} (Evaluation after move: {played_move_eval})
Best move: {best_move_san} (Evaluation after best move: {best_move_eval})
Move quality: {label}
{top_moves_context}

**EVALUATION INTERPRETATION:**
- The evaluation after {active_player}'s move is {played_move_eval}
- {evaluation_interpretation}
- Compare this to the best move evaluation: {best_move_eval}

**CRITICAL: POSITION VERIFICATION**
All three representations (ASCII board, FEN, piece list) show the SAME position - the position AFTER {played_move_san} was played.
- Cross-reference all three to verify piece locations
- Trust the piece list as the authoritative source

**ANALYSIS REQUIREMENTS:**
1. Use the ASCII board to visually understand the position
2. Use the FEN notation for precise position reference
3. Use the piece list to identify exact locations (MOST RELIABLE - AUTHORITATIVE SOURCE)
4. Be SPECIFIC and FACTUAL - ALWAYS check the piece list first
5. NEVER mention a piece on a square unless it's in the piece list

Provide a SPECIFIC comment on {active_player}'s move ({played_move_san}) following the format:
- Start with "{active_player} played {played_move_san}"
- Describe the position using the ASCII board, FEN, and piece list
- Explain WHY this specific move is {label_lower} based on the position
- Compare to the best move ({best_move_san}) and explain what {active_player} missed
```

**Position Representation Format:**
```
============================================================
CHESS POSITION REPRESENTATION
============================================================

**IMPORTANT: All three representations below show the SAME position (after the move).**

1. ASCII BOARD (Visual representation):

    a   b   c   d   e   f   g   h
  ─────────────────────────────────
8 | ♜ | ♞ | ♝ | ♛ | ♚ | ♝ | ♞ | ♜ | 8
  ─────────────────────────────────
7 | ♟ | ♟ | ♟ | ♟ | ♟ | ♟ | ♟ | ♟ | 7
...
    a   b   c   d   e   f   g   h

2. FEN NOTATION (Standard position encoding):
   rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1
   (Position AFTER e4 was played)

3. PIECE LOCATIONS (Explicit piece positions):
White pieces:
  King: e1
  Queen: d1
  Rooks: a1, h1
  ...
Black pieces:
  King: e8
  Queen: d8
  ...

**VERIFICATION:** All three representations above show the same position.
Use them together to verify piece locations and avoid errors.
============================================================
```

**LLM Call:**
```python
result = await self.chain.ainvoke({
    "position_representation": position_representation,
    "fen": fen_after,
    "active_player": active_player,
    "played_move_san": played_move_san,
    "best_move_san": best_move_san,
    "label": label,
    "label_lower": label.lower(),
    "eval_change": eval_change,
    "top_moves_context": top_moves_context,
    "played_move_eval": played_eval_str,
    "best_move_eval": best_eval_str,
    "evaluation_interpretation": evaluation_interpretation,
})
```

**LLM Model:** OpenAI `gpt-4o` (text-only)

**Structured Output:**
```python
class ExplanationOutput(BaseModel):
    explanation: str
```

**Output:**
```python
{
    "explanation": "White played e4. This is the best move because it controls the center, opens lines for the bishop and queen, and follows opening principles. The pawn on e4 supports future development and creates space for White's pieces."
}
```

---

### Node 5: `calculate_accuracy_rating`

**Input State:**
```python
{
    "classifications": [...],
    ...
}
```

**Process:**
1. Calls `AccuracyRatingService.calculate_game_accuracy(classifications)`
   - Calculates accuracy: `(best_moves + good_moves) / total_moves * 100`
   - Counts blunders, mistakes, inaccuracies
2. Calls `AccuracyRatingService.estimate_rating(accuracy, blunder_count)`
   - Estimates rating based on accuracy and mistake frequency

**Output State:**
```python
{
    "accuracy": 85,
    "estimated_rating": 1200,
    "rating_confidence": "medium",
    "accuracy_complete": True,
    "current_step": "calculating_accuracy",
    "progress_percentage": 90
}
```

**Conditional Edge:**
- If `accuracy_complete == False` → `finalize_review` (error)
- If `accuracy_complete == True` → `detect_weaknesses`

---

### Node 6: `detect_weaknesses`

**Input State:**
```python
{
    "classifications": [...],
    ...
}
```

**Process:**
1. Groups mistakes by game phase
2. Calls `WeaknessDetectionAgent.detect_weaknesses(classifications)`
3. LLM analyzes recurring patterns
4. Returns 3-5 weakness categories

**LLM Prompt:**
```
You are a chess coach analyzing a student's game to identify recurring weaknesses.

Analyze the following mistakes from a chess game and identify recurring weakness patterns:

Game Phase Breakdown:
{phase_breakdown}

Mistakes by Phase:
{mistakes_by_phase}

Return 3-5 weakness categories as a structured list.
```

**Structured Output:**
```python
class WeaknessOutput(BaseModel):
    weaknesses: List[str]
```

**Output State:**
```python
{
    "weaknesses": [
        "King safety",
        "Piece coordination",
        "Pawn structure"
    ],
    "weakness_detection_complete": True,
    "current_step": "detecting_weaknesses",
    "progress_percentage": 95
}
```

**Conditional Edge:**
- Always → `finalize_review`

---

### Node 7: `finalize_review`

**Input State:**
```python
{
    "review_complete": False,
    ...
}
```

**Process:**
1. Persists `GameSummary` to database
2. Sets `review_complete = True`
3. Creates `GameReviewOutput`

**Output State:**
```python
{
    "review_complete": True,
    "current_step": "completed",
    "progress_percentage": 100
}
```

**Output:**
```python
GameReviewOutput(
    game_id="uuid",
    status="success",
    error=None
)
```

---

## Step 5: Return to FastAPI Endpoint

**Process:**
1. Receives `GameReviewOutput` from supervisor
2. Loads complete data from database:
   - `MoveReview` records (with explanations)
   - `EngineAnalysis` records (with top moves)
   - `GameSummary` record
3. Builds `GameReviewResponse`
4. Returns JSON response

**Response:**
```json
{
    "game_id": "uuid",
    "moves": [
        {
            "ply": 1,
            "move_san": "e4",
            "quality": "Best",
            "evaluation": "+0.3",
            "top_moves": [
                {"move": "e4", "eval": "+0.3", "rank": 1},
                ...
            ],
            "explanation": "White played e4. This is the best move..."
        },
        ...
    ],
    "summary": {
        "accuracy": 85,
        "estimated_rating": 1200,
        "blunder_count": 2,
        "mistake_count": 5,
        "inaccuracy_count": 8
    }
}
```

---

## Step 6: Streamlit UI - Display Results

**Process:**
1. Receives JSON response
2. Displays:
   - Game ID
   - Accuracy percentage
   - Estimated rating
   - Move count
3. Shows "Review" tab with:
   - Interactive chess board
   - Move-by-move analysis
   - AI explanations
   - Top engine moves

---

## Key Data Flow

### FEN Flow:
```
PGN → Parse → For each ply:
  → Get position BEFORE move (FEN before)
  → Store FEN BEFORE in EngineAnalysis table
  → In explanation: Apply move → Get FEN AFTER
  → Generate position representation from FEN AFTER
  → All three representations (ASCII, FEN, piece list) use FEN AFTER
```

### Move Classification Flow:
```
Engine Analysis → Eval Delta Calculation → Classification:
  - Delta = 0 → "Best"
  - Delta < 0.3 → "Good"
  - Delta < 0.6 → "Inaccuracy"
  - Delta < 1.0 → "Mistake"
  - Delta >= 1.0 → "Blunder"
```

### Explanation Generation Flow:
```
Move Review → Engine Analysis → Explanation Agent:
  1. Get FEN BEFORE from database
  2. Apply move → Get FEN AFTER
  3. Generate position representation (ASCII + FEN + piece list)
  4. Determine active player
  5. Interpret evaluation
  6. Call LLM with structured output
  7. Store explanation in MoveReview
```

---

## Error Handling

**At Each Node:**
- If error occurs → Set `*_error` in state
- Set `review_error` with error message
- Route to `finalize_review` with error status
- Return error in `GameReviewOutput`

**API Level:**
- If `review_output.status == "error"` → Return HTTP 500
- If `move_reviews` is empty → Return HTTP 500
- If `summary` is missing → Return HTTP 500

---

## Performance Considerations

**Parallel Processing:**
- Explanation generation runs in parallel with semaphore limit (default: 10 concurrent)
- Uses `asyncio.gather()` for concurrent LLM calls

**Caching:**
- Engine analysis results cached in Redis
- Explanation results cached in database

**Adaptive Depth:**
- Standard depth: 10
- Deep depth: 20 (if eval delta > 1 pawn)

---

## Summary

**Total Steps:** 7 workflow nodes + 1 explanation LLM call per move

**Time Estimates:**
- 10 moves: ~2 minutes
- 20 moves: ~4 minutes
- 30 moves: ~6.5 minutes
- 40 moves: ~8.5 minutes
- 50 moves: ~11 minutes

**Key Technologies:**
- LangGraph for workflow orchestration
- OpenAI GPT-4o for explanations
- Stockfish for engine analysis
- PostgreSQL for persistence
- Redis for caching
