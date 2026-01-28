"""
Game-related database models.
"""
from sqlalchemy import Column, String, Integer, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.models.base import Base
import uuid


class Game(Base):
    """Game model - stores PGN and metadata."""

    __tablename__ = "games"

    game_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    pgn = Column(Text, nullable=False)
    game_metadata = Column("metadata", JSON, nullable=True)  # time_control, player_color, etc.
    status = Column(String, default="pending")  # pending, analyzing, completed, failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class EngineAnalysis(Base):
    """Engine analysis results per move."""

    __tablename__ = "engine_analysis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(String, nullable=False, index=True)
    ply = Column(Integer, nullable=False)  # Half-move number
    fen = Column(String, nullable=False)
    played_move = Column(String, nullable=False)
    best_move = Column(String, nullable=False)
    eval_before = Column(String, nullable=False)  # Store as string (e.g., "+0.4")
    eval_after = Column(String, nullable=False)
    eval_best = Column(String, nullable=False)
    top_moves = Column(JSON, nullable=True)  # Top 5 moves with evaluations: [{"move": "...", "move_san": "...", "eval": ..., "eval_str": "...", "rank": ...}, ...]
    played_move_eval = Column(String, nullable=True)  # Evaluation of played move
    played_move_rank = Column(Integer, nullable=True)  # Rank of played move in top moves (1-5, or None if not in top 5)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        {"comment": "Cached Stockfish analysis results per move"},
    )


class MoveReview(Base):
    """Processed move review with classification and explanation."""

    __tablename__ = "move_review"

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(String, nullable=False, index=True)
    ply = Column(Integer, nullable=False)
    label = Column(String, nullable=False)  # Best, Excellent, Good, Inaccuracy, Mistake, Blunder
    centipawn_loss = Column(Integer, nullable=True)
    explanation = Column(Text, nullable=True)  # AI-generated explanation
    accuracy = Column(Integer, nullable=True)  # Move accuracy score (0-100)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        {"comment": "Classified moves with explanations"},
    )


class GameSummary(Base):
    """Overall game summary and statistics."""

    __tablename__ = "game_summary"

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(String, nullable=False, unique=True, index=True)
    accuracy = Column(Integer, nullable=True)  # Overall game accuracy
    estimated_rating = Column(Integer, nullable=True)
    rating_confidence = Column(String, nullable=True)  # low, medium, high
    weaknesses = Column(JSON, nullable=True)  # List of weakness strings
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        {"comment": "Game-level summary and statistics"},
    )
