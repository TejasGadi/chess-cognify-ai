"""
Pydantic schemas for chat endpoints.
"""
from pydantic import BaseModel, Field
from typing import Optional, List


class ChatMessageRequest(BaseModel):
    """Schema for chat message request."""

    message: str = Field(..., description="User's message/question", min_length=1, max_length=1000)
    session_id: Optional[str] = Field(
        None, description="Chat session ID (auto-created if not provided)"
    )


class ChatMessageResponse(BaseModel):
    """Schema for chat message response."""

    response: str
    game_id: str
    session_id: str


class ChatHistoryResponse(BaseModel):
    """Schema for chat history response."""

    game_id: str
    session_id: str
    messages: List[dict] = Field(
        ..., description="List of messages with role and content"
    )
