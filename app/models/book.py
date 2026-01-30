"""
Book-related database models.
"""
from sqlalchemy import Column, String, Integer, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.models.base import Base
import uuid


class Book(Base):
    """Book model - stores book metadata and file information."""

    __tablename__ = "books"
    __mapper_args__ = {"exclude_properties": ["metadata"]}

    book_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    author = Column(String, nullable=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=True)  # Optional: store file path if needed
    status = Column(String, nullable=False, default='pending')  # 'pending', 'processing', 'completed', 'failed'
    error_message = Column(Text, nullable=True)  # Error details if status is 'failed'
    total_pages = Column(Integer, nullable=True)
    total_chunks = Column(Integer, nullable=True)  # Number of text chunks created
    book_metadata = Column("metadata", JSON, nullable=True)  # Additional metadata (ISBN, year, etc.)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        {"comment": "Chess books uploaded for chatbot"},
    )
