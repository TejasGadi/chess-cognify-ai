import os
from typing import List, Dict, Any
from langchain_core.documents import Document
from langchain_docling import DoclingLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_qdrant import QdrantVectorStore
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.http import models
from app.config import settings
from sqlalchemy.orm import Session
from app.models.book import Book
from app.utils.logger import get_logger

logger = get_logger(__name__)

class BookProcessor:
    """
    Service for processing PDF books using Docling and storing embeddings in Qdrant.
    """
    
    def __init__(self):
        """Initialize Qdrant client and embedding model."""
        self.qdrant_client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key
        )
        
        self.embedding_model = OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            api_key=settings.openai_api_key
        )
        
        self.collection_name = settings.qdrant_collection_name
        self._ensure_collection_exists()

    def get_status(self, db: Session, book_id: str) -> Dict[str, Any]:
        """Get processing status for a specific book from database."""
        book = db.query(Book).filter(Book.book_id == book_id).first()
        if not book:
            return {"status": "unknown"}
        
        return {
            "status": book.status,
            "message": self._get_status_message(book.status, book.error_message),
            "filename": book.filename,
            "chunks": book.total_chunks
        }
    
    def _get_status_message(self, status: str, error_message: str = None) -> str:
        """Generate user-friendly status message."""
        messages = {
            "pending": "Waiting to start...",
            "processing": "Processing PDF...",
            "completed": "Book processed successfully!",
            "failed": error_message or "Processing failed"
        }
        return messages.get(status, "Unknown status")

    def _ensure_collection_exists(self):
        """Ensure the vectors collection exists in Qdrant."""
        try:
            collections = self.qdrant_client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            
            if not exists:
                logger.info(f"Creating Qdrant collection: {self.collection_name}")
                # Dimension for text-embedding-3-small is 1536
                vector_size = 1536
                
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=vector_size,
                        distance=models.Distance.COSINE
                    )
                )
        except Exception as e:
            logger.error(f"Error checking/creating Qdrant collection: {e}")
            raise

    async def process_and_store_book(self, db: Session, book_id: str, file_path: str, filename: str) -> Dict[str, Any]:
        """
        Process a PDF book and store its embeddings.
        
        Args:
            db: Database session
            book_id: Book ID from database
            file_path: Absolute path to the PDF file
            filename: Original filename for metadata
            
        Returns:
            Dict with processing stats
        """
        book = db.query(Book).filter(Book.book_id == book_id).first()
        if not book:
            logger.error(f"Book {book_id} not found in database")
            return {"status": "failed", "error": "Book not found"}
        
        try:
            logger.info(f"Starting processing for book: {filename} (ID: {book_id})")
            
            # Update status to processing
            book.status = "processing"
            db.commit()
            
            # 1. Load and parse PDF using Docling
            # Docling handles tables and layout better than pypdf
            loader = DoclingLoader(file_path=file_path)
            docs = loader.load()
            
            logger.info(f"Docling parsed {len(docs)} document structures")
            
            # 2. Split into chunks
            # Even though Docling gives structured output, we ensure manageable chunk sizes
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                add_start_index=True
            )
            
            splits = text_splitter.split_documents(docs)
            logger.info(f"Created {len(splits)} text chunks")
            
            # 3. Add metadata
            for split in splits:
                split.metadata["source"] = filename
                split.metadata["file_path"] = file_path
                split.metadata["book_id"] = book_id  # Add book_id for filtering
                # Docling might add other metadata, preserve it
            
            # 4. Store in Qdrant
            # QdrantVectorStore handles the embedding generation using the provided model
            vector_store = QdrantVectorStore(
                client=self.qdrant_client,
                collection_name=self.collection_name,
                embedding=self.embedding_model,
            )
            
            # Upsert documents
            # Note: This might take time for large books
            vector_store.add_documents(documents=splits)
            
            
            logger.info(f"Successfully stored {len(splits)} chunks in Qdrant")
            
            # Update status to completed
            book.status = "completed"
            book.total_chunks = len(splits)
            db.commit()
            
            return {
                "status": "success",
                "chunks": len(splits),
                "filename": filename
            }
            
            
        except Exception as e:
            logger.error(f"Error processing book {filename}: {e}", exc_info=True)
            
            book.status = "failed"
            book.error_message = str(e)
            db.commit()
            
            return {
                "status": "failed",
                "error": str(e),
                "filename": filename
            }


# Global instance
book_processor = BookProcessor()
