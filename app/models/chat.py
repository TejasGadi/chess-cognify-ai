"""
Chat-related database models.
"""
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from app.models.base import Base


class ChatMessage(Base):
    """Chat message model for game review and book conversations."""

    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(String, ForeignKey("games.game_id"), nullable=True, index=True)  # Optional for book chats
    session_id = Column(String, nullable=False, index=True)  # For conversation grouping
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    context_type = Column(String, nullable=True, index=True)  # "game" or "book"
    context_id = Column(String, nullable=True, index=True)  # game_id or book_id depending on context_type
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        {"comment": "Chat messages for game review and book conversations"},
    )
