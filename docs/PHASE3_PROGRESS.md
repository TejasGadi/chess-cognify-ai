# Phase 3: Move Classification & Analysis - Progress

## Status: ✅ COMPLETE

---

## Tasks Completed

### 3.1 Move Classification Agent ✅

#### ✅ Created MoveClassificationService class (`app/services/move_classification_service.py`)
- **File**: `app/services/move_classification_service.py`
- **Class**: `MoveClassificationService`
- **Features**:
  - Deterministic classification (no LLM needed)
  - Evaluation string parsing (handles mate scores)
  - Threshold-based classification

#### ✅ Implemented evaluation delta calculation
- **Method**: `calculate_evaluation_delta()`
- **Formula**: `eval_after - eval_best` (in centipawns)
- **Handles**: Normal evaluations and mate scores
- **Returns**: Delta in centipawns (negative = worse than best)

#### ✅ Implemented classification logic with thresholds
- **Method**: `classify_move()`
- **Thresholds** (in pawns):
  - **Best**: `played_move == best_move` ✅
  - **Excellent**: `Δ ≥ -0.15` ✅
  - **Good**: `-0.15 > Δ ≥ -0.5` ✅
  - **Inaccuracy**: `-0.5 > Δ ≥ -1.0` ✅
  - **Mistake**: `-1.0 > Δ ≥ -2.0` ✅
  - **Blunder**: `Δ < -2.0` ✅
- **Returns**: Label, centipawn_loss, delta

#### ✅ Calculate centipawn loss per move
- **Calculation**: `abs(delta)` in centipawns
- **Stored**: As integer in MoveReview table
- **Used**: For accuracy calculation

#### ✅ Persist to MoveReview table
- **Method**: `persist_classifications()`
- **Features**:
  - Batch insert/update
  - Handles existing records
  - Transaction management

#### ✅ Return classification JSON
- **Format**: Matches MoveReview schema
- **Fields**: ply, label, centipawn_loss, delta

---

### 3.2 Accuracy & Rating Agent ✅

#### ✅ Created AccuracyRatingService class
- **File**: `app/services/accuracy_rating_service.py`
- **Class**: `AccuracyRatingService`
- **Purpose**: Calculate accuracy and estimate ratings

#### ✅ Implemented per-move accuracy calculation
- **Method**: `calculate_move_accuracy()`
- **Formula**: `max(0, 100 - (centipawn_loss * K))`
- **Constant K**: 1.0 (tunable, range 0.8-1.2)
- **Returns**: Accuracy score (0-100)

#### ✅ Implemented overall game accuracy
- **Method**: `calculate_game_accuracy()`
- **Calculation**: Mean of all move accuracies
- **Additional metrics**:
  - Blunder count
  - Mistake count
  - Inaccuracy count
  - Per-move accuracies list

#### ✅ Implemented rating estimation heuristic
- **Method**: `estimate_rating()`
- **Inputs**:
  - Accuracy (0-100)
  - Blunder count
  - Time control (optional)
- **Formula**:
  - Base rating: `400 + (accuracy * 16)`
  - Blunder penalty: `blunder_count * 50`
  - Final: `base_rating - blunder_penalty`
  - Clamped to 400-2500 range
- **Output**:
  - Estimated rating (integer)
  - Confidence level ("low", "medium", "high")

#### ✅ Persist to GameSummary table
- **Method**: `persist_game_summary()`
- **Stores**:
  - Overall accuracy
  - Estimated rating
  - Rating confidence
  - Weaknesses (from Phase 4, optional)

#### ✅ Return accuracy and rating JSON
- **Format**: Matches GameSummary schema
- **Fields**: accuracy, estimated_rating, rating_confidence

---

### 3.3 Game Phase Detection ✅

#### ✅ Implemented phase tagging logic
- **Location**: Already in `PGNService.detect_game_phase()`
- **Logic**:
  - **Opening**: First 24 plies (moves 1-12) ✅
  - **Endgame**: 6 or fewer non-pawn pieces ✅
  - **Middlegame**: Everything else ✅

#### ✅ Add phase metadata to move classifications
- **Method**: `add_game_phases()` in MoveClassificationService
- **Integration**: Uses PGNService to detect phases
- **Stored**: Phase added to classification dictionary
- **Values**: "opening", "middlegame", "endgame", "unknown"

---

## Files Created

1. **`app/services/move_classification_service.py`** (280 lines)
   - MoveClassificationService class
   - Evaluation parsing and delta calculation
   - Threshold-based classification
   - Phase detection integration

2. **`app/services/accuracy_rating_service.py`** (250 lines)
   - AccuracyRatingService class
   - Accuracy calculation (per-move and overall)
   - Rating estimation heuristic
   - Database persistence

3. **`app/services/__init__.py`** (updated)
   - Exports for new service classes

---

## Key Design Decisions

### Evaluation Parsing
- Handles both normal evaluations ("+0.4") and mate scores ("M2")
- Mate scores converted to large centipawn values (±10000)
- Robust error handling for malformed strings

### Classification Thresholds
- Based on standard chess.com/Lichess thresholds
- All comparisons in pawns (converted from centipawns)
- Deterministic - same input always produces same output

### Accuracy Calculation
- Formula: `max(0, 100 - (centipawn_loss * K))`
- K = 1.0 (tunable parameter)
- Per-move accuracy averaged for overall game accuracy

### Rating Estimation
- Heuristic-based (not Elo mathematics)
- Considers accuracy and blunder count
- Time control awareness (lower confidence for fast games)
- Clamped to reasonable range (400-2500)

### Phase Detection
- Reuses existing PGNService method
- Integrated into classification workflow
- Stored as metadata in classification results

---

## Integration Points

### With Phase 2 Components
- ✅ Uses `EngineAnalysis` model for input data
- ✅ Reads from `EngineAnalysis` table
- ✅ Uses `PGNService` for phase detection

### Database Integration
- ✅ Writes to `MoveReview` table (classifications, accuracies)
- ✅ Writes to `GameSummary` table (overall metrics)
- ✅ Handles updates for existing records

### Ready for Phase 4
- Classifications ready for explanation generation
- Phase information available for weakness detection
- Accuracy scores ready for display

---

## Usage Example

```python
from app.services.move_classification_service import MoveClassificationService
from app.services.accuracy_rating_service import AccuracyRatingService

# Classify moves
classification_service = MoveClassificationService()
classifications = classification_service.classify_game_moves(game_id)

# Add phases
classifications = classification_service.add_game_phases(
    game_id, classifications, pgn_string
)

# Persist classifications
classification_service.persist_classifications(game_id, classifications)

# Calculate accuracy and rating
accuracy_service = AccuracyRatingService()
accuracy_metrics = accuracy_service.calculate_game_accuracy(classifications)

# Update move accuracies
accuracy_service.update_move_accuracies(game_id, classifications)

# Estimate rating
rating_info = accuracy_service.estimate_rating(
    accuracy_metrics["accuracy"],
    accuracy_metrics["blunder_count"],
    time_control="600+0"
)

# Persist summary
accuracy_service.persist_game_summary(
    game_id,
    accuracy_metrics["accuracy"],
    rating_info["estimated_rating"],
    rating_info["confidence"]
)
```

---

## Testing Notes

### Manual Testing
1. **Classification**:
   - Test with various evaluation deltas
   - Verify threshold boundaries
   - Test mate score handling

2. **Accuracy**:
   - Test with different centipawn losses
   - Verify formula correctness
   - Test edge cases (0 loss, very high loss)

3. **Rating**:
   - Test with different accuracy/blunder combinations
   - Verify confidence levels
   - Test time control adjustments

### Prerequisites
- Engine analysis results in database
- MoveReview and GameSummary tables exist

---

## Next Steps

Phase 3 is complete. Ready to proceed with:

**Phase 4: AI Explanation Agents**
- Explanation Agent (Groq LLM for mistake explanations)
- Weakness Detection Agent (pattern detection)

---

## Changes from Original Plan

### Added
- Evaluation string parsing (handles mate scores)
- Phase detection integration in classification service
- Update methods for existing database records
- Helper methods for retrieving classifications

### Enhanced
- More robust error handling
- Better mate score handling
- Time control awareness in rating estimation
- Comprehensive logging

---

## Status Summary

| Task | Status | Notes |
|------|--------|-------|
| 3.1 Move Classification Agent | ✅ Complete | All 6 subtasks done |
| 3.2 Accuracy & Rating Agent | ✅ Complete | All 6 subtasks done |
| 3.3 Game Phase Detection | ✅ Complete | Integrated with classification |

**Phase 3: 100% Complete** 🎉
