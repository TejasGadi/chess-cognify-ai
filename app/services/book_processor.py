import os
import re
from typing import List, Dict, Any, Optional
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

    _OUTLINE_BLOCKLIST = frozenset({"picture", "ide", "figure", "fig", "table", "..."})

    def _is_heading_item(self, item: Any, level: int) -> bool:
        """Only SectionHeaderItem or top-level title-like text (for a clean outline)."""
        try:
            if type(item).__name__ == "SectionHeaderItem":
                return True
        except Exception:
            pass
        text = ""
        if hasattr(item, "text") and item.text:
            text = (item.text or "").strip()
        elif hasattr(item, "label") and item.label:
            text = (item.label or "").strip()
        if not text or len(text) <= 3 or len(text) > 90:
            return False
        if text.isdigit() or text.lower() in self._OUTLINE_BLOCKLIST:
            return False
        # Only level 0 for heuristic (top-level headings); title-like: starts with capital, no mid-sentence
        if level != 0:
            return False
        if "..." in text or text.startswith("In ") or text.startswith("Now it's"):
            return False
        if len(text) > 20 and not text[0].isupper():
            return False
        return True

    def _is_chapter_heading(self, label: str) -> bool:
        """True if label looks like a top-level chapter/part (e.g. CHAPTER THREE, Part 1)."""
        s = (label or "").strip()
        if not s:
            return False
        s_lower = s.lower()
        if re.match(r"^(chapter|part)\s+(?:one|two|three|four|five|six|seven|eight|nine|ten|\d+|[ivxlcdm]+)", s_lower):
            return True
        if re.match(r"^chapter\s+[ivxlcdm]+", s_lower):
            return True
        if re.match(r"^[ivxlcdm]+\.\s", s_lower):
            return True
        # All-caps "CHAPTER N" or "CHAPTER THREE"
        if len(s) > 4 and s.isupper() and ("CHAPTER" in s or "PART" in s):
            return True
        return False

    def _assign_heading_levels_by_chapters(self, headings: List[Dict[str, Any]]) -> None:
        """Set level so chapter/part = 0, everything after until next chapter = 1 (nested under that chapter)."""
        seen_chapter = False
        for h in headings:
            label = (h.get("label") or "").strip()
            if self._is_chapter_heading(label):
                h["level"] = 0
                seen_chapter = True
            else:
                # Nest under current chapter; if no chapter yet, keep as top-level (0)
                h["level"] = 1 if seen_chapter else 0

    def _infer_outline_level(self, label: str, level: int) -> int:
        """Infer outline level from label pattern (e.g. 1.1 = 1, 1.1.1 = 2). Used for sub-items."""
        s = (label or "").strip()
        if not s:
            return level
        s_lower = s.lower()
        if re.match(r"^\d+\.\d+\.\d+", s):
            return 2
        if re.match(r"^\d+\.\d+", s) or s_lower.startswith("section ") or re.match(r"^\d+\.\s", s):
            return 1
        return level

    def _build_outline_tree(self, headings: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Build nested tree from flat list of {label, level, page}. Root has label=title, children=list."""
        if not headings:
            return None
        # First: assign hierarchy by chapter boundaries (Chapter N = top level, rest nested until next chapter)
        self._assign_heading_levels_by_chapters(headings)
        # Then: refine sub-levels for items that look like 1.1, 1.1.1, etc.
        for h in headings:
            if h.get("level", 0) == 1:
                orig = int(h.get("level", 0))
                inferred = self._infer_outline_level(h.get("label", ""), orig)
                if inferred == 2:
                    h["level"] = 2
        root: Dict[str, Any] = {"label": "Document", "page": None, "children": []}
        stack: List[Dict[str, Any]] = [root]
        for h in headings:
            label = (h.get("label") or "").strip()
            if not label:
                continue
            level = int(h.get("level", 0))
            page = h.get("page")
            node: Dict[str, Any] = {"label": label, "page": page, "children": []}
            # Pop stack until we have a parent at level - 1
            while len(stack) > 1 and level <= (stack[-1].get("_level", -1)):
                stack.pop()
            parent = stack[-1]
            if "children" not in parent:
                parent["children"] = []
            parent["children"].append(node)
            node["_level"] = level
            stack.append(node)
        # Remove internal _level from tree for JSON output
        def strip_internal(n: Dict[str, Any]) -> Dict[str, Any]:
            out = {"label": n["label"], "page": n.get("page"), "children": []}
            for c in n.get("children", []):
                if "_level" in c:
                    del c["_level"]
                out["children"].append(strip_internal(c))
            return out
        return strip_internal(root)

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

            # 3. Process items and extract images (single pass: outline + content)
            outline_headings: List[Dict[str, Any]] = []
            processed_docs = []
            current_image_urls = []
            image_page_map = {}  # Track which page each image URL belongs to

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
                # Collect heading-like items for document outline (mindmap)
                if self._is_heading_item(item, level):
                    text_content = ""
                    if hasattr(item, "text") and item.text:
                        text_content = (item.text or "").strip()
                    elif hasattr(item, "label") and item.label:
                        text_content = (item.label or "").strip()
                    if text_content and 4 <= len(text_content) <= 90:
                        if text_content.isdigit():
                            continue
                        low = text_content.lower()
                        if low in self._OUTLINE_BLOCKLIST:
                            continue
                        if "..." in text_content or low.startswith("in response") or "now it's time" in low:
                            continue
                        if len(text_content) > 15 and not text_content[0].isupper():
                            continue
                        page_num = 1
                        if getattr(item, "prov", None) and len(item.prov) > 0:
                            page_num = item.prov[0].page_no
                        outline_headings.append({"label": text_content, "level": level, "page": page_num})
                # Check for image
                if hasattr(item, 'image') and item.image:
                    # Flush previous block before starting new image context ONLY if it's a new page
                    # but actually we want images to be associated with following text.
                    # flush_block()
                    
                    img = item.get_image(doc)
                    if img:
                        img_filename = f"img_{hashlib.md5(item.self_ref.encode()).hexdigest()[:10]}.jpg"
                        img_path = os.path.join(book_image_dir, img_filename)
                        img.save(img_path, "JPEG")
                        img_url = f"/api/book_images/{book_id}/{img_filename}"
                        
                        img_page = 1
                        if item.prov and len(item.prov) > 0:
                            img_page = item.prov[0].page_no
                        
                        if img_url not in current_image_urls:
                            current_image_urls.append(img_url)
                            image_page_map[img_url] = img_page
                            
                        logger.info(f"Extracted image from page {img_page} to {img_url}")
                        
                        # Back-associate with previous block if it's on the same page
                        if processed_docs:
                            last_doc = processed_docs[-1]
                            if last_doc.metadata.get("page") == img_page:
                                if "image_urls" not in last_doc.metadata:
                                    last_doc.metadata["image_urls"] = []
                                if img_url not in last_doc.metadata["image_urls"]:
                                    last_doc.metadata["image_urls"].append(img_url)
                                    logger.info(f"Back-associated image {img_url} with previous block on page {img_page}")
                
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
                    
                    # If page changes significantly, flush
                    if current_metadata.get("page") and abs(page_num - current_metadata["page"]) > 2:
                        flush_block()
                    
                    # Periodic cleanup of image_urls that are too far back
                    valid_image_urls = []
                    for url in current_image_urls:
                        img_page = image_page_map.get(url, 0)
                        if abs(page_num - img_page) <= 1: # Within 1 page
                            valid_image_urls.append(url)
                    current_image_urls = valid_image_urls

                    # Update metadata for the current block if it's empty
                    if not current_text_block:
                        current_metadata = {
                            "source": filename,
                            "book_id": book_id,
                            "page": page_num,
                            "image_urls": list(current_image_urls)
                        }
                    else:
                        # Append new images that might have been found while buffering this block
                        for url in current_image_urls:
                            if url not in current_metadata["image_urls"]:
                                current_metadata["image_urls"].append(url)
                    
                    current_text_block.append(text_content)
                    
                    # If block gets too large, flush it to allow splitting
                    if sum(len(t) for t in current_text_block) > 3000:
                        flush_block()

            # Build document outline (mindmap) tree from collected headings
            outline_tree = self._build_outline_tree(outline_headings)
            if outline_tree:
                logger.info(f"Built document outline with {len(outline_headings)} headings")

            # Final flush
            flush_block()

            logger.info(f"Extracted {len(processed_docs)} large metadata blocks")
            
            # 4. Split into manageable chunks (User requested at least 1024)
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=800,
                chunk_overlap=200
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
            
            # Update status to completed and persist outline (mindmap)
            book.status = "completed"
            book.total_chunks = len(final_splits)
            if outline_tree is not None:
                book.outline = outline_tree
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
