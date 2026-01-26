"""
PDF processing service for extracting and chunking text from chess books.
"""
import pdfplumber
from typing import List, Dict, Optional
from pathlib import Path
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PDFService:
    """Service for processing PDF files."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize PDF service.

        Args:
            chunk_size: Maximum characters per chunk
            chunk_overlap: Overlap between chunks in characters
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def extract_text(self, pdf_path: str) -> str:
        """
        Extract all text from a PDF file.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text as a single string
        """
        try:
            text_parts = []
            with pdfplumber.open(pdf_path) as pdf:
                logger.info(f"Extracting text from PDF: {pdf_path} ({len(pdf.pages)} pages)")
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                    if page_num % 50 == 0:
                        logger.debug(f"Processed {page_num} pages")

            full_text = "\n\n".join(text_parts)
            logger.info(f"Extracted {len(full_text)} characters from PDF")
            return full_text

        except Exception as e:
            logger.error(f"Error extracting text from PDF {pdf_path}: {e}")
            raise

    def clean_text(self, text: str) -> str:
        """
        Clean and normalize extracted text.

        Args:
            text: Raw extracted text

        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        lines = text.split("\n")
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line:
                cleaned_lines.append(line)

        # Join with single newlines
        cleaned = "\n".join(cleaned_lines)

        # Remove multiple consecutive newlines (more than 2)
        while "\n\n\n" in cleaned:
            cleaned = cleaned.replace("\n\n\n", "\n\n")

        return cleaned

    def chunk_text(
        self, text: str, metadata: Optional[Dict] = None
    ) -> List[Dict[str, str]]:
        """
        Split text into semantic chunks with overlap.

        Args:
            text: Text to chunk
            metadata: Optional metadata to attach to each chunk

        Returns:
            List of chunk dictionaries with 'text' and 'metadata' keys
        """
        if not text:
            return []

        # Clean text first
        cleaned_text = self.clean_text(text)

        chunks = []
        start = 0
        chunk_index = 0

        while start < len(cleaned_text):
            # Calculate end position
            end = start + self.chunk_size

            # Try to break at paragraph boundary (double newline)
            if end < len(cleaned_text):
                # Look for paragraph break near the end
                paragraph_break = cleaned_text.rfind("\n\n", start, end)
                if paragraph_break > start:
                    end = paragraph_break + 2  # Include the newlines

            # Extract chunk
            chunk_text = cleaned_text[start:end].strip()

            if chunk_text:
                chunk_metadata = {
                    "chunk_index": chunk_index,
                    "start_char": start,
                    "end_char": end,
                }
                if metadata:
                    chunk_metadata.update(metadata)

                chunks.append(
                    {
                        "text": chunk_text,
                        "metadata": chunk_metadata,
                    }
                )
                chunk_index += 1

            # Move start position with overlap
            start = end - self.chunk_overlap
            if start < 0:
                start = 0

            # Prevent infinite loop
            if start >= len(cleaned_text):
                break

        logger.info(f"Created {len(chunks)} chunks from text ({len(cleaned_text)} chars)")
        return chunks

    def process_pdf(
        self, pdf_path: str, book_id: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Complete PDF processing pipeline: extract, clean, and chunk.

        Args:
            pdf_path: Path to PDF file
            book_id: Optional book ID for metadata

        Returns:
            Dictionary with 'text', 'chunks', 'total_pages', and 'metadata'
        """
        try:
            # Extract text
            raw_text = self.extract_text(pdf_path)

            # Count pages
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)

            # Clean text
            cleaned_text = self.clean_text(raw_text)

            # Prepare metadata
            metadata = {
                "book_id": book_id,
                "filename": Path(pdf_path).name,
                "total_pages": total_pages,
            }

            # Chunk text
            chunks = self.chunk_text(cleaned_text, metadata=metadata)

            return {
                "text": cleaned_text,
                "chunks": chunks,
                "total_pages": total_pages,
                "metadata": metadata,
            }

        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {e}")
            raise
