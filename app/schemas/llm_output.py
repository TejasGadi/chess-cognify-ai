"""
Pydantic schemas for LLM structured output.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal


class ExplanationOutput(BaseModel):
    """Structured output for move explanations."""

    explanation: str = Field(
        ...,
        description="Clear, educational explanation of why the best move is better (max 4 sentences)",
    )


class WeaknessOutput(BaseModel):
    """Structured output for weakness detection."""

    weaknesses: List[str] = Field(
        ...,
        description="List of 3-5 high-level weakness categories (chess concepts, not specific moves)",
        min_length=3,
        max_length=5,
    )


class PiecePositions(BaseModel):
    """Piece positions grouped by type."""
    King: List[str] = Field(default_factory=list, description="King squares (usually 1)")
    Queen: List[str] = Field(default_factory=list, description="Queen squares (usually 0-1)")
    Rooks: List[str] = Field(default_factory=list, description="Rook squares")
    Bishops: List[str] = Field(default_factory=list, description="Bishop squares")
    Knights: List[str] = Field(default_factory=list, description="Knight squares")
    Pawns: List[str] = Field(default_factory=list, description="Pawn squares")


class PositionExtractionOutput(BaseModel):
    """Structured output for position extraction step."""
    
    white_pieces: PiecePositions = Field(
        ...,
        description="White pieces by type with their square locations"
    )
    black_pieces: PiecePositions = Field(
        ...,
        description="Black pieces by type with their square locations"
    )
    active_color: Literal["White", "Black"] = Field(
        ...,
        description="Color to move in this position"
    )
    last_move_square: Optional[str] = Field(
        None,
        description="Square where the last piece moved to (e.g., 'e4', 'd5')"
    )
    verification_status: Literal["verified", "needs_review"] = Field(
        "needs_review",
        description="Status of position extraction verification"
    )
    confidence: float = Field(
        ...,
        description="Confidence in extraction accuracy (0.0 to 1.0)",
        ge=0.0,
        le=1.0
    )


class ExplanationValidationOutput(BaseModel):
    """Structured output for explanation validation."""
    
    is_valid: bool = Field(
        ...,
        description="Whether the explanation is valid (no hallucinations or impossible moves)"
    )
    discrepancies: List[str] = Field(
        default_factory=list,
        description="List of specific errors found (e.g., 'Mentions knight on b5 but knight is on b3', 'Mentions impossible move knight from b3 to c4')"
    )
    confidence_score: float = Field(
        ...,
        description="Confidence in validation (0.0 to 1.0). Higher = more confident explanation is correct.",
        ge=0.0,
        le=1.0
    )
    needs_revision: bool = Field(
        ...,
        description="Whether the explanation needs to be revised due to errors"
    )
