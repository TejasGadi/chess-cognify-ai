import os
from typing import List, Dict, Any
from langchain_core.documents import Document
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_qdrant import QdrantVectorStore
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.http import models
from app.config import settings
from sqlalchemy.orm import Session
from app.models.book import Book
from app.utils.logger import get_logger
from PIL import Image
import hashlib

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
            
            # 1. Setup Docling Converter with image extraction
            pipeline_options = PdfPipelineOptions()
            pipeline_options.generate_picture_images = True
            
            converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
                }
            )
            
            # 2. Convert PDF
            result = converter.convert(file_path)
            doc = result.document
            
            # 3. Process items and extract images
            processed_docs = []
            current_image_url = None
            
            # Create book-specific image directory
            book_image_dir = os.path.join("uploads/book_images", book_id)
            os.makedirs(book_image_dir, exist_ok=True)
            
            # Buffering logic for larger chunks
            current_text_block = []
            current_metadata = {}
            
            def flush_block():
                if current_text_block:
                    full_text = "\n\n".join(current_text_block)
                    if len(full_text.strip()) > 50:
                        processed_docs.append(Document(page_content=full_text, metadata=current_metadata.copy()))
                    current_text_block.clear()

            for item, level in doc.iterate_items():
                # Check for image
                if hasattr(item, 'image') and item.image:
                    # Flush previous block before starting new image context
                    flush_block()
                    
                    img = item.get_image(doc)
                    if img:
                        img_filename = f"img_{hashlib.md5(item.self_ref.encode()).hexdigest()[:10]}.jpg"
                        img_path = os.path.join(book_image_dir, img_filename)
                        img.save(img_path, "JPEG")
                        current_image_url = f"/api/book_images/{book_id}/{img_filename}"
                        logger.info(f"Extracted image to {current_image_url}")
                
                # Extract text
                text_content = ""
                if hasattr(item, 'text'):
                    text_content = item.text
                elif hasattr(item, 'label'):
                    text_content = item.label
                
                if text_content and len(text_content.strip()) > 5:
                    page_num = 1
                    if item.prov and len(item.prov) > 0:
                        page_num = item.prov[0].page_no
                    
                    # If page changes significantly or image changed, flush
                    if current_metadata.get("page") and abs(page_num - current_metadata["page"]) > 2:
                        flush_block()
                    
                    # Update metadata for the current block if it's empty
                    if not current_text_block:
                        current_metadata = {
                            "source": filename,
                            "book_id": book_id,
                            "page": page_num
                        }
                        if current_image_url:
                            current_metadata["image_url"] = current_image_url
                    
                    current_text_block.append(text_content)
                    
                    # If block gets too large, flush it to allow splitting
                    if sum(len(t) for t in current_text_block) > 3000:
                        flush_block()
            
            # Final flush
            flush_block()
            
            logger.info(f"Extracted {len(processed_docs)} large metadata blocks")
            
            # 4. Split into manageable chunks (User requested at least 1024)
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1500,
                chunk_overlap=300
            )
            
            final_splits = text_splitter.split_documents(processed_docs)
            logger.info(f"Final split produced {len(final_splits)} chunks")
            
            # 5. Store in Qdrant
            vector_store = QdrantVectorStore(
                client=self.qdrant_client,
                collection_name=self.collection_name,
                embedding=self.embedding_model,
            )
            
            vector_store.add_documents(documents=final_splits)
            
            logger.info(f"Successfully stored {len(final_splits)} chunks in Qdrant")
            
            # Update status to completed
            book.status = "completed"
            book.total_chunks = len(final_splits)
            db.commit()
            
            return {
                "status": "success",
                "chunks": len(final_splits),
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
