"""
LangGraph state management for game review workflow.
"""
from typing import TypedDict, List, Dict, Any, Optional, Literal
from pydantic import BaseModel


class GameReviewState(TypedDict):
    """
    State schema for game review workflow.
    
    All agents communicate via this shared state.
    """

    # Input
    game_id: str
    pgn: str
    metadata: Optional[Dict[str, Any]]

    # Validation
    pgn_valid: bool
    validation_error: Optional[str]

    # Engine Analysis
    engine_analyses: List[Dict[str, Any]]
    engine_analysis_complete: bool
    engine_analysis_error: Optional[str]

    # Move Classification
    classifications: List[Dict[str, Any]]
    classification_complete: bool
    classification_error: Optional[str]

    # Explanations
    explanations: Dict[int, str]  # ply -> explanation
    explanation_complete: bool
    explanation_error: Optional[str]

    # Accuracy & Rating
    accuracy: Optional[int]
    estimated_rating: Optional[int]
    rating_confidence: Optional[str]
    accuracy_complete: bool
    accuracy_error: Optional[str]

    # Weakness Detection
    weaknesses: List[str]
    weakness_detection_complete: bool
    weakness_error: Optional[str]

    # Final Review
    review_complete: bool
    review_error: Optional[str]

    # Progress tracking
    current_step: str
    progress_percentage: int


class GameReviewInput(BaseModel):
    """Input schema for game review request."""

    pgn: str
    metadata: Optional[Dict[str, Any]] = None
    game_id: Optional[str] = None  # Auto-generated if not provided


class GameReviewOutput(BaseModel):
    """Output schema for complete game review."""

    game_id: str
    pgn: str
    metadata: Optional[Dict[str, Any]]
    engine_analyses: List[Dict[str, Any]]
    classifications: List[Dict[str, Any]]
    explanations: Dict[int, str]
    accuracy: Optional[int]
    estimated_rating: Optional[int]
    rating_confidence: Optional[str]
    weaknesses: List[str]
    status: Literal["complete", "error"]
    error: Optional[str] = None
