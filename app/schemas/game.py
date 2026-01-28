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


class GameUpdate(BaseModel):
    """Schema for updating a game."""

    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Updated game metadata"
    )


class GameResponse(BaseModel):
    """Schema for game response."""

    game_id: str
    pgn: str
    metadata: Optional[Dict[str, Any]] = Field(None, alias="game_metadata")
    status: str = "pending"
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True

    @model_validator(mode='before')
    @classmethod
    def extract_metadata(cls, data):
        """Ensure status is never None and handle attribute mapping."""
        if hasattr(data, 'game_metadata'):
            # If it's a model object, we need to handle the mapping manually sometimes
            # or Ensure status is not None
            return {
                'game_id': data.game_id,
                'pgn': data.pgn,
                'game_metadata': data.game_metadata,
                'status': getattr(data, 'status', "pending") or "pending",
                'error_message': getattr(data, 'error_message', None),
                'created_at': data.created_at,
            }
        return data


class TopMoveInfo(BaseModel):
    """Schema for a single top move."""
    move: str  # UCI format
    move_san: str  # SAN notation
    eval: float  # Centipawns
    eval_str: str  # Human-readable
    rank: int  # 1 = best, 2 = second best, etc.
    pv_san: Optional[List[str]] = None


class EngineAnalysisResponse(BaseModel):
    """Schema for engine analysis per move."""

    ply: int
    fen: str
    played_move: str
    best_move: str
    eval_before: str
    eval_after: str
    eval_best: str
    top_moves: Optional[List[TopMoveInfo]] = None  # Top 5 moves with evaluations
    played_move_eval: Optional[str] = None  # Evaluation of played move
    played_move_rank: Optional[int] = None  # Rank of played move in top moves

    class Config:
        from_attributes = True
    
    @model_validator(mode='before')
    @classmethod
    def convert_top_moves(cls, data):
        """Convert top_moves from dict/list to TopMoveInfo objects."""
        if isinstance(data, dict) and "top_moves" in data and data["top_moves"]:
            # Convert list of dicts to list of TopMoveInfo
            if isinstance(data["top_moves"], list):
                data["top_moves"] = [TopMoveInfo(**move) if isinstance(move, dict) else move for move in data["top_moves"]]
        return data


class MoveReviewResponse(BaseModel):
    """Schema for move review."""

    ply: int
    label: str
    centipawn_loss: Optional[int] = None
    explanation: Optional[str] = None
    accuracy: Optional[int] = None
    move_san: Optional[str] = None  # SAN notation of the move
    eval_after: Optional[str] = None  # Evaluation after the move
    top_moves: Optional[List[TopMoveInfo]] = None  # Top 5 engine moves

    class Config:
        from_attributes = True


class GameSummaryResponse(BaseModel):
    """Schema for game summary."""

    accuracy: Optional[int] = None
    estimated_rating: Optional[int] = None
    rating_confidence: Optional[str] = None
    weaknesses: Optional[List[str]] = None
    details: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class GameReviewResponse(BaseModel):
    """Complete game review response."""

    game_id: str
    game: GameResponse
    moves: List[MoveReviewResponse]
    summary: Optional[GameSummaryResponse] = None
