"""
Pydantic schemas for game-related endpoints.
"""
from pydantic import BaseModel, Field, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime


class GameCreate(BaseModel):
    """Schema for creating a new game."""

    pgn: str = Field(..., description="PGN string of the game")
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Game metadata (time_control, player_color, etc.)"
    )


class GameResponse(BaseModel):
    """Schema for game response."""

    game_id: str
    pgn: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True
    
    @model_validator(mode='before')
    @classmethod
    def extract_metadata(cls, data):
        """Extract metadata from game_metadata field."""
        if hasattr(data, 'game_metadata'):
            # Convert SQLAlchemy model to dict
            return {
                'game_id': data.game_id,
                'pgn': data.pgn,
                'metadata': data.game_metadata,
                'created_at': data.created_at,
            }
        return data


class EngineAnalysisResponse(BaseModel):
    """Schema for engine analysis per move."""

    ply: int
    fen: str
    played_move: str
    best_move: str
    eval_before: str
    eval_after: str
    eval_best: str

    class Config:
        from_attributes = True


class MoveReviewResponse(BaseModel):
    """Schema for move review."""

    ply: int
    label: str
    centipawn_loss: Optional[int] = None
    explanation: Optional[str] = None
    accuracy: Optional[int] = None

    class Config:
        from_attributes = True


class GameSummaryResponse(BaseModel):
    """Schema for game summary."""

    accuracy: Optional[int] = None
    estimated_rating: Optional[int] = None
    rating_confidence: Optional[str] = None
    weaknesses: Optional[List[str]] = None

    class Config:
        from_attributes = True


class GameReviewResponse(BaseModel):
    """Complete game review response."""

    game_id: str
    game: GameResponse
    moves: List[MoveReviewResponse]
    summary: Optional[GameSummaryResponse] = None
