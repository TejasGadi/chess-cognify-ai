"""
Book service for managing book uploads and processing.
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.book import Book
from app.services.pdf_service import PDFService
from app.services.vector_store_service import VectorStoreService
from app.utils.logger import get_logger
import os
import shutil
from pathlib import Path

logger = get_logger(__name__)


class BookService:
    """Service for managing chess books."""

    def __init__(self, upload_dir: str = "uploads/books"):
        """
        Initialize book service.

        Args:
            upload_dir: Directory to store uploaded PDF files
        """
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.pdf_service = PDFService()
        self.vector_store_service = VectorStoreService()

    def upload_book(
        self,
        db: Session,
        file_content: bytes,
        filename: str,
        title: Optional[str] = None,
        author: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Book:
        """
        Upload and process a book PDF.

        Args:
            db: Database session
            file_content: PDF file content as bytes
            filename: Original filename
            title: Optional book title
            author: Optional book author
            metadata: Optional additional metadata

        Returns:
            Created Book model instance
        """
        try:
            # Create book record
            book = Book(
                title=title or filename.replace(".pdf", "").replace("_", " "),
                author=author,
                filename=filename,
                metadata=metadata or {},
            )
            db.add(book)
            db.flush()  # Get book_id

            # Save file
            file_path = self.upload_dir / f"{book.book_id}_{filename}"
            with open(file_path, "wb") as f:
                f.write(file_content)
            book.file_path = str(file_path)

            # Process PDF
            logger.info(f"Processing PDF for book {book.book_id}: {filename}")
            processed = self.pdf_service.process_pdf(
                str(file_path), book_id=book.book_id
            )

            # Update book metadata
            book.total_pages = processed["total_pages"]
            book.total_chunks = len(processed["chunks"])

            # Initialize vector store if needed
            try:
                self.vector_store_service.initialize_collection(force_recreate=False)
            except Exception as e:
                logger.warning(f"Collection initialization warning: {e}")

            # Add chunks to vector store
            doc_ids = self.vector_store_service.add_documents(
                processed["chunks"], book_id=book.book_id
            )

            db.commit()
            logger.info(
                f"Successfully uploaded book {book.book_id}: "
                f"{book.total_pages} pages, {book.total_chunks} chunks"
            )

            return book

        except Exception as e:
            db.rollback()
            logger.error(f"Error uploading book: {e}")
            raise

    def get_book(self, db: Session, book_id: str) -> Optional[Book]:
        """
        Get book by ID.

        Args:
            db: Database session
            book_id: Book ID

        Returns:
            Book model instance or None
        """
        return db.query(Book).filter(Book.book_id == book_id).first()

    def list_books(self, db: Session, limit: int = 100) -> List[Book]:
        """
        List all books.

        Args:
            db: Database session
            limit: Maximum number of books to return

        Returns:
            List of Book model instances
        """
        return db.query(Book).order_by(Book.created_at.desc()).limit(limit).all()

    def delete_book(self, db: Session, book_id: str) -> bool:
        """
        Delete a book and its associated documents.

        Args:
            db: Database session
            book_id: Book ID

        Returns:
            True if deleted, False if not found
        """
        try:
            book = self.get_book(db, book_id)
            if not book:
                return False

            # Delete from vector store
            deleted_count = self.vector_store_service.delete_book_documents(book_id)
            logger.info(f"Deleted {deleted_count} vector documents for book {book_id}")

            # Delete file if exists
            if book.file_path and os.path.exists(book.file_path):
                os.remove(book.file_path)
                logger.info(f"Deleted file: {book.file_path}")

            # Delete from database
            db.delete(book)
            db.commit()

            logger.info(f"Successfully deleted book {book_id}")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting book {book_id}: {e}")
            raise
