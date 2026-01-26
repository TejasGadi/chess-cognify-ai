"""
Pydantic schemas for book-related endpoints.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class BookUploadRequest(BaseModel):
    """Schema for book upload request."""

    title: Optional[str] = Field(None, description="Book title")
    author: Optional[str] = Field(None, description="Book author")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class BookResponse(BaseModel):
    """Schema for book response."""

    book_id: str
    title: str
    author: Optional[str] = None
    filename: str
    total_pages: Optional[int] = None
    total_chunks: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BookChatRequest(BaseModel):
    """Schema for book chat request."""

    message: str = Field(..., min_length=1, max_length=1000, description="User question")
    session_id: Optional[str] = Field(None, description="Optional session ID for conversation history")


class BookChatResponse(BaseModel):
    """Schema for book chat response."""

    response: str
    book_id: Optional[str] = None
    session_id: str
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="Source citations")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BookListResponse(BaseModel):
    """Schema for book list response."""

    books: List[BookResponse]
    total: int
