"""
API endpoints for book management and book chatbot.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
from app.models.base import get_db
from app.services.book_service import BookService
from app.agents.book_chatbot import BookChatbotAgent
from app.services.chat_service import ChatService
from app.schemas.book import (
    BookResponse,
    BookChatRequest,
    BookChatResponse,
    BookListResponse,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

books_router = APIRouter(prefix="/api/books", tags=["books"])

# Initialize services
book_service = BookService()
book_chatbot = BookChatbotAgent()
chat_service = ChatService()


@books_router.post("/upload", response_model=BookResponse, status_code=201)
async def upload_book(
    file: UploadFile = File(..., description="PDF file to upload"),
    title: Optional[str] = Form(None),
    author: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """
    Upload and process a chess book PDF.

    - **file**: PDF file (required)
    - **title**: Optional book title
    - **author**: Optional book author

    The PDF will be processed, chunked, and embedded into the vector database.
    """
    try:
        # Validate file type
        if not file.filename.endswith(".pdf"):
            raise HTTPException(
                status_code=400, detail="Only PDF files are supported"
            )

        # Read file content
        content = await file.read()
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="File is empty")

        # Upload and process
        book = book_service.upload_book(
            db=db,
            file_content=content,
            filename=file.filename,
            title=title,
            author=author,
        )

        logger.info(f"Book uploaded successfully: {book.book_id}")
        return book

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading book: {e}")
        raise HTTPException(status_code=500, detail=f"Error uploading book: {str(e)}")


@books_router.get("/", response_model=BookListResponse)
def list_books(
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    List all uploaded books.

    - **limit**: Maximum number of books to return (default: 100)
    """
    try:
        books = book_service.list_books(db=db, limit=limit)
        return BookListResponse(books=books, total=len(books))
    except Exception as e:
        logger.error(f"Error listing books: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing books: {str(e)}")


@books_router.get("/{book_id}", response_model=BookResponse)
def get_book(
    book_id: str,
    db: Session = Depends(get_db),
):
    """
    Get book details by ID.

    - **book_id**: Book ID
    """
    try:
        book = book_service.get_book(db=db, book_id=book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        return book
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting book: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting book: {str(e)}")


@books_router.delete("/{book_id}", status_code=204)
def delete_book(
    book_id: str,
    db: Session = Depends(get_db),
):
    """
    Delete a book and all its associated documents.

    - **book_id**: Book ID
    """
    try:
        deleted = book_service.delete_book(db=db, book_id=book_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Book not found")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting book: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting book: {str(e)}")


@books_router.post("/{book_id}/chat", response_model=BookChatResponse)
async def chat_with_book(
    book_id: str,
    request: BookChatRequest,
    db: Session = Depends(get_db),
):
    """
    Chat with a specific book using RAG.

    - **book_id**: Book ID
    - **message**: User question
    - **session_id**: Optional session ID for conversation history

    Returns AI-generated response based on book content.
    """
    try:
        # Verify book exists
        book = book_service.get_book(db=db, book_id=book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        # Get or create session ID
        session_id = request.session_id or chat_service.create_session_id()

        # Get conversation history if session exists
        conversation_history = chat_service.get_conversation_history(
            db=db, game_id=None, session_id=session_id, context_type="book"
        )

        # Get response from chatbot
        result = book_chatbot.chat(
            query=request.message,
            book_id=book_id,
            conversation_history=conversation_history,
        )

        # Save messages to database
        chat_service.add_message(
            db=db,
            game_id=None,
            session_id=session_id,
            role="user",
            content=request.message,
            context_type="book",
            context_id=book_id,
        )
        chat_service.add_message(
            db=db,
            game_id=None,
            session_id=session_id,
            role="assistant",
            content=result["response"],
            context_type="book",
            context_id=book_id,
        )

        return BookChatResponse(
            response=result["response"],
            book_id=book_id,
            session_id=session_id,
            sources=result.get("sources", []),
            metadata=result.get("metadata", {}),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in book chat: {e}")
        raise HTTPException(status_code=500, detail=f"Error in book chat: {str(e)}")


@books_router.post("/chat", response_model=BookChatResponse)
async def chat_with_all_books(
    request: BookChatRequest,
    db: Session = Depends(get_db),
):
    """
    Chat across all uploaded books using RAG.

    - **message**: User question
    - **session_id**: Optional session ID for conversation history

    Searches across all books in the vector database.
    """
    try:
        # Get or create session ID
        session_id = request.session_id or chat_service.create_session_id()

        # Get conversation history if session exists
        conversation_history = chat_service.get_conversation_history(
            db=db, game_id=None, session_id=session_id, context_type="book"
        )

        # Get response from chatbot (no book_id = search all books)
        result = book_chatbot.chat(
            query=request.message,
            book_id=None,  # Search all books
            conversation_history=conversation_history,
        )

        # Save messages to database
        chat_service.add_message(
            db=db,
            game_id=None,
            session_id=session_id,
            role="user",
            content=request.message,
            context_type="book",
            context_id=None,  # All books
        )
        chat_service.add_message(
            db=db,
            game_id=None,
            session_id=session_id,
            role="assistant",
            content=result["response"],
            context_type="book",
            context_id=None,
        )

        return BookChatResponse(
            response=result["response"],
            book_id=None,
            session_id=session_id,
            sources=result.get("sources", []),
            metadata=result.get("metadata", {}),
        )

    except Exception as e:
        logger.error(f"Error in book chat: {e}")
        raise HTTPException(status_code=500, detail=f"Error in book chat: {str(e)}")
