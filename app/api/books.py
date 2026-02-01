from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
import os
import shutil
import uuid

from app.services.book_processor import book_processor
from app.services.rag_service import rag_service
from app.utils.logger import get_logger
from app.models.book import Book
from app.models.base import get_db, SessionLocal

router = APIRouter(prefix="/api/books", tags=["books"])
logger = get_logger(__name__)

# Uploads directory
UPLOAD_DIR = "uploads/books"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    answer: str
    chess_data: Optional[List[Dict[str, Any]]] = None
    sources: Optional[List[Dict[str, Any]]] = None
    status: str

class BookResponse(BaseModel):
    book_id: str
    title: str
    filename: str
    status: str
    error_message: Optional[str] = None
    total_chunks: Optional[int] = None
    created_at: str
    
    class Config:
        from_attributes = True

@router.post("/upload")
async def upload_book(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a chess book (PDF) for processing.
    Processing happens in the background.
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    book_id = str(uuid.uuid4())
    safe_filename = f"{book_id}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    
    try:
        # Save file to disk
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Create book record in database
        book = Book(
            book_id=book_id,
            title=file.filename.replace('.pdf', ''),
            filename=file.filename,
            file_path=file_path,
            status='pending'
        )
        db.add(book)
        db.commit()
        db.refresh(book)
            
        # Trigger background processing
        background_tasks.add_task(
            _process_book_task, 
            book_id,
            file_path, 
            file.filename
        )
        
        return {
            "message": "Book uploaded successfully. Processing started in background.",
            "book_id": book_id,
            "filename": file.filename
        }
    except Exception as e:
        logger.error(f"Error uploading book: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

async def _process_book_task(book_id: str, file_path: str, filename: str):
    """Background task wrapper for book processing."""
    from app.models.base import SessionLocal
    db = SessionLocal()
    try:
        result = await book_processor.process_and_store_book(db, book_id, file_path, filename)
        if result["status"] == "failed":
            logger.error(f"Background processing failed for {filename}: {result.get('error')}")
        else:
            logger.info(f"Background processing completed for {filename}")
    finally:
        db.close()

@router.get("", response_model=List[BookResponse])
async def list_books(db: Session = Depends(get_db)):
    """Get list of all books."""
    books = db.query(Book).order_by(Book.created_at.desc()).all()
    return [
        BookResponse(
            book_id=book.book_id,
            title=book.title,
            filename=book.filename,
            status=book.status,
            error_message=book.error_message,
            total_chunks=book.total_chunks,
            created_at=book.created_at.isoformat() if book.created_at else None
        )
        for book in books
    ]

@router.get("/{book_id}", response_model=BookResponse)
async def get_book(book_id: str, db: Session = Depends(get_db)):
    """Get details of a specific book."""
    book = db.query(Book).filter(Book.book_id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    return BookResponse(
        book_id=book.book_id,
        title=book.title,
        filename=book.filename,
        status=book.status,
        error_message=book.error_message,
        total_chunks=book.total_chunks,
        created_at=book.created_at.isoformat() if book.created_at else None
    )

def _collect_outline_labels(node: Optional[Dict[str, Any]], max_depth: int, depth: int = 0) -> List[str]:
    """Collect label strings from outline tree up to max_depth for suggested queries."""
    if not node or depth > max_depth:
        return []
    labels = []
    label = (node.get("label") or "").strip()
    if label and label.lower() != "document":
        labels.append(label)
    for child in node.get("children") or []:
        labels.extend(_collect_outline_labels(child, max_depth, depth + 1))
    return labels


@router.get("/{book_id}/mindmap")
async def get_book_mindmap(book_id: str, db: Session = Depends(get_db)):
    """
    Get document structure (mindmap) and suggested queries for the book.
    Returns outline tree from Docling parsing and query suggestions derived from section labels.
    """
    book = db.query(Book).filter(Book.book_id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    mindmap = getattr(book, "outline", None) or (book.book_metadata or {}).get("outline")
    suggested_queries: List[str] = []
    if mindmap and isinstance(mindmap, dict):
        labels = _collect_outline_labels(mindmap, max_depth=2)[:20]
        seen = set()
        for label in labels:
            if not label or label in seen:
                continue
            seen.add(label)
            suggested_queries.append(f"Explain {label}")
            suggested_queries.append(f"What does the book say about {label}?")
            if len(suggested_queries) >= 15:
                break
        suggested_queries = suggested_queries[:15]
    return {"mindmap": mindmap, "suggested_queries": suggested_queries}


@router.get("/{book_id}/status")
async def get_book_status(book_id: str, db: Session = Depends(get_db)):
    """Get the processing status of a book."""
    status = book_processor.get_status(db, book_id)
    if status["status"] == "unknown":
        raise HTTPException(status_code=404, detail="Book not found")
    return status

@router.post("/{book_id}/query", response_model=QueryResponse)
async def query_book(book_id: str, request: QueryRequest, db: Session = Depends(get_db)):
    """
    Query a specific chess book.
    """
    # Verify book exists
    book = db.query(Book).filter(Book.book_id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    if book.status != 'completed':
        raise HTTPException(status_code=400, detail=f"Book is not ready for queries. Status: {book.status}")
    
    try:
        result = await rag_service.query(request.query, book_id=book_id)
        return result
    except Exception as e:
        logger.error(f"Error in book query endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{book_id}")
async def delete_book(book_id: str, db: Session = Depends(get_db)):
    """Delete a book and its vectors."""
    book = db.query(Book).filter(Book.book_id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    try:
        # TODO: Delete vectors from Qdrant by book_id filter
        # For now, just delete the database record
        db.delete(book)
        db.commit()
        
        # Delete file if it exists
        if book.file_path and os.path.exists(book.file_path):
            os.remove(book.file_path)
        
        return {"message": "Book deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting book: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
